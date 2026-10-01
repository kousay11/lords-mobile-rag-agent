# Migrations métier

Le backend utilise actuellement Hibernate `ddl-auto: update` (pas de runner Flyway/Liquibase). Les scripts de ce dossier sont des migrations explicites et idempotentes pour les bases existantes ; ils ne sont pas exécutés automatiquement par PostgreSQL.

## Suppression Version / Royaume (002)

Les concepts du jeu sont stables entre versions et le corpus n'est pas suivi par version : les champs `Version / corpus documentaire` et `Royaume` ont été supprimés pour tous les rôles (joueur + admin). L'agent interroge tout le corpus (`active, deprecated, needs_review`, fiabilité >= 3) sans filtre de version.

Avant de déployer le backend correspondant sur une base existante :

```sh
docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < database/migrations/002_drop_version_kingdom.sql
```

`002` supprime `player_profiles.game_version/version_mode/kingdom`, `knowledge_documents.game_version`, `chat_threads/chat_messages.game_version`. `ddl-auto:update` ne supprime jamais de colonnes seul : sans `002`, les colonnes restent présentes mais inutilisées (nullable, sans écriture). La colonne `agent_threads.game_version` est conservée pour compatibilité et ignorée par le code.

## Historique (001)

`001_player_profile_preferences.sql` ajoutait `response_length`, `version_mode` et `setup_completed`. `version_mode` est désormais obsolète (voir `002`).
