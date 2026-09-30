"""Read-only LangGraph workflow for the Lords Mobile documentary agent."""

from __future__ import annotations

import asyncio
import os
import re
from typing import Annotated, Any, NotRequired, TypedDict

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from intent import (
    classify_intent,
    extract_game_version,
    extract_topics,
    needs_clarification,
    rewrite_queries,
)
from prompts import build_grounded_prompt


RAG_URL = os.getenv("RAG_SERVICE_URL", "http://rag:8001").rstrip("/")
MAX_CONTEXT_CHUNKS = 8
_CITATION_PATTERN = re.compile(r"\[(\d+)]")
_PERCENT_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:[-–—]\s*\d+(?:[.,]\d+)?)?\s*%"
)
_QUOTED_TERM_PATTERN = re.compile(r"[\"“«]([^\"”»\n]{2,80})[\"”»]")


class LordsMobileState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: NotRequired[str]
    language: NotRequired[str]
    game_version: NotRequired[str | None]
    player_context: NotRequired[dict[str, Any]]
    intent: NotRequired[str]
    topics: NotRequired[list[str]]
    rewritten_queries: NotRequired[list[str]]
    retrieved_documents: NotRequired[list[dict[str, Any]]]
    context: NotRequired[str]
    sources: NotRequired[list[dict[str, Any]]]
    confidence: NotRequired[float]
    needs_clarification: NotRequired[bool]
    search_type: NotRequired[str]
    generation_mode: NotRequired[str]
    model: NotRequired[str]
    base_url: NotRequired[str]


# Backward-compatible import name for callers that imported AgentState.
AgentState = LordsMobileState


def _latest_question(state: LordsMobileState) -> str:
    message = next(
        (item for item in reversed(state.get("messages", [])) if isinstance(item, HumanMessage)),
        None,
    )
    return str(message.content).strip() if message else ""


def get_llm(
    model_name: str | None,
    base_url: str | None,
    api_key: str | None,
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model_name or "qwen2.5:7b-instruct",
        api_key=api_key or "local-provider",
        base_url=base_url,
        temperature=0.2,
        timeout=60,
        max_retries=1,
    )


def classify_node(state: LordsMobileState) -> dict[str, Any]:
    query = _latest_question(state)
    intent = classify_intent(query)
    requested_language = state.get("language")
    language = requested_language if requested_language in {"fr", "en", "ar"} else "fr"
    return {"intent": intent, "language": language}


def route_after_classification(state: LordsMobileState) -> str:
    intent = state.get("intent", "unclear")
    if intent in {"greeting", "unclear", "out_of_scope"}:
        return "direct_answer"
    return "extract_game_context"


def extract_game_context_node(state: LordsMobileState) -> dict[str, Any]:
    query = _latest_question(state)
    player_context = state.get("player_context") or {}
    intent = state.get("intent", "fact_lookup")
    return {
        "topics": extract_topics(query),
        "game_version": extract_game_version(query, state.get("game_version")),
        "player_context": player_context,
        "needs_clarification": needs_clarification(query, intent, player_context),
    }


def route_after_context_extraction(state: LordsMobileState) -> str:
    return "clarification_answer" if state.get("needs_clarification") else "rewrite_query"


def _clarification_message(language: str) -> str:
    messages = {
        "fr": (
            "Aucune stratégie ne peut garantir une victoire dans toutes les batailles. "
            "Pour vous donner un conseil documenté, précisez le type de bataille "
            "(joueur contre joueur, Sombre nid, Colisée ou niveau), les troupes repérées "
            "chez l’adversaire et les types de troupes que vous pouvez engager."
        ),
        "en": (
            "No strategy can guarantee victory in every battle. For sourced advice, "
            "specify the battle type (player versus player, Darknest, Colosseum, or stage), "
            "the enemy troops you scouted, and the troop types you can deploy."
        ),
        "ar": (
            "لا توجد استراتيجية تضمن الفوز في كل المعارك. للحصول على نصيحة موثقة، "
            "حدّد نوع المعركة، وقوات الخصم التي كشفتها، وأنواع القوات التي يمكنك إرسالها."
        ),
    }
    return messages.get(language, messages["fr"])


def clarification_answer_node(state: LordsMobileState) -> dict[str, Any]:
    return {
        "messages": [AIMessage(content=_clarification_message(state.get("language", "fr")))],
        "sources": [],
        "context": "",
        "retrieved_documents": [],
        "rewritten_queries": [],
        "confidence": 0.0,
        "needs_clarification": True,
        "generation_mode": "deterministic_clarification",
    }


