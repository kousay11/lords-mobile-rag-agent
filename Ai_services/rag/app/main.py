import os
import asyncio
import json
from fastapi import FastAPI, Form, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from embeddings import (
    get_inference_embedder,
    get_ingest_embedder,
    download_progress,
)
from vector_store import VectorStoreClient
from models import (
    BatchIngestRequest,
    IngestTextRequest,
    LordsMobileMetadata,
    RetrieveRequest,
)
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

models = {}
warmup_state = {
    "status": "idle",
    "last_error": None,
}
warmup_lock = asyncio.Lock()
ingest_lock = asyncio.Lock()

init_state = {
    "status": "idle",  # idle | loading | ready | error
    "last_error": None,
}
init_lock = asyncio.Lock()


def _warmup_response():
    return {
        "status": warmup_state["status"],
        "last_error": warmup_state["last_error"],
    }


async def _run_warmup():
    if "embedder" not in models or "vs" not in models:
        return

    async with warmup_lock:
        if warmup_state["status"] == "ready":
            return

        warmup_state["status"] = "warming"
        warmup_state["last_error"] = None

        try:
            warmup_vec = models["embedder"].encode(["lords mobile guide warmup"])
            _ = warmup_vec.tolist()
            await asyncio.to_thread(models["vs"].total_chunks)
            warmup_state["status"] = "ready"
        except Exception as e:
            warmup_state["status"] = "error"
            warmup_state["last_error"] = str(e)


