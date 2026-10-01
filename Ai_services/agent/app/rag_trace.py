"""Temporary, opt-in, one-chat diagnostic; never changes graph state or payloads."""
from contextvars import ContextVar
import json
import os
from uuid import uuid4

_active = ContextVar("rag_trace", default=None)
_claimed = False


def begin(question):
    global _claimed
    target = os.getenv("RAG_TRACE_QUESTION", "")
    if not target or question != target or _claimed:
        return None
    _claimed = True
    return _active.set({"trace_id": str(uuid4()), "question": question, "calls": 0})


def end(token):
    if token is not None:
        _active.reset(token)


def enabled():
    return _active.get() is not None


def bind(**fields):
    if enabled():
        _active.get().update(fields)


def emit(event, **fields):
    if enabled():
        print(json.dumps({"diagnostic": "rag_trace_v1", **_active.get(),
                          "event": event, **fields}, ensure_ascii=False, default=str), flush=True)


def next_call():
    if not enabled():
        return None
    _active.get()["calls"] += 1
    return _active.get()["calls"]


def chunks(items):
    return [{"rank": rank, "source": item.get("metadata", {}).get("source"),
             **{key: item.get("metadata", {}).get(key) for key in
                ("title", "document_id", "chunk_id", "status", "reliability")},
             "score": item.get("score"), "text_start": str(item.get("text", ""))[:600]}
            for rank, item in enumerate(items, 1)]


def messages(items):
    return [{"type": item.type, "id": item.id, "content": item.content,
             "sources": item.additional_kwargs.get("metadata", {}).get("sources", [])}
            for item in items]


def state(values):
    return {**{key: values.get(key) for key in
               ("intent", "topics", "rewritten_queries", "queries", "context",
                "retrieved_context", "sources", "player_context", "search_type")},
            "keys": sorted(values), "retrieved_documents": chunks(values.get("retrieved_documents", [])),
            "messages": messages(values.get("messages", []))}
