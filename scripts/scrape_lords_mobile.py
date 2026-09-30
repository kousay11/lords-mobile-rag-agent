#!/usr/bin/env python3
"""Scrape explicitly approved Lords Mobile sources into .md / .pdf corpus files.

Lit data/lords-mobile/sources.yaml (allowlist stricte), télécharge uniquement
les URLs déclarées, convertit HTML -> Markdown, sauvegarde les PDF tels quels,
et met à jour manifest.jsonl pour ingestion RAG ultérieure (admin ou script ingest).

Usage:
  python scripts/scrape_lords_mobile.py --dry-run        # plan (défaut)
  python scripts/scrape_lords_mobile.py --execute        # télécharge + manifest
  python scripts/scrape_lords_mobile.py --execute --overwrite
  python scripts/scrape_lords_mobile.py --execute --source-id wiki-hero-en-001

Sécurité stage d'été:
- domaines limités à allowed_domains du YAML
- pas de crawl, pas de login jeu, pas d'interaction compte
- délai poli entre requêtes, User-Agent identifié, taille max 20MB
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
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "lords-mobile"
DEFAULT_SOURCES = DEFAULT_DATA_DIR / "sources.yaml"
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024
USER_AGENT = "LordsMobileGuideCorpus/0.2 (stage-ete; +contact-admin)"
MIN_MD_CHARS = 500


def load_sources(path: Path) -> tuple[list[str], dict, list[dict]]:
    try:
        import yaml  # type: ignore
    except ImportError:
        print("PyYAML manquant: pip install -r scripts/requirements-scrape.txt", file=sys.stderr)
        raise SystemExit(2)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "sources" not in data:
        raise ValueError(f"{path} doit contenir allowed_domains + sources")
    return (
        [str(d).lower() for d in data.get("allowed_domains", [])],
        dict(data.get("defaults", {}) or {}),
        list(data.get("sources", []) or []),
    )


def check_url(url: str, allowed: list[str]) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError(f"URL non HTTP(S): {url}")
    host = parsed.netloc.lower().split(":")[0]
    if not any(host == d or host.endswith("." + d) for d in allowed):
        raise ValueError(f"Domaine non autorisé: {host} (autorisés: {allowed})")
    return url


def safe_target(data_dir: Path, relative: str) -> Path:
    target = (data_dir / relative).resolve()
    root = data_dir.resolve()
    if root != target and root not in target.parents:
        raise ValueError(f"Chemin hors corpus refusé: {relative}")
    return target


def fetch_wikitext(api_base: str, title: str) -> str:
    """Récupère le wikitext via MediaWiki API (contourne l'anti-bot HTML Fandom)."""
    import json as _json
    from urllib.parse import urlencode

    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2",
    }
    url = api_base.rstrip("/") + "/api.php?" + urlencode(params)
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126.0",
        "Accept": "application/json",
    }
    try:
        import requests  # type: ignore

        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
    except ImportError:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    pages = data.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        raise ValueError(f"Page wiki introuvable: {title}")
    revs = pages[0].get("revisions", [])
    if not revs:
        raise ValueError(f"Pas de révision pour: {title}")
    content = revs[0].get("slots", {}).get("main", {}).get("content") or revs[0].get("content", "")
    if not content:
        raise ValueError(f"Contenu vide pour: {title}")
    return content


