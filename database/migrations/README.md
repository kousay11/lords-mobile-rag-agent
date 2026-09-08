# Migrations métier

Ce dossier est réservé aux migrations PostgreSQL possédées par Spring Boot : documents du corpus, conversations, messages et feedbacks.

Il n'est volontairement pas monté comme script d'initialisation PostgreSQL à ce stade. Le service Agent possède encore une table technique `chat_threads` utilisée par son checkpointer ; créer les tables métier avant d'adapter l'Agent et le Backend créerait un conflit de propriétaire et de schéma.

Lors de l'étape Backend, ajouter Flyway ou Liquibase, puis créer la première migration versionnée ici. Les tables internes LangGraph restent sous la responsabilité du checkpointer Agent.
