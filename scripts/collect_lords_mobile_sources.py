#!/usr/bin/env python3
"""Collect only explicitly approved Lords Mobile source files.

The script does not crawl websites, authenticate to third parties, or interact
with Lords Mobile. It reads download_url values from the local manifest and is
dry-run by default.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "lords-mobile"
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024


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


def safe_target(data_dir: Path, relative_path: str) -> Path:
    target = (data_dir / relative_path).resolve()
    root = data_dir.resolve()
    if root != target and root not in target.parents:
        raise ValueError(f"Refusing a path outside the corpus: {relative_path}")
    return target


def validate_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError(f"Only explicit HTTP(S) download URLs are supported: {raw_url}")
    return raw_url


def download(url: str, target: Path) -> None:
    request = Request(url, headers={"User-Agent": "LordsMobileGuideCorpus/0.1"})
    with urlopen(request, timeout=30) as response:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
            raise ValueError(f"Download exceeds {MAX_DOWNLOAD_BYTES} bytes: {url}")

        target.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("wb", delete=False, dir=target.parent) as temporary:
            downloaded = 0
            while chunk := response.read(64 * 1024):
                downloaded += len(chunk)
                if downloaded > MAX_DOWNLOAD_BYTES:
                    raise ValueError(f"Download exceeds {MAX_DOWNLOAD_BYTES} bytes: {url}")
                temporary.write(chunk)
            temporary_path = Path(temporary.name)

    shutil.move(str(temporary_path), target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--execute", action="store_true", help="Perform the approved downloads.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing local file.")
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    manifest = data_dir / "manifest.jsonl"
    if not manifest.is_file():
        parser.error(f"Manifest not found: {manifest}")

    records = read_manifest(manifest)
    planned = 0
    for record in records:
        source_id = str(record.get("id", "<missing id>"))
        relative_path = record.get("path")
        url = record.get("download_url")
        if not relative_path or not url:
            print(f"SKIP {source_id}: requires both path and download_url")
            continue

        target = safe_target(data_dir, str(relative_path))
        validate_url(str(url))
        planned += 1
        if not args.execute:
            print(f"PLAN {source_id}: {url} -> {target.relative_to(data_dir)}")
            continue
        if target.exists() and not args.overwrite:
            print(f"SKIP {source_id}: target already exists ({target.relative_to(data_dir)})")
            continue

        print(f"DOWNLOAD {source_id}: {url}")
        download(str(url), target)
        time.sleep(max(0.0, args.delay_seconds))

    print(f"{planned} approved download(s) {'completed' if args.execute else 'planned'}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"Collection failed: {error}", file=sys.stderr)
        raise SystemExit(1)