def rewrite_node(state: LordsMobileState) -> dict[str, Any]:
    query = _latest_question(state)
    return {"rewritten_queries": rewrite_queries(query, state.get("topics", []))}


async def _retrieve_one(
    query: str,
    *,
    search_type: str,
    top_k: int,
    game_version: str | None,
    statuses: list[str],
    min_reliability: int,
    min_score: float,
) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {
        "query": query,
        "top_k": top_k,
        "search_type": search_type,
        # Search across source languages; the saved preference controls the answer.
        "statuses": statuses,
        "min_reliability": min_reliability,
        "min_relevance_score": min_score,
    }
    if game_version:
        payload["game_version"] = game_version

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{RAG_URL}/retrieve", json=payload)
        response.raise_for_status()
        return response.json().get("chunks", [])


async def retrieve_node(
    state: LordsMobileState, config: RunnableConfig
) -> dict[str, Any]:
    cfg = (config or {}).get("configurable", {})
    query = _latest_question(state)
    rewritten = state.get("rewritten_queries", [])
    queries = list(dict.fromkeys([query, *rewritten]))
    search_type = str(cfg.get("search_type", "hybrid"))
    top_k = max(1, min(int(cfg.get("top_k", 8)), 20))
    min_score = max(0.0, min(float(cfg.get("min_relevance_score", 0.25)), 1.0))
    min_reliability = max(1, min(int(cfg.get("min_reliability", 4)), 5))
    game_version = state.get("game_version")
    statuses = ["active", "deprecated"] if game_version else ["active"]
    # A deliberately selected annual review corpus can be consulted with reservations.
    # Unspecified versions retain the validated-only policy; no document is promoted.
    if game_version and re.fullmatch(r"\d{4}-review", game_version):
        statuses = ["active", "needs_review"]
        min_reliability = max(3, min_reliability - 1)

    batches = await asyncio.gather(
        *[
            _retrieve_one(
                item,
                search_type=search_type,
                top_k=top_k,
                game_version=game_version,
                statuses=statuses,
                min_reliability=min_reliability,
                min_score=min_score,
            )
            for item in queries
        ]
    )

    deduplicated: dict[str, dict[str, Any]] = {}
    for chunk in (item for batch in batches for item in batch):
        metadata = chunk.get("metadata", {})
        key = str(metadata.get("chunk_id") or chunk.get("text", "")[:200])
        previous = deduplicated.get(key)
        if previous is None or float(chunk.get("score", 0)) > float(previous.get("score", 0)):
            deduplicated[key] = chunk

    ranked = sorted(
        deduplicated.values(), key=lambda item: float(item.get("score", 0)), reverse=True
    )[:MAX_CONTEXT_CHUNKS]
    return {
        "retrieved_documents": ranked,
        "search_type": search_type,
    }


def _source_from_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    metadata = chunk.get("metadata", {})
    return {
        "chunk_id": metadata.get("chunk_id"),
        "document_id": metadata.get("document_id"),
        "title": metadata.get("title") or metadata.get("source") or "Source",
        "content": str(chunk.get("text", "")).strip(),
        "url": metadata.get("url"),
        "source_type": metadata.get("source_type"),
        "language": metadata.get("language"),
        "game_version": metadata.get("game_version"),
        "status": metadata.get("status"),
        "reliability": metadata.get("reliability"),
        "score": round(float(chunk.get("score", 0)), 4),
    }


def validate_context_node(state: LordsMobileState) -> dict[str, Any]:
    chunks = state.get("retrieved_documents", [])
    # Keep exactly one source entry per context block so [n] always maps to
    # the same passage in both the prompt and the frontend evidence panel.
    sources = [_source_from_chunk(chunk) for chunk in chunks]
    if chunks:
        top_scores = [float(item.get("score", 0)) for item in chunks[:3]]
        score_signal = sum(top_scores) / len(top_scores)
        reliability_values = [
            float(item.get("metadata", {}).get("reliability", 1)) / 5.0
            for item in chunks[:3]
        ]
        reliability_signal = sum(reliability_values) / len(reliability_values)
        confidence = round(min(0.95, 0.7 * score_signal + 0.3 * reliability_signal), 3)
    else:
        confidence = 0.0

    requires_clarification = bool(state.get("needs_clarification")) or not chunks
    context = "\n\n".join(str(item.get("text", "")) for item in chunks)
    return {
        "context": context,
        "sources": sources,
        "confidence": confidence,
        "needs_clarification": requires_clarification,
    }


