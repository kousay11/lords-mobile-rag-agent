# Agent Lords Mobile

Service FastAPI/LangGraph en lecture seule. Il classe la demande, extrait le
contexte de jeu, interroge le service RAG, puis produit une réponse avec les
sources, la version concernée et un niveau de confiance.

L'agent ne contient aucun outil d'automatisation de compte ou de jeu. Les
conversations sont conservées par les checkpoints LangGraph dans PostgreSQL.

## Services requis

- `rag` sur `http://rag:8001` ;
- PostgreSQL via `CHECKPOINT_DB_URI` ;
- un fournisseur compatible OpenAI configuré dans `config/providers.json`.

Si le fournisseur de génération est indisponible, l'agent renvoie une réponse
extractive prudente à partir des documents retrouvés, sans inventer de faits.

## API principale

- `GET /health` : état du service et de la persistance ;
- `POST /chat` : réponse structurée Lords Mobile ;
- `GET /threads/{thread_id}` : historique d'une conversation ;
- `GET /models` : fournisseurs et modèles configurés.

Exemple minimal pour `POST /chat` :

```json
{
  "message": "Comment fonctionnent les joyaux de combat ?",
  "thread_id": "demo",
  "user_id": "local-user",
  "language": "fr"
}
```

## Tests

Depuis la racine du projet :

```powershell
docker compose --env-file .env run --rm --no-deps `
  -v "${PWD}/Ai_services/agent/tests:/tests:ro" `
  agent python -m unittest discover -s /tests -v
```
