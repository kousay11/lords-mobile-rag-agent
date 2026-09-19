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

Les services RAG et Agent sont internes au réseau Docker. Le frontend Next.js passe exclusivement par le backend Spring Boot pour l'authentification, le chat, les conversations, le profil joueur et l'administration du corpus.

## API backend

- `POST /api/auth/register` et `POST /api/auth/login` : authentification JWT ;
- `POST /api/lords-mobile/chat` : question authentifiée transmise à l'agent en lecture seule ;
- `GET /api/lords-mobile/threads` : conversations de l'utilisateur courant ;
- `GET|PUT /api/lords-mobile/profile` : contexte du joueur ;
- `POST /api/lords-mobile/messages/{messageId}/feedback` : retour utile ou non utile ;
- `/api/admin/knowledge/**` : catalogue PostgreSQL et indexation RAG, réservés au rôle `ADMIN` ;
- `GET /api/health` : santé du backend et des services IA.

Le backend écoute sur le port `8080` dans Docker et est publié par défaut sur `http://localhost:8081`. La documentation OpenAPI est disponible sur `http://localhost:8081/swagger-ui.html` après son démarrage.

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
