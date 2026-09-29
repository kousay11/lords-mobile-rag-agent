# Scripts d'exploitation

- `scrape_lords_mobile.py` : nouveau pipeline recommandé. Lit `data/lords-mobile/sources.yaml` (allowlist), `--dry-run` par défaut, `--execute` pour télécharger + MAJ `manifest.jsonl`. Wiki Fandom via MediaWiki API (contourne 403 HTML), IGG officiel en HTML direct. `pip install -r scripts/requirements-scrape.txt`.
- `ingest_lords_mobile.py` : envoie les fichiers Markdown, texte ET PDF locaux vers le RAG. Exécuter d'abord avec `--dry-run`. PDF extrait en local via pypdf.
- `start.ps1` : crée un `.env` local s'il manque puis démarre Docker Compose ; utiliser `-Build` pour reconstruire les images.
- `validate.ps1` : valide la configuration Docker Compose et la syntaxe Python, sans service externe.

Ces scripts sont volontairement sans automatisation de compte, de jeu, de crawler ou de collecte implicite.

`ingest_lords_mobile.py --document-id IDENTIFIANT` permet de reprendre ou de limiter une ingestion. L'option peut être répétée pour plusieurs documents.

Lorsque le RAG n'expose pas son port sur l'hôte, lancer l'ingestion depuis un conteneur temporaire relié au réseau Compose :

```powershell
docker compose --env-file .env run --rm --no-deps `
  -v "${PWD}/data/lords-mobile:/corpus:ro" `
  -v "${PWD}/scripts/ingest_lords_mobile.py:/scripts/ingest_lords_mobile.py:ro" `
  rag python /scripts/ingest_lords_mobile.py `
  --data-dir /corpus --rag-url http://rag:8001
```