def _localized_direct_answer(intent: str, language: str) -> str:
    messages = {
        "fr": {
            "greeting": "Bonjour ! Je peux vous guider dans Lords Mobile à partir de sources documentées.",
            "unclear": "Pouvez-vous préciser votre question sur Lords Mobile, par exemple le héros, le type de troupe, l’événement ou votre objectif ?",
            "out_of_scope": "Je suis limité au guide documentaire Lords Mobile en lecture seule. Je ne peux ni automatiser un compte ou le jeu, ni traiter les anciennes fonctions réseau de QoSentry.",
        },
        "en": {
            "greeting": "Hello! I can provide sourced, read-only guidance about Lords Mobile.",
            "unclear": "Please clarify your Lords Mobile question, such as the hero, troop type, event, or goal involved.",
            "out_of_scope": "I am limited to sourced, read-only Lords Mobile guidance. I cannot automate accounts or gameplay, or handle QoSentry network operations.",
        },
        "ar": {
            "greeting": "مرحبًا! يمكنني تقديم إرشادات موثقة عن Lords Mobile بوضع القراءة فقط.",
            "unclear": "يرجى توضيح سؤالك عن Lords Mobile، مثل البطل أو نوع القوات أو الحدث أو الهدف.",
            "out_of_scope": "أنا مخصص لإرشادات Lords Mobile الموثقة وبوضع القراءة فقط، ولا أستطيع أتمتة الحساب أو اللعب.",
        },
    }
    catalog = messages.get(language, messages["fr"])
    return catalog.get(intent, catalog["unclear"])


def direct_answer_node(state: LordsMobileState) -> dict[str, Any]:
    intent = state.get("intent", "unclear")
    language = state.get("language", "fr")
    return {
        "messages": [AIMessage(content=_localized_direct_answer(intent, language))],
        "sources": [],
        "context": "",
        "retrieved_documents": [],
        "rewritten_queries": [],
        "confidence": 1.0 if intent == "greeting" else 0.0,
        "needs_clarification": intent == "unclear",
        "generation_mode": "deterministic",
    }


def _fallback_grounded_answer(state: LordsMobileState) -> str:
    language = state.get("language", "fr")
    length = (state.get("player_context") or {}).get("response_length", "standard")
    count = {"short": 1, "standard": 2, "detailed": 3}.get(length, 2)
    chunks = state.get("retrieved_documents", [])[:count]
    if not chunks:
        if language == "en":
            return "I did not find reliable enough evidence in the corpus. Please specify the topic or game version."
        if language == "ar":
            return "لم أجد دليلاً موثوقًا كافيًا في المصادر. يرجى تحديد الموضوع أو إصدار اللعبة."
        return "Je n’ai pas trouvé de preuve suffisamment fiable dans le corpus. Précisez le sujet ou la version du jeu."

    if language == "en":
        return (
            "The available documents contain evidence relevant to this question. "
            f"Review evidence item(s) {', '.join(f'[{index}]' for index in range(1, len(chunks) + 1))} "
            "in the RAG evidence panel for the exact source excerpts. "
            "Check the source version before relying on exact values."
        )
    elif language == "ar":
        return (
            "تتضمن الوثائق المتاحة أدلة مرتبطة بهذا السؤال. "
            f"راجع الأدلة {', '.join(f'[{index}]' for index in range(1, len(chunks) + 1))} "
            "في لوحة أدلة RAG للاطلاع على مقتطفات المصادر. "
            "تحقق من إصدار المصدر قبل الاعتماد على القيم الدقيقة."
        )
    else:
        heading = "Les documents disponibles indiquent :"
        warning = "Vérifiez la version de la source avant d’utiliser une valeur précise."
        excerpts = [
            f"- Consultez la preuve [{index}] dans le panneau Preuves RAG."
            for index in range(1, len(chunks) + 1)
        ]
        return "\n".join([heading, *excerpts, warning])


def _normalize_evidence(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().replace("–", "-").replace("—", "-")).strip()


