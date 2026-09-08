#!/usr/bin/env python3
"""Ingest approved local Markdown and text documents into the RAG service.

This script never downloads documents and never performs game or account
actions. It only sends local files explicitly listed in the corpus manifest to
the internal RAG /ingest/batch endpoint.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "lords-mobile"
TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}


def read_manifest(path: Path) -> list[dict]:
    records: list[dict] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON in {path}:{line_number}: {error.msg}") from error
        if not isinstance(record, dict):
            raise ValueError(f"Expected an object in {path}:{line_number}")
        records.append(record)
    return records


def safe_source_path(data_dir: Path, relative_path: str) -> Path:
    source = (data_dir / relative_path).resolve()
    root = data_dir.resolve()
    if root != source and root not in source.parents:
        raise ValueError(f"Refusing a path outside the corpus: {relative_path}")
    return source


def to_document(data_dir: Path, record: dict) -> dict | None:
    relative_path = record.get("path")
    if not relative_path:
        raise ValueError(f"Source {record.get('id', '<unknown>')} has no path")

    source_path = safe_source_path(data_dir, str(relative_path))
    if not source_path.is_file():
        raise ValueError(f"Source file not found: {source_path}")
    if source_path.suffix.lower() not in TEXT_EXTENSIONS:
        print(f"SKIP {record.get('id', source_path.name)}: PDF ingestion will be added with the document pipeline")
        return None

    required = (
        "id", "title", "source", "source_type", "language", "game_version",
        "topics", "reliability", "status",
    )
    missing = [field for field in required if record.get(field) in (None, "")]
    if missing:
        raise ValueError(f"Source {record.get('id', source_path.name)} is missing: {', '.join(missing)}")

    metadata = {
        key: value
        for key, value in record.items()
        if key not in {"id", "path", "download_url"}
    }
    metadata["document_id"] = str(record["id"])
    metadata["source"] = metadata.get("source") or source_path.name
    return {"text": source_path.read_text(encoding="utf-8"), "metadata": metadata}


def post_batch(rag_url: str, documents: list[dict]) -> dict:
    body = json.dumps({"documents": documents}).encode("utf-8")
    request = Request(
        rag_url.rstrip("/") + "/ingest/batch",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--rag-url", default="http://localhost:8001")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument(
        "--document-id",
        action="append",
        dest="document_ids",
        help="Ingest only this manifest document id; repeat for multiple documents.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")

    data_dir = args.data_dir.resolve()
    records = read_manifest(data_dir / "manifest.jsonl")
    if args.document_ids:
        requested_ids = set(args.document_ids)
        known_ids = {str(record.get("id")) for record in records}
        unknown_ids = sorted(requested_ids - known_ids)
        if unknown_ids:
            raise ValueError(f"Unknown document id(s): {', '.join(unknown_ids)}")
        records = [record for record in records if str(record.get("id")) in requested_ids]
    documents = [document for record in records if (document := to_document(data_dir, record))]
    print(f"Prepared {len(documents)} local text document(s).")
    if args.dry_run:
        for document in documents:
            print(f"PLAN {document['metadata']['document_id']}: {document['metadata']['title']}")
        return 0

    for offset in range(0, len(documents), args.batch_size):
        batch = documents[offset : offset + args.batch_size]
        result = post_batch(args.rag_url, batch)
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (HTTPError, URLError, OSError, ValueError) as error:
        print(f"Ingestion failed: {error}", file=sys.stderr)
        raise SystemExit(1)
