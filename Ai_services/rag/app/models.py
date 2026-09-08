"""Validated contracts for the Lords Mobile knowledge corpus and retrieval API."""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


DocumentStatus = Literal["active", "deprecated", "needs_review"]
SourceType = Literal["official", "verified_community", "community", "reference"]
SearchType = Literal["hybrid", "semantic", "keyword"]


class LordsMobileMetadata(BaseModel):
    """Traceability fields stored with every indexed chunk."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    document_id: Annotated[str, Field(min_length=1, max_length=255)]
    title: Annotated[str, Field(min_length=1, max_length=500)]
    source: Annotated[str, Field(min_length=1, max_length=500)]
    source_type: SourceType
    language: Annotated[
        str, Field(min_length=2, max_length=16, pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
    ]
    game_version: Annotated[str, Field(min_length=1, max_length=50)]
    reliability: Annotated[int, Field(ge=1, le=5)]
    status: DocumentStatus
    url: HttpUrl | None = None
    published_at: date | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    topics: Annotated[list[str], Field(min_length=1)]
    entity_type: Annotated[str | None, Field(max_length=100)] = None
    entity_name: Annotated[str | None, Field(max_length=255)] = None
    tags: list[str] = Field(default_factory=list)
    content_hash: Annotated[str | None, Field(min_length=16, max_length=128)] = None
    parent_doc_hash: Annotated[str | None, Field(min_length=16, max_length=128)] = None

    @field_validator("topics")
    @classmethod
    def normalize_topics(cls, values: list[str]) -> list[str]:
        normalized = list(
            dict.fromkeys(value.strip().lower() for value in values if value.strip())
        )
        if not normalized:
            raise ValueError("must contain at least one non-empty value")
        return normalized

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))

    @field_validator("collected_at")
    @classmethod
    def collected_at_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("must include a timezone")
        return value


class IngestTextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: Annotated[str, Field(min_length=1)]
    metadata: LordsMobileMetadata


class BatchDocument(IngestTextRequest):
    pass


class BatchIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: Annotated[list[BatchDocument], Field(min_length=1, max_length=100)]


class RetrieveRequest(BaseModel):
    """Hybrid retrieval request. Active sources are used unless requested otherwise."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    query: Annotated[str, Field(min_length=1)]
    top_k: Annotated[int, Field(ge=1, le=50)] = int(os.getenv("TOP_K", "8"))
    search_type: SearchType = "hybrid"
    min_relevance_score: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5
    language: Annotated[
        str | None,
        Field(min_length=2, max_length=16, pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$"),
    ] = None
    game_version: Annotated[str | None, Field(min_length=1, max_length=50)] = None
    topic: Annotated[str | None, Field(min_length=1, max_length=100)] = None
    entity_type: Annotated[str | None, Field(min_length=1, max_length=100)] = None
    source_type: SourceType | None = None
    statuses: Annotated[list[DocumentStatus], Field(min_length=1)] = Field(
        default_factory=lambda: ["active"]
    )
    min_reliability: Annotated[int | None, Field(ge=1, le=5)] = None
