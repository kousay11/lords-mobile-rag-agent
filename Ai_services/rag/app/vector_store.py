import os
import uuid
import io
import math
import hashlib
import re
from datetime import datetime, timezone
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchAny,
    MatchValue,
    FilterSelector,
    SparseVector,
    SparseVectorParams,
    Modifier,
    PayloadSchemaType,
    Prefetch,
    Fusion,
    FusionQuery,
    Range,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from dotenv import load_dotenv
import numpy as np
from scipy.spatial.distance import cosine

load_dotenv()


# ── Common stopwords to ignore in sparse vectors ──────────────────────────────
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "are",
    "were", "been", "has", "have", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "this", "that",
    "these", "those", "not", "no", "nor", "so", "if", "then", "than",
    "too", "very", "just", "about", "above", "after", "again", "all",
    "also", "am", "any", "because", "before", "between", "both", "each",
    "few", "further", "get", "he", "her", "here", "him", "his", "how",
    "i", "into", "its", "let", "me", "more", "most", "my", "myself",
    "new", "now", "only", "other", "our", "out", "over", "own", "same",
    "she", "some", "such", "them", "there", "they", "through", "up",
    "us", "we", "what", "when", "which", "while", "who", "whom", "why",
    "you", "your",
})


def normalize_score(score: float, search_type: str, is_rrf: bool = False) -> float:
    """
    Normalize search scores to 0-1 range for consistent display.

    Args:
        score: Raw score from Qdrant
        search_type: "hybrid", "semantic", or "keyword"
        is_rrf: Whether this is an RRF-fused score

    Returns:
        Normalized score between 0 and 1
    """
    if is_rrf or search_type == "hybrid":
        return min(1.0, max(0.0, score * 1.5))

    elif search_type == "semantic":
        return max(0.0, min(1.0, (score + 1.0) / 2.0))

    elif search_type == "keyword":
        return 1.0 / (1.0 + math.exp(-score / 10.0))

    return max(0.0, min(1.0, score))


COLLECTION = os.getenv("QDRANT_COLLECTION", "lords_mobile_knowledge")
VECTOR_SIZE = 1024  # Qwen3-Embedding-0.6B dense dimension
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1024))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 128))


