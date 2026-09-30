"""FastAPI entry point for the read-only Lords Mobile LangGraph agent."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pydantic import BaseModel, ConfigDict, Field

from config import DEFAULT_PROVIDER, FULL_CONFIG, LLM_MODEL, PROVIDERS
from db import CHECKPOINT_DB_URI, get_db_connection
from graph import build_graph


class OpenAIMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str = ""
    messages: list[OpenAIMessage] | None = None
    thread_id: str | None = None
    user_id: str | None = None
    model: str | None = None
    provider: str | None = None
    base_url: str | None = None
    language: str | None = Field(default=None, pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
    game_version: str | None = Field(default=None, max_length=50)
    player_context: dict[str, Any] = Field(default_factory=dict)
    search_type: str = Field(default="hybrid", pattern=r"^(hybrid|semantic|keyword)$")
    top_k: int = Field(default=8, ge=1, le=20)
    min_relevance_score: float = Field(default=0.25, ge=0.0, le=1.0)
    min_reliability: int = Field(default=4, ge=1, le=5)


class ChatResponse(BaseModel):
    thread_id: str
    response: str
    model: str
    provider: str
    intent: str
    language: str
    game_version: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
    needs_clarification: bool = False
    search_type: str = "hybrid"
    rewritten_queries: list[str] = Field(default_factory=list)
    generation_mode: str = "llm"
    read_only: bool = True


class OpenAIChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str | None = None
    messages: list[OpenAIMessage]
    thread_id: str | None = None
    provider: str | None = None
    base_url: str | None = None
    language: str | None = None
    game_version: str | None = None
    player_context: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False


async def _run_setup_maybe_async(checkpointer) -> None:
    setup = getattr(checkpointer, "setup", None)
    if callable(setup):
        result = setup()
        if asyncio.iscoroutine(result):
            await result


async def _ensure_agent_threads_table() -> None:
    """Keep agent checkpoint metadata separate from backend business tables."""
    if not CHECKPOINT_DB_URI:
        return
    connection = await get_db_connection()
    async with connection:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_threads (
                thread_id TEXT PRIMARY KEY,
                user_id TEXT,
                preview TEXT,
                language VARCHAR(16),
                game_version VARCHAR(50),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


async def _upsert_thread(
    thread_id: str,
    *,
    user_id: str | None,
    preview: str,
    language: str | None,
    game_version: str | None,
) -> None:
    if not CHECKPOINT_DB_URI:
        return
    connection = await get_db_connection()
    async with connection:
        await connection.execute(
            """
            INSERT INTO agent_threads
                (thread_id, user_id, preview, language, game_version, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (thread_id) DO UPDATE SET
                user_id = COALESCE(EXCLUDED.user_id, agent_threads.user_id),
                preview = EXCLUDED.preview,
                language = COALESCE(EXCLUDED.language, agent_threads.language),
                game_version = COALESCE(EXCLUDED.game_version, agent_threads.game_version),
                updated_at = NOW()
            """,
            (thread_id, user_id, preview[:400], language, game_version),
        )


async def _delete_thread_metadata(thread_id: str) -> None:
    if not CHECKPOINT_DB_URI:
        return
    connection = await get_db_connection()
    async with connection:
        await connection.execute(
            "DELETE FROM agent_threads WHERE thread_id = %s", (thread_id,)
        )


async def _list_thread_metadata(limit: int, offset: int) -> list[dict[str, Any]]:
    if not CHECKPOINT_DB_URI:
        return []
    connection = await get_db_connection()
    async with connection:
        cursor = await connection.execute(
            """
            SELECT thread_id, user_id, preview, language, game_version, updated_at
            FROM agent_threads
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        rows = await cursor.fetchall()
    return [
        {
            **dict(row),
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        }
        for row in rows
    ]


def _resolve_provider(
    provider: str | None, base_url: str | None
) -> tuple[str, str, str | None]:
    provider_id = provider or DEFAULT_PROVIDER
    if provider_id not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider_id}'")
    provider_config = PROVIDERS[provider_id]
    resolved_url = (base_url or provider_config.get("base_url") or "").strip()
    if not resolved_url:
        raise HTTPException(status_code=400, detail="The selected provider has no base URL")
    return provider_id, resolved_url, provider_config.get("api_key")