def grounding_issues(content: str, chunks: list[dict[str, Any]]) -> list[str]:
    """Detect high-risk claims that cannot be traced to retrieved evidence."""
    issues: list[str] = []
    citations = [int(value) for value in _CITATION_PATTERN.findall(content)]
    if not citations:
        issues.append("missing_citation")
    elif any(value < 1 or value > len(chunks) for value in citations):
        issues.append("invalid_citation")

    evidence = _normalize_evidence(
        "\n".join(str(chunk.get("text", "")) for chunk in chunks)
    )
    answer_without_citations = _CITATION_PATTERN.sub("", content)
    for numeric_claim in _PERCENT_PATTERN.findall(answer_without_citations):
        if _normalize_evidence(numeric_claim) not in evidence:
            issues.append(f"unsupported_percentage:{numeric_claim.strip()}")

    for quoted_term in _QUOTED_TERM_PATTERN.findall(answer_without_citations):
        normalized = _normalize_evidence(quoted_term)
        if re.search(r"[a-zà-ÿ]", normalized) and normalized not in evidence:
            issues.append(f"unsupported_quoted_term:{quoted_term.strip()}")

    return issues


async def generate_node(
    state: LordsMobileState, config: RunnableConfig
) -> dict[str, Any]:
    cfg = (config or {}).get("configurable", {})
    chunks = state.get("retrieved_documents", [])
    if not chunks:
        return {
            "messages": [AIMessage(content=_fallback_grounded_answer(state))],
            "generation_mode": "safe_fallback",
        }

    system_prompt = build_grounded_prompt(
        language=state.get("language", "fr"),
        intent=state.get("intent", "fact_lookup"),
        game_version=state.get("game_version"),
        player_context=state.get("player_context", {}),
        context_blocks=chunks,
    )
    try:
        llm = get_llm(
            model_name=cfg.get("model") or state.get("model"),
            base_url=cfg.get("base_url") or state.get("base_url"),
            api_key=cfg.get("api_key"),
        )
        history = list(state.get("messages", []))[-12:]
        response = await llm.ainvoke([SystemMessage(content=system_prompt), *history])
        content = response.content if isinstance(response.content, str) else str(response.content)
        issues = grounding_issues(content, chunks)
        if issues:
            print(
                "Warning: LLM answer failed grounding validation, using grounded fallback: "
                + ", ".join(issues)
            )
            content = _fallback_grounded_answer(state)
            mode = "grounding_fallback"
        else:
            mode = "llm"
    except Exception as error:
        print(f"Warning: LLM generation unavailable, using grounded fallback: {error}")
        content = _fallback_grounded_answer(state)
        mode = "safe_fallback"

    if any(chunk.get("metadata", {}).get("status") == "needs_review" for chunk in chunks):
        warning = {
            "fr": "Sources avec réserves : ce corpus n’est pas entièrement validé ; son année ne garantit pas sa compatibilité avec la version actuelle du jeu.",
            "en": "Sources awaiting review: this corpus is not yet validated; its year does not guarantee compatibility with the current game version.",
            "ar": "مصادر قيد المراجعة: هذه المجموعة لم تُعتمد بعد، ولا تضمن سنتها التوافق مع الإصدار الحالي للعبة.",
        }.get(state.get("language", "fr"))
        content = f"{warning}\n\n{content}"

    ai_message = AIMessage(
        content=content,
        additional_kwargs={
            "metadata": {
                "sources": state.get("sources", []),
                "confidence": state.get("confidence", 0.0),
                "needs_clarification": state.get("needs_clarification", False),
                "game_version": state.get("game_version"),
            }
        },
    )
    return {"messages": [ai_message], "generation_mode": mode}


def build_graph(checkpointer=None):
    builder = StateGraph(LordsMobileState)
    builder.add_node("classify_intent", classify_node)
    builder.add_node("direct_answer", direct_answer_node)
    builder.add_node("extract_game_context", extract_game_context_node)
    builder.add_node("clarification_answer", clarification_answer_node)
    builder.add_node("rewrite_query", rewrite_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("validate_context", validate_context_node)
    builder.add_node("generate_answer", generate_node)

    builder.set_entry_point("classify_intent")
    builder.add_conditional_edges(
        "classify_intent",
        route_after_classification,
        {
            "direct_answer": "direct_answer",
            "extract_game_context": "extract_game_context",
        },
    )
    builder.add_edge("direct_answer", END)
    builder.add_conditional_edges(
        "extract_game_context",
        route_after_context_extraction,
        {
            "clarification_answer": "clarification_answer",
            "rewrite_query": "rewrite_query",
        },
    )
    builder.add_edge("clarification_answer", END)
    builder.add_edge("rewrite_query", "retrieve")
    builder.add_edge("retrieve", "validate_context")
    builder.add_edge("validate_context", "generate_answer")
    builder.add_edge("generate_answer", END)
    return builder.compile(checkpointer=checkpointer) if checkpointer else builder.compile()
