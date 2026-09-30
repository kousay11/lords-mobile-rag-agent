#!/usr/bin/env python3
"""Collecte officielle fraîche 2026 : guides IGG + changelog App Store -> .md + manifest.

Usage:
  python scripts/scrape_official_2026.py --dry-run
  python scripts/scrape_official_2026.py --execute
  python scripts/scrape_official_2026.py --execute --source-id official-igg-heroes-2026

Sécurité : allowlist YAML uniquement, pas de crawl, délai poli, 20MB max.
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "lords-mobile"
DEFAULT_SOURCES = DEFAULT_DATA_DIR / "sources-official-2026.yaml"
MAX_BYTES = 20 * 1024 * 1024
BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def load_yaml(path: Path):
    import yaml  # type: ignore

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return (
        [str(d).lower() for d in data.get("allowed_domains", [])],
        dict(data.get("defaults", {}) or {}),
        list(data.get("sources", []) or []),
    )


def check_url(url: str, allowed: list[str]) -> None:
    host = urlparse(url).netloc.lower().split(":")[0]
    if not any(host == d or host.endswith("." + d) for d in allowed):
        raise ValueError(f"Domaine non autorisé: {host}")


def fetch(url: str) -> str:
    import requests  # type: ignore

    r = requests.get(
        url,
        headers={"User-Agent": BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"},
        timeout=45,
    )
    r.raise_for_status()
    if len(r.content) > MAX_BYTES:
        raise ValueError("Réponse trop volumineuse")
    return r.text


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.out: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "nav", "footer", "header", "form", "aside"}:
            self._skip += 1
            return
        if self._skip:
            return
        if tag in {"h1", "h2", "h3"}:
            self.out.append("\n\n" + {"h1": "# ", "h2": "## ", "h3": "### "}[tag])
        elif tag in {"p", "li"}:
            self.out.append("\n- " if tag == "li" else "\n\n")
        elif tag == "br":
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "footer", "header", "form", "aside"}:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._skip:
            return
        t = re.sub(r"\s+", " ", html_lib.unescape(data))
        if t.strip():
            self.out.append(t)


def html_to_md(html: str, title: str, url: str, note: str) -> str:
    p = _TextExtractor()
    p.feed(html)
    body = re.sub(r"\n{3,}", "\n\n", "".join(p.out)).strip()
    header = f"# {title}\n\n> Source: {url}\n> {note}\n\n"
    return header + body + "\n"


def extract_appstore_versions(html: str) -> str:
    """Extrait l'historique des versions App Store (notes 2026 : Transformers, Angry Birds...)."""
    # L'HTML App Store embarque du JSON avec "versionHistory"
    blocks = re.findall(r"\"releaseNotes\"\\?:\\?\"(.*?)\\?\"[,}]", html)
    versions = re.findall(r"\"versionDisplay\"\\?:\\?\"(.*?)\\?\"", html)
    lines = []
    for i, note in enumerate(blocks[:8]):
        ver = versions[i] if i < len(versions) else f"v{i+1}"
        clean = note.encode().decode("unicode_escape", errors="ignore")
        clean = re.sub(r"\\n", "\n", clean)
        clean = html_lib.unescape(clean).strip()
        if len(clean) > 50:
            lines.append(f"\n## Version {ver}\n\n{clean}\n")
    if not lines:
        # fallback : cherche "Version History" en texte
        m = re.search(r"Version History.{0,5000}", html, re.DOTALL)
        fallback = html_to_md(m.group(0) if m else html[:20000], "Changelog", "", "") if m else ""
        return fallback
    return "\n".join(lines)


def extract_published_date(html: str) -> str | None:
    """Read an explicit publication date; collection time is never publication time."""
    text = html_lib.unescape(re.sub(r"<[^>]+>", " ", html))
    match = re.search(r"Published\s*[:：]\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def manifest_records(manifest: Path) -> dict:
    out = {}
    if manifest.is_file():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                rec = json.loads(line)
                out[str(rec["id"])] = rec
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    ap.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--delay-seconds", type=float, default=1.5)
    ap.add_argument("--source-id", action="append", dest="source_ids", default=None)
    args = ap.parse_args()

    allowed, defaults, sources = load_yaml(args.sources.resolve())
    if args.source_ids:
        sources = [s for s in sources if str(s.get("id")) in set(args.source_ids)]
    manifest = args.data_dir.resolve() / "manifest.jsonl"
    records = manifest_records(manifest)
    today = datetime.now(timezone.utc)

    planned = 0
    for src in sources:
        sid, url = str(src["id"]), str(src["url"])
        rel, kind = str(src["output_path"]), str(src.get("kind", "igg-guide"))
        try:
            check_url(url, allowed)
        except ValueError as e:
            print(f"SKIP {sid}: {e}")
            continue
        planned += 1
        if not args.execute:
            print(f"PLAN {sid}: {url} -> {rel} [{kind}]")
            continue
        target = (args.data_dir.resolve() / rel).resolve()
        if target.exists() and not args.overwrite:
            print(f"SKIP {sid}: existe déjà")
            continue
        print(f"DOWNLOAD {sid}: {url}")
        html = fetch(url)
        if kind == "appstore-changelog":
            body = extract_appstore_versions(html)
            md = (
                f"# {src['title']}\n\n> Source: {url}\n"
                f"> Changelog officiel Apple App Store collecté le {today.date().isoformat()} "
                f"(collabs 2026 : Transformers, Angry Birds, World Championship — vérifier en jeu).\n"
                + body + "\n"
            )
        else:
            md = html_to_markdown_igg(html, str(src["title"]), url, today)
        if len(md) < 500:
            print(f"  WARN {sid}: contenu court ({len(md)} chars)")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(md, encoding="utf-8")
        print(f"  SAVED {len(md)} chars -> {rel}")
        records[sid] = {
            "id": sid,
            "path": rel,
            "title": src["title"],
            "source": src["source"],
            "url": url,
            "source_type": "official",
            "language": "en",
            "game_version": src.get("game_version", defaults.get("game_version", "2026-review")),
            "published_at": extract_published_date(html) if kind == "igg-guide" else None,
            "collected_at": today.isoformat().replace("+00:00", "Z"),
            "topics": src.get("topics", ["update-notes"]),
            "entity_type": src.get("entity_type", "guide"),
            "entity_name": src.get("entity_name", sid),
            "reliability": int(src.get("reliability", 4)),
            "status": src.get("status", defaults.get("status", "needs_review")),
        }
        time.sleep(max(0.0, args.delay_seconds))

    if args.execute and planned:
        manifest.write_text(
            "\n".join(json.dumps(records[k], ensure_ascii=False) for k in sorted(records)) + "\n",
            encoding="utf-8",
        )
        print(f"Manifest: {len(records)} entrées")
    print(f"{planned} source(s) {'traitée(s)' if args.execute else 'planifiée(s)'}.")
    return 0


def html_to_markdown_igg(html: str, title: str, url: str, today) -> str:
    return html_to_md(
        html, title, url,
        f"Guide officiel IGG refresh le {today.date().isoformat()} — vérifier les valeurs en jeu.",
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as e:
        print(f"Scrape 2026 failed: {e}", file=sys.stderr)
        raise SystemExit(1)