def wikitext_to_markdown(wt: str, title: str, url: str) -> str:
    """Conversion wikitext -> Markdown lisible pour RAG (sans dépendance)."""
    # Supprime commentaires, templates complexes (garde texte simple)
    wt = re.sub(r"<!--.*?-->", " ", wt, flags=re.DOTALL)
    # Fichiers / images -> supprime
    wt = re.sub(r"\[\[(File|Image|Category):[^\]]*\]\]", " ", wt)
    # Liens internes [[Page|texte]] -> texte, [[Page]] -> Page
    wt = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", wt)
    wt = re.sub(r"\[\[([^\]]+)\]\]", r"\1", wt)
    # Liens externes [http... texte] -> texte (url)
    wt = re.sub(r"\[https?://[^\s\]]+\s+([^\]]+)\]", r"\1", wt)
    wt = re.sub(r"\[https?://[^\]]+\]", "", wt)
    # Templates {{...}} imbriqués simples -> supprime (plusieurs passes)
    for _ in range(5):
        new = re.sub(r"\{\{[^{}]*\}\}", " ", wt)
        if new == wt:
            break
        wt = new
    # Titres == X == -> ## X
    def _h(m: re.Match) -> str:
        level = min(3, max(1, 4 - len(m.group(1)) // 1)) if False else None
        eqs = m.group(1)
        text = m.group(2).strip()
        depth = len(eqs)
        if depth >= 4:
            return f"\n### {text}\n"
        if depth == 3:
            return f"\n### {text}\n"
        if depth == 2:
            return f"\n## {text}\n"
        return f"\n# {text}\n"

    wt = re.sub(r"(={2,4})\s*(.+?)\s*\1", _h, wt)
    # Gras/italique wiki -> markdown
    wt = wt.replace("'''''", "**").replace("'''", "**").replace("''", "*")
    # Listes * -> -
    wt = re.sub(r"(?m)^\*+", "- ", wt)
    wt = re.sub(r"(?m)^#+", "1.", wt)
    # Balises HTML résiduelles
    wt = re.sub(r"<[^>]+>", " ", wt)
    # Tableaux wiki {| ... |} -> texte brut (évite bruit {| class=... |} dans RAG)
    wt = re.sub(r"\{\|.*?\|\}", lambda m: re.sub(r"[\|\!]\s*", " ", m.group(0)), wt, flags=re.DOTALL)
    wt = re.sub(r"^\s*[\|\!].*$", " ", wt, flags=re.MULTILINE)
    wt = html_lib.unescape(wt)
    wt = re.sub(r"\n{3,}", "\n\n", wt).strip()
    header = (
        f"# {title}\n\n"
        f"> Source: {url}\n"
        f"> Wiki communautaire — à relire avant ingestion (fiabilité 3/5, vérifier les valeurs en jeu).\n\n"
    )
    return header + wt + "\n"


def fetch(url: str) -> tuple[bytes, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
    }
    # Préfère requests (meilleure tolérance anti-bot basique) si dispo
    try:
        import requests  # type: ignore

        resp = requests.get(url, headers=headers, timeout=45)
        if resp.status_code == 403:
            raise ValueError(
                f"403 Forbidden pour {url} — Fandom anti-bot. "
                "Solution stage: téléchargement manuel du HTML (Ctrl+S) dans data/lords-mobile/community/ "
                "puis mise à jour manifest.jsonl, ou utilise l'API officielle IGG."
            )
        resp.raise_for_status()
        if len(resp.content) > MAX_DOWNLOAD_BYTES:
            raise ValueError(f"Téléchargement > {MAX_DOWNLOAD_BYTES}: {url}")
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        return resp.content, ctype
    except ImportError:
        pass
    req = Request(url, headers=headers)
    with urlopen(req, timeout=45) as resp:
        length = resp.headers.get("Content-Length")
        if length and int(length) > MAX_DOWNLOAD_BYTES:
            raise ValueError(f"Téléchargement > {MAX_DOWNLOAD_BYTES}: {url}")
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        buf = bytearray()
        while chunk := resp.read(64 * 1024):
            buf.extend(chunk)
            if len(buf) > MAX_DOWNLOAD_BYTES:
                raise ValueError(f"Téléchargement > {MAX_DOWNLOAD_BYTES}: {url}")
        return bytes(buf), ctype


class _MdExtractor(HTMLParser):
    """Extracteur HTML -> Markdown simple sans dépendance (fallback si bs4 absent)."""

    def __init__(self) -> None:
        super().__init__()
        self.out: list[str] = []
        self._skip = 0  # script/style/nav/footer
        self._in_li = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "nav", "footer", "aside", "form", "header"}:
            self._skip += 1
            return
        if self._skip:
            return
        if tag in {"h1", "h2", "h3"}:
            level = {"h1": "# ", "h2": "## ", "h3": "### "}[tag]
            self.out.append("\n\n" + level)
        elif tag == "p":
            self.out.append("\n\n")
        elif tag == "br":
            self.out.append("\n")
        elif tag == "li":
            self.out.append("\n- ")
            self._in_li = True
        elif tag == "a":
            href = dict(attrs).get("href", "")
            self.out.append("[")
            self._pending_href = href or ""
        elif tag in {"tr"}:
            self.out.append("\n| ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "footer", "aside", "form", "header"}:
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag == "a" and getattr(self, "_pending_href", None) is not None:
            href = getattr(self, "_pending_href", "")
            self.out.append(f"]({href})" if href else "]")
            self._pending_href = None
        if tag == "li":
            self._in_li = False

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = html_lib.unescape(data)
        text = re.sub(r"\s+", " ", text)
        if text.strip():
            self.out.append(text if self._in_li else text)


def html_to_markdown(html: str, title: str, url: str) -> str:
    # Tente BeautifulSoup si dispo pour un meilleur nettoyage (main/article).
    text_html = html
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "aside", "form", "header"]):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.find("div", {"id": "content"})
        text_html = str(main) if main else str(soup)
    except ImportError:
        pass
    parser = _MdExtractor()
    parser.feed(text_html)
    body = "".join(parser.out)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    header = (
        f"# {title}\n\n"
        f"> Source: {url}\n"
        f"> Collecté le {datetime.now(timezone.utc).date().isoformat()} — synthèse à relire avant ingestion "
        f"(fiabilité à confirmer, vérifier les valeurs en jeu).\n\n"
    )
    md = header + body
    # Nettoyage pubs / boilerplate Fandom courants
    md = re.sub(r"(Advertisement|Sign In|Create a Free Account|Skip to content)+", " ", md)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    return md


