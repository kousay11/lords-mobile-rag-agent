# Retrait de `collect_lords_mobile_sources.py` — Note de stage

Date : 2026-09-28
Statut : appliqué le 2026-09-29 (script supprimé, README mis à jour)

## 1. Contexte

`scripts/collect_lords_mobile_sources.py` était le script historique de collecte du corpus.
Il est remplacé par `scripts/scrape_lords_mobile.py` + `data/lords-mobile/sources.yaml`.

## 2. Causes du retrait

1. **Inopérant sur le manifeste actuel** (`collect_lords_mobile_sources.py:96-98`) :
   ```python
   url = record.get("download_url")
   if not relative_path or not url:
       print(f"SKIP {source_id}: requires both path and download_url")
   ```
   Le manifeste (`data/lords-mobile/manifest.jsonl`) n'utilise que `url`, jamais
   `download_url`. Résultat constaté : 12/12 `SKIP`, `0 approved download(s) planned`.

2. **Pas de production `.md` / `.pdf` exploitable RAG** : téléchargement brut uniquement,
   sans conversion HTML → Markdown ni extraction PDF.

3. **Bloqué par l'anti-bot Fandom** : les pages `lordsmobile.fandom.com/wiki/...` renvoient
   `403 Forbidden` en HTML simple. Le nouveau pipeline utilise la MediaWiki API
   (`/api.php?action=query&titles=...&prop=revisions`) qui répond `200 JSON`, puis convertit
   le wikitext en Markdown.

4. **Pas de mise à jour du manifeste** : le nouveau scraper écrit/met à jour
   `manifest.jsonl` automatiquement (`id`, `path`, `title`, `topics`, `reliability`,
   `status: needs_review`), prêt pour `ingest_lords_mobile.py` ou l'admin
   `POST /api/admin/knowledge/documents` + `POST .../{id}/index`.

## 3. Fichiers liés

| Fichier | Lien | Action si suppression |
|---|---|---|
| `scripts/collect_lords_mobile_sources.py` | script lui-même | `git rm scripts/collect_lords_mobile_sources.py` |
| `README.md:43` | `python scripts/collect_lords_mobile_sources.py` dans § Corpus documentaire | remplacer par `python scripts/scrape_lords_mobile.py --dry-run` |
| `scripts/README.md:3` | ligne `collect_lords_mobile_sources.py : legacy...` | supprimer la ligne, garder `scrape_` + `ingest_` |
| `docs/PLAN_ARCHITECTURE_RAG_AGENT_LORDS_MOBILE.md`, `docs/GUIDE_ADAPTATION...` | aucune référence (vérifié par grep) | rien à faire |
| Code Python (`Ai_services/`, `backend/`) | aucun import (script standalone) | rien à faire |

Vérification effectuée le 2026-09-28 par `grep -r "collect_lords_mobile_sources"` : seules les
2 références README ci-dessus.

## 4. Procédure de suppression proposée

```bash
cd "/home/najjar/Documents/Me/summer internship/lords-mobile-rag-agent"
git rm scripts/collect_lords_mobile_sources.py
# éditer README.md:43 -> scrape_lords_mobile.py --dry-run
# éditer scripts/README.md -> retirer la ligne legacy
python3 -m py_compile scripts/scrape_lords_mobile.py scripts/ingest_lords_mobile.py
docker compose config --quiet
git status -sb
git commit -m "chore(scripts): retire collect_lords_mobile_sources.py (remplacé par scrape_lords_mobile.py)"
git push origin main
```

## 5. Rollback

```bash
git log --oneline -- scripts/collect_lords_mobile_sources.py
git restore --source=<commit-avant-suppression> -- scripts/collect_lords_mobile_sources.py
```

## 6. Décision

- [ ] Supprimer maintenant
- [ ] Garder en legacy jusqu'à la fin du stage