class VectorStoreClient:
    def __init__(self, embedder=None):
        self.client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "qdrant"),
            port=int(os.getenv("QDRANT_PORT", 6333)),
        )
        self.embedder = embedder
        self._ensure_collection()

    def _create_collection(self):
        self.client.create_collection(
            collection_name=COLLECTION,
            vectors_config={
                "dense": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(modifier=Modifier.IDF)
            },
        )
        self._create_payload_indexes()

    def _collection_matches_expected_schema(self) -> bool:
        try:
            collection_info = self.client.get_collection(collection_name=COLLECTION)
        except Exception as ex:
            raise RuntimeError(
                f"Could not verify Qdrant collection {COLLECTION!r}; "
                f"refusing to modify it: {ex}"
            ) from ex

        params = getattr(getattr(collection_info, "config", None), "params", None)
        vectors = getattr(params, "vectors", None)
        sparse_vectors = getattr(params, "sparse_vectors", None)

        dense_config = None
        if isinstance(vectors, dict):
            dense_config = vectors.get("dense")
        elif vectors is not None:
            dense_config = vectors

        sparse_config = None
        if isinstance(sparse_vectors, dict):
            sparse_config = sparse_vectors.get("sparse")
        elif sparse_vectors is not None:
            sparse_config = sparse_vectors

        if dense_config is None or sparse_config is None:
            return False

        dense_distance = getattr(dense_config, "distance", None)
        sparse_modifier = getattr(sparse_config, "modifier", None)

        return (
            getattr(dense_config, "size", None) == VECTOR_SIZE
            and str(dense_distance).lower() == str(Distance.COSINE).lower()
            and str(sparse_modifier).lower() == str(Modifier.IDF).lower()
        )

    def _create_payload_indexes(self):
        index_definitions = (
            ("document_id", PayloadSchemaType.KEYWORD),
            ("source_type", PayloadSchemaType.KEYWORD),
            ("language", PayloadSchemaType.KEYWORD),
            ("topics", PayloadSchemaType.KEYWORD),
            ("entity_type", PayloadSchemaType.KEYWORD),
            ("status", PayloadSchemaType.KEYWORD),
            ("reliability", PayloadSchemaType.INTEGER),
        )
        for field_name, field_schema in index_definitions:
            try:
                self.client.create_payload_index(
                    collection_name=COLLECTION,
                    field_name=field_name,
                    field_schema=field_schema,
                )
            except Exception as error:
                print(f"Warning: could not create payload index {field_name}: {error}")

    def _ensure_collection(self):
        names = [c.name for c in self.client.get_collections().collections]
        if COLLECTION not in names:
            self._create_collection()
            return

        if not self._collection_matches_expected_schema():
            raise RuntimeError(
                f"Qdrant collection {COLLECTION!r} exists with an incompatible schema; "
                "refusing to delete/recreate it automatically. "
                "Resolve the mismatch manually instead."
            )

        self._create_payload_indexes()

    def _split_into_segments(self, text: str) -> list[tuple[str, str]]:
        """Split text into prose and code block segments.

        Returns list of (type, content) tuples where type is 'prose' or 'code'.
        """
        segments = []
        code_pattern = re.compile(r'```[\s\S]*?```', re.MULTILINE)
        prose_parts = code_pattern.split(text)

        code_matches = code_pattern.finditer(text)
        code_positions = [(m.start(), m.end(), m.group()) for m in code_matches]

        prose_idx = 0
        for start, end, code_content in code_positions:
            if prose_idx < start:
                prose = text[prose_idx:start].strip()
                if prose:
                    segments.append(("prose", prose))
            segments.append(("code", code_content.strip()))
            prose_idx = end

        if prose_idx < len(text):
            prose = text[prose_idx:].strip()
            if prose:
                segments.append(("prose", prose))

        if not segments:
            segments.append(("prose", text.strip()))

        return segments

    def _merge_code_to_chunks(self, chunks: list[str], code_blocks: list[str]) -> list[str]:
        """Merge code blocks into the nearest adjacent chunks."""
        if not code_blocks or not chunks:
            return chunks + code_blocks

        result = []
        code_idx = 0

        for chunk in chunks:
            if code_idx < len(code_blocks):
                combined = chunk + "\n\n" + code_blocks[code_idx]
                result.append(combined)
                code_idx += 1
            else:
                result.append(chunk)

        while code_idx < len(code_blocks):
            result.append(code_blocks[code_idx])
            code_idx += 1

        return result

    def _semantic_split(
        self,
        text: str,
        threshold: float = 0.75,
        embedder=None,
    ) -> list[str]:
        """Chunk text by semantic similarity using embeddings (no LLM needed).

        Algorithm:
        1. Split text into segments (prose and code blocks)
        2. Apply semantic chunking to prose segments
        3. Preserve code blocks as atomic units, merge to adjacent chunks
        4. Handle very long code blocks with fallback splitter
        """
        embedder = embedder or self.embedder
        if not embedder:
            return []

        segments = self._split_into_segments(text)
        chunks: list[str] = []
        code_blocks: list[str] = []

        for seg_type, seg_content in segments:
            if seg_type == "code":
                if len(seg_content) > 500:
                    try:
                        splitter = RecursiveCharacterTextSplitter(
                            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
                        )
                        code_chunks = splitter.split_text(seg_content)
                        code_blocks.extend([c for c in code_chunks if c.strip()])
                    except Exception:
                        code_blocks.append(seg_content)
                else:
                    code_blocks.append(seg_content)
            else:
                prose_chunks = self._chunk_prose(seg_content, threshold, embedder)
                chunks.extend(prose_chunks)

        if not chunks and not code_blocks:
            return []

        if chunks:
            chunks = self._merge_code_to_chunks(chunks, code_blocks)
        else:
            chunks = code_blocks

        return [c.strip() for c in chunks if c.strip()]

    def _chunk_prose(self, prose: str, threshold: float, embedder) -> list[str]:
        """Apply semantic chunking to a prose segment."""
        sentences = re.split(r'(?<=[.!?])\s+', prose.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 1:
            # Short segments: keep if long enough, filter out question fragments
            text = sentences[0] if sentences else ""
            if len(text) < 40:
                return []
            return sentences

        if not sentences:
            return []
            return sentences

        batch_size = 64
        embeddings = []
        for i in range(0, len(sentences), batch_size):
            batch = sentences[i:i + batch_size]
            emb = embedder.encode(batch, show_progress_bar=False)
            embeddings.extend(emb.tolist())

        embeddings = np.array(embeddings)

        similarities = []
        for i in range(len(sentences) - 1):
            sim = 1.0 - cosine(embeddings[i], embeddings[i + 1])
            similarities.append(sim)

        if threshold == "percentile":
            threshold = float(os.getenv("SEMANTIC_CHUNK_THRESHOLD", "85")) / 100.0
            threshold = np.percentile(similarities, threshold)

        break_points = []
        for i, sim in enumerate(similarities):
            if sim < threshold:
                break_points.append(i + 1)

        if not break_points:
            return sentences

        chunks = []
        start = 0
        for bp in break_points:
            chunk = " ".join(sentences[start:bp])
            if chunk.strip():
                chunks.append(chunk.strip())
            start = bp
        if start < len(sentences):
            chunk = " ".join(sentences[start:])
            if chunk.strip():
                chunks.append(chunk.strip())

        return chunks

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into meaningful terms, filtering stopwords and short tokens.

        Unicode-aware: matches letter sequences in any script (Latin, Arabic, ...),
        including hyphenated compounds. ASCII-only patterns would silently drop
        Arabic terms and leave keyword search mute on them.
        """
        tokens = re.findall(r"[^\W\d_]+(?:-[^\W\d_]+)*", text.lower(), flags=re.UNICODE)
        # Filter stopwords and very short tokens
        tokens = [t for t in tokens if t not in _STOPWORDS and len(t) > 2]
        return tokens

    def _generate_sparse_vector(self, text: str) -> SparseVector:
        """Generate sparse vector from text using TF-IDF-like hashing.

        Uses MD5-hashed token indices mapped to Qdrant's 65536 sparse index space.
        Weight = log(1 + tf) * log(N / df) approximation (IDF-like).
        Also generates bigrams for multi-word terms.
        """
        tokens = self._tokenize(text)
        if not tokens:
            return SparseVector(indices=[], values=[])

        # Term frequency
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1

        # Bigrams
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]}_{tokens[i + 1]}"
            tf[bigram] = tf.get(bigram, 0) + 1

        # Build sparse vector with IDF-like weighting
        # Simulate N=10000 (estimated corpus size) and df=1 for IDF max
        N = 10000
        index_to_weight: dict[int, float] = {}
        for token, count in tf.items():
            idx = int(hashlib.md5(token.encode()).hexdigest()[:8], 16) % 65536
            # log(1 + tf) * log(N / df) — IDF approx with df=1
            weight = math.log1p(count) * math.log(N + 1)
            index_to_weight[idx] = index_to_weight.get(idx, 0.0) + weight

        sorted_items = sorted(index_to_weight.items())
        return SparseVector(
            indices=[i for i, _ in sorted_items],
            values=[v for _, v in sorted_items],
        )

    def _build_chunk_payload(
        self, chunk: str, metadata: dict, chunk_index: int
    ) -> dict:
        """Keep each chunk traceable to its validated Lords Mobile document."""
        return {
            "text": chunk,
            "document_id": metadata.get("document_id", ""),
            "source": metadata.get("source", ""),
            "url": metadata.get("url"),
            "title": metadata.get("title", ""),
            "source_type": metadata.get("source_type", ""),
            "language": metadata.get("language", ""),
            "published_at": metadata.get("published_at"),
            "collected_at": metadata.get("collected_at"),
            "topics": metadata.get("topics", []),
            "entity_type": metadata.get("entity_type"),
            "entity_name": metadata.get("entity_name"),
            "tags": metadata.get("tags", []),
            "reliability": metadata.get("reliability", 0),
            "status": metadata.get("status", "needs_review"),
            "chunk_index": chunk_index,
            "parent_doc_hash": metadata.get("content_hash", ""),
            "ingested_at": metadata.get("ingested_at", ""),
        }

    @staticmethod
    def _prepare_document_metadata(text: str, metadata: dict) -> dict:
        prepared = dict(metadata or {})
        prepared.setdefault("ingested_at", datetime.now(timezone.utc).isoformat())
        computed_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        supplied_hash = prepared.get("content_hash")
        if supplied_hash and supplied_hash != computed_hash:
            raise ValueError("content_hash does not match the document text")
        prepared["content_hash"] = computed_hash
        return prepared

    @staticmethod
    def _point_id(document_id: str, content_hash: str, chunk_index: int) -> str:
        return str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"lords-mobile:{document_id}:{content_hash}:{chunk_index}",
            )
        )

    def _remove_superseded_chunks(self, document_id: str, content_hash: str) -> None:
        """Remove older revisions only after the new revision has been upserted."""
        old_revision_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id", match=MatchValue(value=document_id)
                )
            ],
            must_not=[
                FieldCondition(
                    key="parent_doc_hash", match=MatchValue(value=content_hash)
                )
            ],
        )
        self.client.delete(
            collection_name=COLLECTION,
            points_selector=FilterSelector(filter=old_revision_filter),
            wait=True,
        )

    def ingest_text(self, text: str, metadata: dict, embedder=None) -> list[str]:
        embedder = embedder or self.embedder
        payload_metadata = self._prepare_document_metadata(text, metadata)

        # Use semantic chunking (falls back to recursive if embedder unavailable)
        try:
            chunks = self._semantic_split(text, embedder=embedder)
        except Exception:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
            )
            chunks = splitter.split_text(text)
        
        if not chunks:
            return []

        # Filter out low-quality chunks: too short, question-only fragments, or bare titles.
        # Threshold kept low (~40 chars) so short but relevant statements survive
        # while boilerplate fragments are still removed.
        valid_chunks = []
        for chunk in chunks:
            stripped = chunk.strip()
            if len(stripped) < 40:
                continue
            # Skip question-only fragments (ends with ? and is short)
            if stripped.endswith('?') and len(stripped) < 100:
                continue
            # Skip explicit question titles: "Q: ..." prefix
            if re.match(r'^Q:\s*', stripped, re.IGNORECASE):
                continue
            valid_chunks.append(chunk)

        if not valid_chunks:
            return []

        chunks = valid_chunks
        dense_vectors = embedder.encode(chunks).tolist()

        points, ids = [], []
        for chunk_idx, (chunk, dense_vec) in enumerate(zip(chunks, dense_vectors)):
            pid = self._point_id(
                payload_metadata["document_id"],
                payload_metadata["content_hash"],
                chunk_idx,
            )
            ids.append(pid)

            sparse_vec = self._generate_sparse_vector(chunk)
            
            payload = self._build_chunk_payload(chunk, payload_metadata, chunk_idx)
            payload["chunk_id"] = pid
            
            points.append(
                PointStruct(
                    id=pid,
                    vector={"dense": dense_vec, "sparse": sparse_vec},
                    payload=payload,
                )
            )
        try:
            self.client.upsert(collection_name=COLLECTION, points=points)
        except Exception:
            # Best-effort cleanup of this revision's new points only;
            # never touch other documents' points.
            try:
                self.client.delete(
                    collection_name=COLLECTION,
                    points_selector=ids,
                    wait=False,
                )
            except Exception:
                pass
            raise
        self._remove_superseded_chunks(
            payload_metadata["document_id"], payload_metadata["content_hash"]
        )
        return ids

    def ingest_text_with_details(self, text: str, metadata: dict, embedder=None) -> dict:
        """Like ingest_text but returns details about chunking and filtering."""
        embedder = embedder or self.embedder
        payload_metadata = self._prepare_document_metadata(text, metadata)

        # Use semantic chunking (falls back to recursive if embedder unavailable)
        try:
            chunks = self._semantic_split(text, embedder=embedder)
        except Exception:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
            )
            chunks = splitter.split_text(text)

        if not chunks:
            return {"chunks_created": 0, "chunks_filtered": 0, "chunk_texts": []}

        # Filter and track (threshold ~40 chars so short relevant statements survive)
        all_chunks = [c.strip() for c in chunks]
        valid_chunks = []
        for stripped in all_chunks:
            if len(stripped) < 40:
                continue
            if stripped.endswith('?') and len(stripped) < 100:
                continue
            if re.match(r'^Q:\s*', stripped, re.IGNORECASE):
                continue
            valid_chunks.append(stripped)

        chunks_filtered = len(all_chunks) - len(valid_chunks)

        if not valid_chunks:
            return {"chunks_created": 0, "chunks_filtered": chunks_filtered, "chunk_texts": []}

        # Embed and store
        chunks = valid_chunks
        dense_vectors = embedder.encode(chunks).tolist()
        points, ids = [], []
        for chunk_idx, (chunk, dense_vec) in enumerate(zip(chunks, dense_vectors)):
            pid = self._point_id(
                payload_metadata["document_id"],
                payload_metadata["content_hash"],
                chunk_idx,
            )
            ids.append(pid)
            sparse_vec = self._generate_sparse_vector(chunk)
            payload = self._build_chunk_payload(chunk, payload_metadata, chunk_idx)
            payload["chunk_id"] = pid
            points.append(
                PointStruct(
                    id=pid,
                    vector={"dense": dense_vec, "sparse": sparse_vec},
                    payload=payload,
                )
            )
        if points:
            try:
                self.client.upsert(collection_name=COLLECTION, points=points)
            except Exception:
                # Best-effort cleanup of this revision's new points only;
                # never touch other documents' points.
                try:
                    self.client.delete(
                        collection_name=COLLECTION,
                        points_selector=ids,
                        wait=False,
                    )
                except Exception:
                    pass
                raise
            self._remove_superseded_chunks(
                payload_metadata["document_id"], payload_metadata["content_hash"]
            )

        return {
            "chunks_created": len(ids),
            "chunks_filtered": chunks_filtered,
            "chunk_texts": [c[:200] for c in valid_chunks],
        }

    @staticmethod
    def _lords_mobile_filter_conditions(
        language: str = None,
        topic: str = None,
        entity_type: str = None,
        source_type: str = None,
        statuses: list[str] = None,
        min_reliability: int = None,
    ) -> list[FieldCondition]:
        conditions: list[FieldCondition] = []
        if language:
            conditions.append(FieldCondition(key="language", match=MatchValue(value=language)))
        if topic:
            conditions.append(FieldCondition(key="topics", match=MatchValue(value=topic)))
        if entity_type:
            conditions.append(
                FieldCondition(key="entity_type", match=MatchValue(value=entity_type))
            )
        if source_type:
            conditions.append(
                FieldCondition(key="source_type", match=MatchValue(value=source_type))
            )
        if statuses:
            conditions.append(FieldCondition(key="status", match=MatchAny(any=statuses)))
        if min_reliability is not None:
            conditions.append(
                FieldCondition(key="reliability", range=Range(gte=min_reliability))
            )
        return conditions

    def hybrid_search(
        self,
        query: str,
        embedder=None,
        top_k: int = 10,
        language: str = None,
        topic: str = None,
        entity_type: str = None,
        source_type: str = None,
        statuses: list[str] = None,
        min_reliability: int = None,
        min_score: float = 0.5,
    ) -> list[dict]:
        embedder = embedder or self.embedder

        dense_query_vector = embedder.encode([query]).tolist()[0]
        sparse_query_vector = self._generate_sparse_vector(query)

        filter_conditions = []

        filter_conditions.extend(
            self._lords_mobile_filter_conditions(
                language=language,
                topic=topic,
                entity_type=entity_type,
                source_type=source_type,
                statuses=statuses,
                min_reliability=min_reliability,
            )
        )

        search_filter = Filter(must=filter_conditions) if filter_conditions else None

        results = self.client.query_points(
            collection_name=COLLECTION,
            prefetch=[
                Prefetch(
                    query=dense_query_vector,
                    using="dense",
                    limit=top_k * 2,
                    filter=search_filter,
                ),
                Prefetch(
                    query=sparse_query_vector,
                    using="sparse",
                    limit=top_k * 2,
                    filter=search_filter,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )

        normalized_results = []
        for r in results.points:
            norm_score = normalize_score(r.score, "hybrid", is_rrf=True)

            if norm_score >= min_score:
                payload = r.payload or {}
                text = payload.get("text", "")

                normalized_results.append(
                    {
                        "text": text,
                        "score": norm_score,
                        "raw_score": float(r.score),
                        "metadata": {
                            key: value
                            for key, value in payload.items()
                            if key != "text"
                        },
                    }
                )

  # Fallback: if hybrid returns too few results, try dense-only
        if len(normalized_results) < 3:
            dense_results = self.search(
                dense_query_vector, top_k=top_k * 2,
                language=language, topic=topic,
                entity_type=entity_type, source_type=source_type,
                statuses=statuses, min_reliability=min_reliability,
                min_score=min_score,
            )
            existing_texts = {r["text"] for r in normalized_results}
            for r in dense_results:
                if r["text"] not in existing_texts:
                    normalized_results.append({
                        "text": r["text"],
                        "score": r["score"],
                        "raw_score": r["score"],
                        "metadata": r["metadata"],
                    })
                    existing_texts.add(r["text"])
                if len(normalized_results) >= top_k:
                    break

        # Both branches now carry normalized 0-1 scores: sort and trim.
        normalized_results.sort(key=lambda r: r["score"], reverse=True)
        return normalized_results[:top_k]

    def search(
        self, query_vector: list[float], top_k: int = 5,
        language: str = None, topic: str = None,
        entity_type: str = None, source_type: str = None,
        statuses: list[str] = None, min_reliability: int = None,
        min_score: float = 0.5,
    ) -> list[dict]:
        filter_conditions = []

        filter_conditions.extend(
            self._lords_mobile_filter_conditions(
                language=language,
                topic=topic,
                entity_type=entity_type,
                source_type=source_type,
                statuses=statuses,
                min_reliability=min_reliability,
            )
        )

        search_filter = Filter(must=filter_conditions) if filter_conditions else None

        results = self.client.query_points(
            collection_name=COLLECTION,
            query=query_vector,
            using="dense",
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
        )
        results_list = []
        for r in results.points:
            norm_score = normalize_score(r.score, "semantic")
            if norm_score < min_score:
                continue
            payload = r.payload or {}
            text = payload.get("text", "")
            results_list.append({
                "text": text,
                "score": norm_score,
                "raw_score": float(r.score),
                "metadata": {k: v for k, v in payload.items() if k != "text"}
            })
        return results_list

    def keyword_search(
        self,
        query: str,
        embedder=None,
        top_k: int = 10,
        language: str = None,
        topic: str = None,
        entity_type: str = None,
        source_type: str = None,
        statuses: list[str] = None,
        min_reliability: int = None,
        min_score: float = 0.5,
    ) -> list[dict]:
        """Keyword-only search using manually generated sparse vectors."""
        sparse_query_vector = self._generate_sparse_vector(query)

        filter_conditions = []

        filter_conditions.extend(
            self._lords_mobile_filter_conditions(
                language=language,
                topic=topic,
                entity_type=entity_type,
                source_type=source_type,
                statuses=statuses,
                min_reliability=min_reliability,
            )
        )

        search_filter = Filter(must=filter_conditions) if filter_conditions else None

        results = self.client.query_points(
            collection_name=COLLECTION,
            query=sparse_query_vector,
            using="sparse",
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
        )

        normalized_results = []
        for r in results.points:
            norm_score = normalize_score(r.score, "keyword")

            if norm_score >= min_score:
                payload = r.payload or {}
                text = payload.get("text", "")

                normalized_results.append(
                    {
                        "text": text,
                        "score": norm_score,
                        "raw_score": float(r.score),
                        "metadata": {
                            key: value
                            for key, value in payload.items()
                            if key != "text"
                        },
                    }
                )

        return normalized_results

    def list_documents(self, limit: int = 500) -> list[dict]:
        documents: dict[str, dict] = {}
        offset = None

        while True:
            points, next_offset = self.client.scroll(
                collection_name=COLLECTION,
                limit=250,
                with_payload=True,
                with_vectors=False,
                offset=offset,
            )

            for point in points:
                payload = point.payload or {}
                source = str(payload.get("source") or "unknown")
                document_id = str(payload.get("document_id") or source)
                ingested_at = payload.get("ingested_at")

                if document_id not in documents:
                    documents[document_id] = {
                        "document_id": document_id,
                        "source": source,
                        "title": payload.get("title") or source,
                        "source_type": payload.get("source_type"),
                        "language": payload.get("language"),
                        "topics": payload.get("topics", []),
                        "status": payload.get("status"),
                        "reliability": payload.get("reliability"),
                        "chunk_count": 0,
                        "last_updated": ingested_at,
                    }

                documents[document_id]["chunk_count"] += 1
                if ingested_at and (
                    documents[document_id]["last_updated"] is None or
                    ingested_at > documents[document_id]["last_updated"]
                ):
                    documents[document_id]["last_updated"] = ingested_at

            if next_offset is None or len(documents) >= limit:
                break
            offset = next_offset

        rows = list(documents.values())
        rows.sort(
            key=lambda item: (
                item.get("last_updated") or "",
                item.get("source") or "",
            ),
            reverse=True,
        )
        return rows[:limit]

    def delete_document(self, document_id: str) -> int:
        """Delete only points where document_id matches exactly (never by source)."""
        doc_filter = Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        )
        count_result = self.client.count(
            collection_name=COLLECTION,
            count_filter=doc_filter,
            exact=True,
        )
        deleted_chunks = count_result.count
        if deleted_chunks == 0:
            return 0

        self.client.delete(
            collection_name=COLLECTION,
            points_selector=FilterSelector(filter=doc_filter),
            wait=True,
        )
        return deleted_chunks

    def total_chunks(self) -> int:
        count_result = self.client.count(
            collection_name=COLLECTION,
            exact=True,
        )
        return count_result.count

    @staticmethod
    def extract_pdf_text(content: bytes) -> str:
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