async def _fetch_models() -> list[dict[str, Any]]:
    available: list[dict[str, Any]] = []
    for provider_id, provider in PROVIDERS.items():
        headers = {}
        if provider.get("api_key"):
            headers["Authorization"] = f"Bearer {provider['api_key']}"
        try:
            async with httpx.AsyncClient(timeout=provider.get("timeout_seconds", 10)) as client:
                response = await client.get(
                    provider["base_url"].rstrip("/") + "/models", headers=headers
                )
                response.raise_for_status()
                for item in response.json().get("data", []):
                    if item.get("id"):
                        available.append(
                            {
                                "id": item["id"],
                                "object": "model",
                                "owned_by": item.get("owned_by", provider_id),
                                "provider": provider_id,
                            }
                        )
        except Exception as error:
            print(f"Warning: model listing unavailable for {provider_id}: {error}")
    if available:
        return available
    return [
        {
            "id": LLM_MODEL,
            "object": "model",
            "owned_by": "configured-default",
            "provider": DEFAULT_PROVIDER,
        }
    ]


def _extract_user_message(messages: list[OpenAIMessage]) -> str:
    for message in reversed(messages):
        if message.role.lower() == "user" and message.content.strip():
            return message.content.strip()
    return ""


def _graph_messages(messages: list[OpenAIMessage]) -> list[BaseMessage]:
    converted: list[BaseMessage] = []
    for message in messages:
        content = message.content.strip()
        if not content:
            continue
        role = message.role.lower()
        if role == "user":
            converted.append(HumanMessage(content=content))
        elif role == "assistant":
            converted.append(AIMessage(content=content))
        # External system messages are intentionally ignored.
    return converted