def manifest_records(manifest: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not manifest.is_file():
        return out
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rec = json.loads(line)
        if isinstance(rec, dict) and rec.get("id"):
            out[str(rec["id"])] = rec
    return out


def write_manifest(manifest: Path, records: dict[str, dict]) -> None:
    lines = [json.dumps(records[k], ensure_ascii=False) for k in sorted(records)]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    ap.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    ap.add_argument("--execute", action="store_true", help="Télécharge réellement.")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--delay-seconds", type=float, default=1.5)
    ap.add_argument("--source-id", action="append", dest="source_ids", default=None)
    ap.add_argument("--min-chars", type=int, default=MIN_MD_CHARS)
    ap.add_argument("--dry-run", action="store_true", help="Plan uniquement (comportement par défaut sans --execute).")
    args = ap.parse_args()

    data_dir = args.data_dir.resolve()
    allowed, defaults, sources = load_sources(args.sources.resolve())
    if args.source_ids:
        wanted = set(args.source_ids)
        sources = [s for s in sources if str(s.get("id")) in wanted]
        if not sources:
            print(f"Aucune source correspond à {wanted}", file=sys.stderr)
            return 1

    manifest = data_dir / "manifest.jsonl"
    records = manifest_records(manifest)

    planned = 0
    for src in sources:
        sid = str(src.get("id", "<missing>"))
        url = str(src.get("url", ""))
        rel = str(src.get("output_path", ""))
        fmt = str(src.get("format", "html-to-md"))
        if not url or not rel:
            print(f"SKIP {sid}: url + output_path requis")
            continue
        try:
            check_url(url, allowed)
            target = safe_target(data_dir, rel)
        except ValueError as e:
            print(f"SKIP {sid}: {e}")
            continue
        planned += 1
        if not args.execute:
            print(f"PLAN {sid}: {url} -> {rel} [{fmt}]")
            continue
        if target.exists() and not args.overwrite:
            print(f"SKIP {sid}: existe déjà ({rel}), utilise --overwrite pour remplacer")
            # met quand même à jour le manifest si entrée absente
            if sid not in records:
                print(f"  -> entrée manifest manquante, sera créée sans re-télécharger")
            else:
                continue
        print(f"DOWNLOAD {sid}: {url}")
        wiki_api = str(src.get("wiki_api", "") or "")
        wiki_title = str(src.get("wiki_title", "") or "")
        fmt_lower = fmt.lower()
        target.parent.mkdir(parents=True, exist_ok=True)
        if wiki_api and wiki_title:
            wt = fetch_wikitext(wiki_api, wiki_title)
            md = wikitext_to_markdown(wt, str(src.get("title", sid)), url)
            if len(md) < args.min_chars:
                print(f"  WARN {sid}: contenu converti trop court ({len(md)} chars)")
            if target.suffix.lower() not in {".md", ".markdown", ".txt"}:
                target = target.with_suffix(".md")
            target.write_text(md, encoding="utf-8")
            print(f"  SAVED MD (wiki API) {len(md)} chars -> {target.relative_to(data_dir)}")
            actual_rel = str(target.relative_to(data_dir))
        else:
            raw, ctype = fetch(url)
            is_pdf = "pdf" in ctype or url.lower().endswith(".pdf") or fmt_lower == "pdf"

            if is_pdf or fmt_lower == "pdf":
                if not target.suffix.lower() == ".pdf":
                    target = target.with_suffix(".pdf")
                target.write_bytes(raw)
                print(f"  SAVED PDF {len(raw)} octets -> {target.relative_to(data_dir)}")
                actual_rel = str(target.relative_to(data_dir))
            else:
                try:
                    html = raw.decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    html = raw.decode("latin-1")
                md = html_to_markdown(html, str(src.get("title", sid)), url)
                if len(md) < args.min_chars:
                    print(f"  WARN {sid}: contenu converti trop court ({len(md)} chars), vérifie l'URL")
                if target.suffix.lower() not in {".md", ".markdown", ".txt"}:
                    target = target.with_suffix(".md")
                target.write_text(md, encoding="utf-8")
                print(f"  SAVED MD {len(md)} chars -> {target.relative_to(data_dir)}")
                actual_rel = str(target.relative_to(data_dir))

        # Construit / met à jour l'entrée manifest pour ingestion ultérieure
        entry = dict(records.get(sid, {}))
        entry.update(
            {
                "id": sid,
                "path": actual_rel,
                "title": src.get("title", entry.get("title", sid)),
                "source": src.get("source", entry.get("source", "Lords Mobile Wiki")),
                "url": url,
                "source_type": src.get("source_type", defaults.get("source_type", "verified_community")),
                "language": src.get("language", defaults.get("language", "en")),
                "game_version": src.get("game_version", defaults.get("game_version", "2025-review")),
                "published_at": src.get("published_at", entry.get("published_at")),
                "collected_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "topics": src.get("topics", entry.get("topics", ["guides"])),
                "entity_type": src.get("entity_type", entry.get("entity_type", "guide")),
                "entity_name": src.get("entity_name", entry.get("entity_name", sid)),
                "reliability": int(src.get("reliability", defaults.get("reliability", 3))),
                "status": src.get("status", defaults.get("status", "needs_review")),
            }
        )
        records[sid] = entry
        time.sleep(max(0.0, args.delay_seconds))

    if args.execute and planned:
        write_manifest(manifest, records)
        print(f"Manifest mis à jour: {manifest} ({len(records)} entrées)")
    print(f"{planned} source(s) {'traitée(s)' if args.execute else 'planifiée(s)'}.")
    print("Ensuite: python scripts/ingest_lords_mobile.py --dry-run  puis  import via /api/admin/knowledge (ADMIN).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"Scrape failed: {error}", file=sys.stderr)
        raise SystemExit(1)
