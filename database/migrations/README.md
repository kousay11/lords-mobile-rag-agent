# Migrations métier

Le backend utilise actuellement Hibernate `ddl-auto: update` (pas de runner Flyway/Liquibase). Les scripts de ce dossier sont des migrations explicites et idempotentes pour les bases existantes ; ils ne sont pas exécutés automatiquement par PostgreSQL.

## Préférences du profil

Avant de déployer le backend correspondant sur une base existante :

```sh
docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < database/migrations/001_player_profile_preferences.sql
```

Le script ajoute `response_length`, `version_mode` et `setup_completed` à `player_profiles`, sans supprimer les valeurs existantes. La relation unique `user_id → users.id` est conservée. Les anciens profils doivent enregistrer leurs préférences une fois avant leur prochaine question.

- Langues : `fr`, `en`, `ar`.
- Longueur : `short`, `standard`, `detailed` (consigne de rédaction, pas nombre exact de mots garanti).
- Version : `unknown` avec version nulle, ou `specific` avec un identifiant proposé par `/api/lords-mobile/profile/versions`. Cette liste contient tous les ensembles indexés ; `/api/lords-mobile/profile/version-options` fournit leurs libellés, types et compteurs. Les numéros de version, corpus annuels à vérifier et guides datés restent distingués, sans modifier les statuts des documents. Une date de collecte ou `2026-review` n’est pas une version du jeu.
- `setup_completed` est attribué uniquement par le serveur après validation. Le chat renvoie HTTP 428 si le profil n’est pas configuré, avant tout appel à l’agent.

Les préférences enregistrées priment sur les champs de préférence envoyés avec une question. La langue de réponse est indépendante de celle des sources ; les critères de validation des sources restent appliqués. Les nouveaux paramètres remplacent aussi les préférences du checkpointer lors d’une conversation existante.

Les tables internes LangGraph restent sous la responsabilité du service Agent.

La sélection explicite d’un corpus `AAAA-review` autorise uniquement dans ce corpus les sources `needs_review` de fiabilité >= 3, avec un avertissement dans la réponse. Le mode sans version précise conserve les sources actives de fiabilité >= 4. Les documents présents uniquement sur disque ne sont pas annoncés comme indexés.
