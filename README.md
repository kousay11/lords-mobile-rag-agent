# Lords Mobile Guide Agent

Plateforme RAG en lecture seule pour répondre à des questions sur Lords Mobile à partir d'un corpus traçable et versionné.

## Architecture

```text
Next.js -> Spring Boot -> Agent LangGraph -> RAG FastAPI -> Qdrant
                    |             |
                PostgreSQL      PostgreSQL checkpoints
                    |
                  Redis
```

Les services RAG et Agent sont internes au réseau Docker. Le navigateur devra passer par Spring Boot lorsque les routes chat et knowledge auront été adaptées ; le frontend historique appelle encore directement l'agent et ne constitue pas encore le flux cible.

## Démarrage de l'infrastructure

1. Copier `.env.example` vers `.env` et remplacer les secrets de développement.
2. Configurer un fournisseur LLM dans `config/providers.json`.
3. Exécuter `docker compose up --build`.
4. Vérifier l'état des services avec `docker compose ps`.

Sous PowerShell, `scripts/start.ps1 -Build` effectue la même opération. `scripts/validate.ps1` valide la configuration Compose et les fichiers Python sans démarrer les services.

## Corpus documentaire

Les documents sont conservés sous `data/lords-mobile/`. La collecte ne télécharge que les URLs explicitement déclarées dans le manifeste et l'ingestion n'exécute aucune action de jeu ni de compte.

```powershell
python scripts/collect_lords_mobile_sources.py
python scripts/ingest_lords_mobile.py --dry-run
```

Consulter `data/lords-mobile/README.md` avant d'ajouter une source.
