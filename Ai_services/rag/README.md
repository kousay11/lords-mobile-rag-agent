# Service RAG Lords Mobile

Le service expose l'ingestion contrôlée et la recherche dense, sparse ou hybride dans la collection Qdrant `lords_mobile_knowledge`.

## Métadonnées d'ingestion

Les champs suivants sont obligatoires : `document_id`, `title`, `source`, `source_type`, `language`, `reliability`, `status` et `topics`.

```json
{
  "text": "Contenu documentaire suffisamment détaillé...",
  "metadata": {
    "document_id": "official-buildings-001",
    "title": "Castle requirements",
    "source": "Official guide",
    "url": "https://example.com/official-guide",
    "source_type": "official",
    "language": "en",
    "reliability": 5,
    "status": "active",
    "topics": ["buildings", "progression"]
  }
}
```

Pour `/ingest/file`, envoyer le fichier dans le champ multipart `file` et cet objet de métadonnées sérialisé en JSON dans le champ `metadata`. Les formats acceptés sont PDF, Markdown et texte UTF-8, dans la limite configurée par `MAX_UPLOAD_BYTES`.

## Recherche

Sans filtre de statut explicite, `/retrieve` ne consulte que les documents `active`.

```json
{
  "query": "Quels sont les prérequis du château ?",
  "search_type": "hybrid",
  "top_k": 8,
  "language": "fr",
  "topic": "buildings",
  "source_type": "official",
  "statuses": ["active"],
  "min_reliability": 4
}
```

Une réingestion identique utilise les mêmes identifiants de chunks. Lorsqu'un document portant le même `document_id` change, la nouvelle révision est écrite avant le retrait de ses anciens chunks.

## Tests

Depuis une image du service contenant ses dépendances :

```text
python -m unittest discover -s tests -v
```