def _normalize_messages(messages: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for message in messages or []:
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            continue
        content = message.content if isinstance(message.content, str) else str(message.content)
        if content:
            normalized.append({"role": role, "content": content})
    return normalized


async def _get_graph_state(graph, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    getter = getattr(graph, "aget_state", None)
    return await getter(config) if callable(getter) else graph.get_state(config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.checkpointer = None
    app.state.checkpointer_context = None
    app.state.persistence_enabled = False
    app.state.graph = build_graph()

    if CHECKPOINT_DB_URI:
        context = AsyncPostgresSaver.from_conn_string(CHECKPOINT_DB_URI)
        checkpointer = await context.__aenter__()
        await _run_setup_maybe_async(checkpointer)
        await _ensure_agent_threads_table()
        app.state.checkpointer = checkpointer
        app.state.checkpointer_context = context
        app.state.persistence_enabled = True
        app.state.graph = build_graph(checkpointer=checkpointer)

    try:
        yield
    finally:
        if app.state.checkpointer_context is not None:
            await app.state.checkpointer_context.__aexit__(None, None, None)


app = FastAPI(
    title="Lords Mobile Guide Agent",
    version="1.0.0",
    description="Read-only, source-grounded LangGraph agent.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "lords-mobile-agent",
        "read_only": True,
        "persistence": bool(getattr(app.state, "persistence_enabled", False)),
    }


@app.get("/config")
async def get_config():
    return {**FULL_CONFIG, "read_only": True, "domain": "lords-mobile"}


@app.get("/models")
@app.get("/v1/models")
async def models():
    return {"object": "list", "data": await _fetch_models()}


@app.post("/threads")
async def create_thread():
    thread_id = str(uuid4())
    if getattr(app.state, "persistence_enabled", False):
        await _upsert_thread(
            thread_id,
            user_id=None,
            preview="",
            language=None,
            game_version=None,
        )
    return {"thread_id": thread_id, "created_at": time.time(), "status": "created"}


@app.get("/threads")
async def list_threads(limit: int = 100, offset: int = 0):
    data = await _list_thread_metadata(max(1, min(limit, 500)), max(0, offset))
    return {
        "object": "list",
        "data": data,
        "persistence": bool(getattr(app.state, "persistence_enabled", False)),
    }


@app.get("/threads/{thread_id}")
async def get_thread(thread_id: str):
    if not getattr(app.state, "persistence_enabled", False):
        raise HTTPException(status_code=404, detail="Thread persistence is not enabled")
    snapshot = await _get_graph_state(app.state.graph, thread_id)
    values = getattr(snapshot, "values", {}) or {}
    messages = _normalize_messages(values.get("messages", []))
    if not messages:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {
        "thread_id": thread_id,
        "messages": messages,
        "language": values.get("language"),
        "game_version": values.get("game_version"),
        "player_context": values.get("player_context", {}),
    }


@app.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    if not getattr(app.state, "persistence_enabled", False):
        raise HTTPException(status_code=404, detail="Thread persistence is not enabled")
    checkpointer = app.state.checkpointer
    delete = getattr(checkpointer, "adelete_thread", None)
    if not callable(delete):
        raise HTTPException(status_code=500, detail="Thread deletion is not supported")
    await delete(thread_id)
    await _delete_thread_metadata(thread_id)
    return {"thread_id": thread_id, "status": "deleted"}


async def _invoke_chat(request: ChatRequest) -> ChatResponse:
    incoming = request.messages or [OpenAIMessage(role="user", content=request.message)]
    user_message = _extract_user_message(incoming) or request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="No valid user message provided")

    thread_id = request.thread_id or str(uuid4())
    provider, base_url, api_key = _resolve_provider(request.provider, request.base_url)
    model_name = request.model or LLM_MODEL
    if getattr(app.state, "persistence_enabled", False):
        messages: list[BaseMessage] = [HumanMessage(content=user_message)]
    else:
        messages = _graph_messages(incoming)
        if not messages:
            messages = [HumanMessage(content=user_message)]

    state: dict[str, Any] = {
        "messages": messages,
        "model": model_name,
        "base_url": base_url,
    }
    if request.user_id:
        state["user_id"] = request.user_id
    # Always overwrite checkpointed preferences, including an explicitly unknown version.
    state["language"] = request.language
    state["game_version"] = request.game_version
    state["player_context"] = request.player_context

    result = await app.state.graph.ainvoke(
        state,
        config={
            "configurable": {
                "thread_id": thread_id,
                "model": model_name,
                "provider": provider,
                "base_url": base_url,
                "api_key": api_key,
                "search_type": request.search_type,
                "top_k": request.top_k,
                "min_relevance_score": request.min_relevance_score,
                "min_reliability": request.min_reliability,
            }
        },
    )
    response_message = result.get("messages", [])[-1]
    response_text = response_message.content if isinstance(response_message.content, str) else str(response_message.content)

    await _upsert_thread(
        thread_id,
        user_id=request.user_id,
        preview=user_message,
        language=result.get("language"),
        game_version=result.get("game_version"),
    )
    return ChatResponse(
        thread_id=thread_id,
        response=response_text,
        model=model_name,
        provider=provider,
        intent=result.get("intent", "fact_lookup"),
        language=result.get("language", "fr"),
        game_version=result.get("game_version"),
        sources=result.get("sources", []),
        confidence=float(result.get("confidence", 0.0)),
        needs_clarification=bool(result.get("needs_clarification", False)),
        search_type=result.get("search_type", request.search_type),
        rewritten_queries=result.get("rewritten_queries", []),
        generation_mode=result.get("generation_mode", "llm"),
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        return await _invoke_chat(request)
    except HTTPException:
        raise
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"RAG service unavailable: {error}") from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: OpenAIChatRequest):
    if request.stream:
        raise HTTPException(status_code=400, detail="Streaming is not supported yet")
    result = await _invoke_chat(
        ChatRequest(
            messages=request.messages,
            thread_id=request.thread_id,
            model=request.model,
            provider=request.provider,
            base_url=request.base_url,
            language=request.language,
            game_version=request.game_version,
            player_context=request.player_context,
        )
    )
    return {
        "id": f"chatcmpl-{uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": result.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result.response},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "thread_id": result.thread_id,
        "provider": result.provider,
        "sources": result.sources,
        "confidence": result.confidence,
        "needs_clarification": result.needs_clarification,
        "game_version": result.game_version,
        "read_only": True,
    }