async def _init_models():
    async with init_lock:
        if init_state["status"] in ("loading", "ready"):
            return

        init_state["status"] = "loading"
        init_state["last_error"] = None

        try:
            embedder = await asyncio.to_thread(get_inference_embedder)
            models["embedder"] = embedder
        except Exception as e:
            init_state["status"] = "error"
            init_state["last_error"] = f"Embedder init failed: {e}"
            return

        max_retries = int(os.getenv("QDRANT_INIT_MAX_RETRIES", "30"))
        retry_delay = float(os.getenv("QDRANT_INIT_RETRY_DELAY_SEC", "2"))
        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                models["vs"] = VectorStoreClient(embedder=models["embedder"])
                last_error = None
                break
            except Exception as e:
                last_error = e
                if attempt == max_retries:
                    break
                print(
                    f"Qdrant not ready yet (attempt {attempt}/{max_retries}): {e}. "
                    f"Retrying in {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)

        if last_error is not None:
            init_state["status"] = "error"
            init_state["last_error"] = f"Vector store init failed: {last_error}"
            return

        init_state["status"] = "ready"
        init_state["last_error"] = None
        warmup_state["status"] = "idle"
        warmup_state["last_error"] = None
        asyncio.create_task(_run_warmup())


async def _get_ingest_embedder():
    async with ingest_lock:
        if "ingest_embedder" not in models:
            models["ingest_embedder"] = await asyncio.to_thread(get_ingest_embedder)
    return models["ingest_embedder"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading AI models and connecting to DB...")
    models.clear()
    warmup_state["status"] = "idle"
    warmup_state["last_error"] = None
    init_state["status"] = "idle"
    init_state["last_error"] = None

    asyncio.create_task(_init_models())
    print("System starting (background init).")
    yield
    models.clear()
    warmup_state["status"] = "idle"
    warmup_state["last_error"] = None
    init_state["status"] = "idle"
    init_state["last_error"] = None


app = FastAPI(title="Lords Mobile RAG Service", version="1.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
ALLOWED_FILE_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


def _require_ready():
    if init_state["status"] == "error":
        raise HTTPException(
            status_code=503,
            detail=init_state["last_error"] or "RAG service failed to initialize",
        )
    if "embedder" not in models or "vs" not in models:
        raise HTTPException(status_code=503, detail="Models still loading")


@app.get("/health")
async def health():
    progress = 100.0 if init_state["status"] == "ready" else download_progress["percentage"]

    payload = {
        "service": "rag",
        "status": "starting",
        "init": {
            "status": init_state["status"],
            "last_error": init_state["last_error"],
            "progress": progress
        },
        "warmup": _warmup_response(),
    }

    if init_state["status"] == "error":
        payload["status"] = "degraded"
        return payload

    if "embedder" in models and "vs" in models and init_state["status"] == "ready":
        payload["status"] = "ok"
    return payload


@app.post("/warmup")
async def warmup():
    if init_state["status"] != "ready":
        asyncio.create_task(_init_models())

    _require_ready()

    if warmup_state["status"] != "warming" and warmup_state["status"] != "ready":
        asyncio.create_task(_run_warmup())

    return _warmup_response()


@app.post("/ingest/text")
async def ingest_text(req: IngestTextRequest):
    _require_ready()
    try:
        ids = models["vs"].ingest_text(
            req.text, req.metadata.model_dump(mode="json"), models["embedder"]
        )
        return {"ingested_chunks": len(ids), "ids": ids}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    metadata: str = Form(..., description="JSON Lords Mobile document metadata"),
):
    _require_ready()
    try:
        filename = file.filename or "unknown"
        extension = os.path.splitext(filename)[1].lower()
        if extension not in ALLOWED_FILE_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file extension: {extension or '<none>'}",
            )
        try:
            document_metadata = LordsMobileMetadata.model_validate_json(metadata)
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=json.loads(error.json())) from error

        content = await file.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {MAX_UPLOAD_BYTES}-byte upload limit",
            )
        text = (
            models["vs"].extract_pdf_text(content)
            if extension == ".pdf"
            else content.decode("utf-8")
        )
        if not text.strip():
            raise HTTPException(
                status_code=422, detail="The document contains no extractable text"
            )
        ids = models["vs"].ingest_text(
            text, document_metadata.model_dump(mode="json"), models["embedder"]
        )
        return {"filename": filename, "ingested_chunks": len(ids), "ids": ids}
    except HTTPException:
        raise
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=422, detail="Text files must be UTF-8 encoded") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/batch")
async def ingest_batch(req: BatchIngestRequest):
    _require_ready()
    try:
        ingest_embedder = await _get_ingest_embedder()
        total = len(req.documents)
        ingested = 0
        chunks = 0
        errors = []
        document_details = []

        for idx, doc in enumerate(req.documents):
            try:
                result = models["vs"].ingest_text_with_details(
                    doc.text, doc.metadata.model_dump(mode="json"), ingest_embedder
                )
                ingested += 1
                chunks += result["chunks_created"]
                document_details.append({
                    "index": idx,
                    "source": doc.metadata.source,
                    "title": doc.metadata.title,
                    "status": "success",
                    "chunks_created": result["chunks_created"],
                    "chunks_filtered": result["chunks_filtered"],
                    "chunk_previews": [c[:120] for c in result["chunk_texts"][:3]],
                })
            except Exception as e:
                errors.append({"index": idx, "error": str(e), "source": doc.metadata.source})
                document_details.append({
                    "index": idx,
                    "source": doc.metadata.source,
                    "title": doc.metadata.title,
                    "status": "error",
                    "error": str(e),
                })

        return {
            "total_documents": total,
            "ingested_documents": ingested,
            "total_chunks": chunks,
            "errors": errors,
            "document_details": document_details,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retrieve")
async def retrieve(req: RetrieveRequest):
    _require_ready()
    try:
        if req.search_type == "hybrid":
            chunks = models["vs"].hybrid_search(
                query=req.query,
                embedder=models["embedder"],
                top_k=req.top_k,
                language=req.language,
                topic=req.topic,
                entity_type=req.entity_type,
                source_type=req.source_type,
                statuses=req.statuses,
                min_reliability=req.min_reliability,
                min_score=req.min_relevance_score,
            )
        elif req.search_type == "semantic":
            vec = models["embedder"].encode([req.query]).tolist()[0]
            chunks = models["vs"].search(
                vec,
                top_k=req.top_k,
                language=req.language,
                topic=req.topic,
                entity_type=req.entity_type,
                source_type=req.source_type,
                statuses=req.statuses,
                min_reliability=req.min_reliability,
                min_score=req.min_relevance_score,
            )
        elif req.search_type == "keyword":
            # Keyword-only search using sparse vectors
            chunks = models["vs"].keyword_search(
                query=req.query,
                embedder=models["embedder"],
                top_k=req.top_k,
                language=req.language,
                topic=req.topic,
                entity_type=req.entity_type,
                source_type=req.source_type,
                statuses=req.statuses,
                min_reliability=req.min_reliability,
                min_score=req.min_relevance_score,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid search_type: {req.search_type}",
            )
        return {"chunks": chunks, "query": req.query, "search_type": req.search_type}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def list_documents(limit: int = 500):
    _require_ready()
    try:
        rows = models["vs"].list_documents(limit=limit)
        total_chunks = models["vs"].total_chunks()
        return {
            "data": rows,
            "total_documents": len(rows),
            "total_chunks": total_chunks,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    _require_ready()
    try:
        deleted_chunks = models["vs"].delete_document(document_id)
        if deleted_chunks == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        return {
            "document_id": document_id,
            "deleted_chunks": deleted_chunks,
            "status": "deleted",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collection")
async def reset_collection():
    _require_ready()
    try:
        models["vs"].reset_collection()
        return {"status": "collection reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
