# Corpus Lords Mobile

Ce dossier ne contient que des copies de documents dont l'utilisation est autorisée ou des notes rédigées par l'équipe. Ne pas y placer de secrets, données personnelles ou identifiants de compte.

Chaque source doit être décrite dans `manifest.jsonl`. Les champs minimums sont : `id`, `path`, `title`, `source`, `source_type`, `language`, `game_version`, `published_at`, `topics`, `reliability` et `status`.

- `source_type` : `official`, `verified_community`, `community` ou `reference`.
- `reliability` : entier de 1 à 5 ; une source officielle vérifiée reçoit 5.
- `status` : `active`, `deprecated` ou `needs_review`.
- `path` doit rester sous ce dossier ; les scripts refusent les chemins sortant du corpus.

La collecte automatique est désactivée par défaut : le script effectue seulement une prévisualisation. `--execute` télécharge exclusivement les URLs explicitement autorisées dans le manifeste ; il ne parcourt aucun site ni ne se connecte au jeu.

## Corpus initial

Le corpus initial contient 12 synthèses françaises fondées sur des pages officielles IGG :

- 9 fiches actives sur les héros, la chasse, les Sombres nids, les joyaux, l'équipement et les niveaux élite ;
- 3 archives de versions 2.13, 2.16 et 2.18, marquées `deprecated` et exclues de la recherche par défaut.

Les guides généraux datent de 2019. Leur fiabilité est donc fixée à 4/5 et chaque fiche demande de vérifier dans le jeu les valeurs susceptibles d'avoir changé. Les notes de mise à jour sont fiables pour leur version historique, mais ne décrivent pas nécessairement les règles actuelles.

Ce corpus est le socle d'évaluation prévu par le plan, pas une encyclopédie complète du jeu. Toute nouvelle source doit être examinée, synthétisée et ajoutée au manifeste avant ingestion.
