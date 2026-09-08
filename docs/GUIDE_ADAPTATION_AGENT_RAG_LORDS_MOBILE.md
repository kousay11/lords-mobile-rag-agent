# Guide d'adaptation de l'agent RAG pour Lords Mobile

## 1. But de ce document

Ce document sert de guide de démarrage pour transformer l'agent RAG actuel de QoSentry en un agent conversationnel spécialisé dans **Lords Mobile**.

L'objectif n'est pas de reconstruire le projet depuis zéro. L'architecture actuelle doit être conservée autant que possible, puis adaptée sur les points qui dépendent du domaine : documents, prompts, intentions, métadonnées, modèle de données, interface et identité visuelle.

L'agent final doit :

- répondre aux questions des joueurs ;
- expliquer les mécaniques du jeu avec un langage adapté au niveau du joueur ;
- utiliser les documents Lords Mobile comme source principale ;
- afficher les sources utilisées ;
- prendre en compte la version du jeu et la langue ;
- reconnaître les cas où il ne possède pas suffisamment d'informations ;
- rester en lecture seule dans la première version.

## 2. Décision d'architecture

### 2.1 Technologies conservées

| Couche | Technologie actuelle | Rôle dans le nouveau projet |
|---|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS | Chat, sources, profil joueur, administration |
| Backend métier | Spring Boot, Java 17 | API publique, authentification, utilisateurs, conversations |
| Agent | Python, FastAPI, LangChain, LangGraph | Orchestration de la question et génération de réponse |
| Service RAG | Python, FastAPI | Ingestion, embeddings, recherche documentaire |
| Base relationnelle | PostgreSQL | Utilisateurs, conversations, documents, feedbacks, checkpoints |
| Base vectorielle | Qdrant | Vecteurs denses, sparse et métadonnées de chunks |
| Cache et événements | Redis | Cache de réponses, rate limiting et événements optionnels |
| Modèles | Embeddings + LLM OpenAI-compatible | Recherche et génération |
| Déploiement | Docker Compose | Lancement reproductible de toute la plateforme |

### 2.2 Règle importante sur les bases de données

PostgreSQL et Qdrant ne remplissent pas le même rôle :

- **PostgreSQL** est la base métier durable et relationnelle.
- **Qdrant** est l'index de recherche sémantique et lexicale.

Il ne faut pas stocker uniquement un document dans Qdrant. Le document original et son état de validation doivent être enregistrés dans PostgreSQL ou dans un stockage de fichiers contrôlé. Qdrant contient les chunks indexés et leurs métadonnées de recherche.

## 3. Architecture globale cible

```mermaid
flowchart TB
    Player[Joueur] --> Front[Next.js / TypeScript]
    Front --> Backend[Spring Boot / Java 17]
    Backend --> Auth[(PostgreSQL)]
    Backend --> Agent[Agent FastAPI / LangGraph]
    Agent --> RAG[Service RAG FastAPI]
    Agent --> Checkpoints[(PostgreSQL checkpoints)]
    Agent --> Redis[(Redis)]
    RAG --> Qdrant[(Qdrant vector store)]
    RAG --> Corpus[(Documents contrôlés)]
    Admin[Administrateur] --> Front
    Admin --> Backend
    Backend --> RAG
```

### 3.1 Flux d'une question

```text
Frontend
  -> Spring Boot : authentification, utilisateur et validation de la requête
  -> Agent FastAPI : question + thread_id + contexte joueur
  -> LangGraph : intention, clarification, réécriture
  -> RAG FastAPI : recherche hybride dans Qdrant
  -> Agent : contexte et sources
  -> LLM : génération contrôlée
  -> Agent : réponse + citations + confiance
  -> Spring Boot : journalisation et réponse API
  -> Frontend : affichage conversationnel
```

### 3.2 Flux d'ingestion documentaire

```text
Admin ou import batch
  -> Spring Boot : contrôle d'accès et création du document
  -> RAG FastAPI : extraction et préparation du texte
  -> RAG : nettoyage, déduplication et chunking
  -> Embeddings : vecteur dense + vecteur sparse
  -> Qdrant : indexation des chunks
  -> PostgreSQL : statut, hash, version, source et audit
```

## 4. Arborescence à conserver et à faire évoluer

### 4.1 Arborescence recommandée

```text
project-root/
├── docker-compose.yml                 # orchestration locale complète
├── README.md                          # démarrage et documentation principale
├── config/
│   ├── providers.json                 # fournisseurs LLM autorisés
│   └── lords-mobile-topics.json       # sujets et entités du jeu
├── data/
│   └── lords-mobile/                  # documents sources contrôlés
├── docs/
│   ├── PLAN_ARCHITECTURE_RAG_AGENT_LORDS_MOBILE.md
│   └── GUIDE_ADAPTATION_AGENT_RAG_LORDS_MOBILE.md
├── database/
│   └── migrations/                    # migrations PostgreSQL métier
├── backend/
│   ├── pom.xml
│   └── src/main/
│       ├── java/.../auth/             # réutiliser authentification
│       ├── java/.../user/             # réutiliser utilisateurs et rôles
│       ├── java/.../chat/             # nouveau module conversations
│       ├── java/.../knowledge/        # nouveau module documents RAG
│       └── resources/application.yml
├── ai-services/
│   ├── rag/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── main.py
│   │       ├── embeddings.py
│   │       ├── vector_store.py
│   │       ├── document_pipeline.py  # nouveau
│   │       └── models.py             # nouveau
│   └── agent/
│       ├── Dockerfile
│       ├── requirements.txt
│       └── app/
│           ├── main.py
│           ├── graph.py
│           ├── prompts.py             # nouveau
│           ├── intent.py              # nouveau
│           ├── db.py
│           └── config.py
├── frontend/
│   ├── package.json
│   ├── app/
│   │   ├── chat/page.tsx
│   │   ├── knowledge/page.tsx         # nouveau espace admin
│   │   └── settings/page.tsx
│   ├── components/
│   │   ├── thread/                    # réutiliser composants chat
│   │   ├── rag/                       # nouveau sources et confiance
│   │   └── game/                      # nouveau thème Lords Mobile
│   ├── lib/api.ts
│   └── app/globals.css
```

## 5. Fichiers existants à réutiliser

### 5.1 Agent Python

#### [ai-services/agent/app/graph.py](../ai-services/agent/app/graph.py)

À réutiliser :

- `StateGraph` et la structure LangGraph ;
- `AgentState` avec les messages ;
- le retriever HTTP vers le service RAG ;
- la recherche parallèle avec plusieurs requêtes ;
- la déduplication des documents ;
- le nœud de génération ;
- la compilation du graphe.

À modifier :

- prompts QoSentry vers prompts Lords Mobile ;
- classification `greeting/technical` vers les intentions du jeu ;
- paramètres `user_role` vers `language`, `game_version`, `player_profile` ;
- contexte de logs réseau vers contexte joueur ;
- noms de métriques et descriptions ;
- format des sources et de la confiance.

#### [ai-services/agent/app/main.py](../ai-services/agent/app/main.py)

À réutiliser :

- endpoints `/chat` et éventuellement `/openai/chat/completions` ;
- gestion de `thread_id` ;
- checkpointer PostgreSQL ;
- validation Pydantic ;
- contrôle de la santé du service.

À modifier ou ajouter :

- `GameContextRequest` ou champs de contexte dans `ChatRequest` ;
- endpoints d'administration documentaire, idéalement protégés par Spring Boot ;
- réponse contenant `confidence`, `citations`, `game_version` et `needs_clarification` ;
- suppression des routes d'incident et d'optimisation spécifiques au réseau si elles ne sont plus utilisées.

#### [ai-services/agent/app/db.py](../ai-services/agent/app/db.py)

À conserver pour la connexion asynchrone PostgreSQL et les checkpoints LangGraph. Ajouter éventuellement des méthodes séparées pour les feedbacks ou laisser ces données au backend Java afin d'éviter deux propriétaires de la même logique métier.

#### [ai-services/agent/app/config.py](../ai-services/agent/app/config.py)

À conserver pour les fournisseurs LLM, les modèles et les URLs. Ajouter des paramètres Lords Mobile dans des variables d'environnement plutôt que de les coder en dur.

### 5.2 Service RAG Python

#### [ai-services/rag/app/main.py](../ai-services/rag/app/main.py)

À réutiliser :

- initialisation asynchrone du modèle d'embedding ;
- endpoint `/health` ;
- `/ingest/text`, `/ingest/file`, `/ingest/batch` ;
- `/retrieve` ;
- verrous d'initialisation et d'ingestion ;

À modifier :

- modèles Pydantic avec `game_version`, `language`, `source_type` et `reliability` ;
- validation des extensions et de la taille des fichiers ;
- filtres Qdrant Lords Mobile ;
- endpoint de réindexation ou mise à jour par `document_id` ;
- contrôle des documents obsolètes.

#### [ai-services/rag/app/vector_store.py](../ai-services/rag/app/vector_store.py)

À réutiliser :

- collection Qdrant avec vecteur dense et sparse ;
- index payload ;
- split sémantique et fallback récursif ;
- hash et déduplication ;
- recherche hybride RRF ;
- recherche dense et keyword de secours.

À modifier :

- nom de collection, par exemple `lords_mobile_knowledge` ;
- taille et stratégie de chunk après évaluation sur des guides du jeu ;
- métadonnées métier Lords Mobile ;
- filtres `game_version`, `language`, `topic`, `entity_type`, `status` et `reliability` ;
- conservation des tableaux, coûts, durées, niveaux et unités.

#### [ai-services/rag/app/embeddings.py](../ai-services/rag/app/embeddings.py)

À conserver au départ. Tester le modèle actuel avec un petit corpus français/anglais du jeu. Le choix définitif du modèle doit être basé sur `Recall@k`, la latence et la qualité des noms propres, pas uniquement sur sa taille.

### 5.3 Backend Java

#### [backend/pom.xml](../backend/pom.xml)

À conserver :

- Spring Boot Web ;
- Spring Data JPA ;
- PostgreSQL ;
- Spring Security et JWT ;
- validation ;
- Redis ;
- OpenAPI.

À ajouter éventuellement :

- client HTTP Spring pour appeler l'agent et le RAG ;
- migrations Flyway ou Liquibase si le projet n'en utilise pas encore ;
- tests d'intégration PostgreSQL ;
- configuration CORS limitée aux URLs frontend.

Le backend Java doit rester la porte d'entrée publique. Le frontend ne doit pas appeler directement PostgreSQL, Qdrant ou les endpoints internes d'administration.

#### Modules Java à identifier ou créer

```text
backend/src/main/java/.../
├── auth/                         # existant à réutiliser
├── user/                         # existant à réutiliser
├── ai/
│   ├── AgentClient.java          # appel HTTP vers agent
│   ├── RagClient.java            # appel HTTP vers RAG admin
│   └── AiExceptionHandler.java
├── chat/
│   ├── ChatController.java
│   ├── ChatService.java
│   ├── ChatThread.java
│   ├── ChatMessage.java
│   └── ChatRepository.java
├── knowledge/
│   ├── KnowledgeController.java
│   ├── KnowledgeService.java
│   ├── KnowledgeDocument.java
│   ├── KnowledgeDocumentRepository.java
│   └── dto/
└── feedback/
    ├── FeedbackController.java
    └── Feedback.java
```

### 5.4 Frontend TypeScript

#### [frontend/lib/api.ts](../frontend/lib/api.ts)

À conserver :

- client Axios ;
- ajout automatique du JWT ;
- gestion centralisée des erreurs ;
- types TypeScript pour les réponses API.

À ajouter :

```ts
export interface GameContext {
  language: 'fr' | 'en' | 'ar'
  gameVersion?: string
  playerLevel?: number
  playStyle?: 'free_to_play' | 'low_spender' | 'spender'
  objective?: string
}

export interface RagSource {
  title: string
  url?: string
  sourceType: string
  gameVersion?: string
  score: number
}

export interface ChatAnswer {
  threadId: string
  response: string
  sources: RagSource[]
  confidence: number
  needsClarification: boolean
}
```

Ajouter des fonctions `sendLordsMobileMessage`, `getChatThreads`, `submitAnswerFeedback`, `listKnowledgeDocuments` et `uploadKnowledgeDocument` en les faisant passer par Spring Boot.

#### Pages et composants à réutiliser

- `frontend/app/chat/` : base de l'expérience conversationnelle ;
- `frontend/components/thread/` : affichage des messages et streaming ;
- `frontend/components/backend-readiness-gate.tsx` : contrôle de disponibilité ;
- `frontend/hooks/useAuth.ts` : authentification ;
- `frontend/lib/auth.ts` : gestion du token ;
- composants UI Radix et icônes `lucide-react`.

À ajouter :

- `SourceList` : sources associées à une réponse ;
- `ConfidenceBadge` : confiance lisible, sans prétendre être une probabilité exacte ;
- `GameContextPanel` : version, langue et profil joueur ;
- `KnowledgeDocumentTable` : liste et statut des documents ;
- `UploadKnowledgeDialog` : import réservé aux administrateurs ;
- `FeedbackButtons` : utile/inutile et commentaire facultatif.

## 6. Modèle de données PostgreSQL

PostgreSQL doit contenir les données métier et d'audit. Exemple de modèle minimal :

```sql
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    source VARCHAR(500) NOT NULL,
    url VARCHAR(1000),
    source_type VARCHAR(50) NOT NULL,
    language VARCHAR(10) NOT NULL,
    game_version VARCHAR(50),
    reliability SMALLINT NOT NULL DEFAULT 1,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    content_hash VARCHAR(128) NOT NULL UNIQUE,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    qdrant_chunks INTEGER NOT NULL DEFAULT 0,
    last_error TEXT
);

CREATE TABLE chat_threads (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title VARCHAR(255),
    language VARCHAR(10),
    game_version VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    thread_id UUID NOT NULL REFERENCES chat_threads(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    confidence NUMERIC(5,4),
    sources JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE answer_feedback (
    id UUID PRIMARY KEY,
    message_id UUID NOT NULL REFERENCES chat_messages(id),
    user_id UUID NOT NULL,
    rating VARCHAR(20) NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Les checkpoints techniques de LangGraph peuvent continuer à utiliser le mécanisme PostgreSQL existant. Les tables métier ne doivent pas être mélangées avec les tables internes du checkpointer.

## 7. Contrats API recommandés

### 7.1 API publique Spring Boot

```text
POST   /api/lords-mobile/chat
GET    /api/lords-mobile/threads
GET    /api/lords-mobile/threads/{threadId}
DELETE /api/lords-mobile/threads/{threadId}
POST   /api/lords-mobile/messages/{messageId}/feedback
GET    /api/lords-mobile/profile
PUT    /api/lords-mobile/profile
```

### 7.2 API administrateur Spring Boot

```text
GET    /api/admin/knowledge/documents
POST   /api/admin/knowledge/documents
POST   /api/admin/knowledge/documents/{id}/index
PATCH  /api/admin/knowledge/documents/{id}
DELETE /api/admin/knowledge/documents/{id}
POST   /api/admin/knowledge/reindex
```

### 7.3 API interne Agent/RAG

```text
POST /chat
GET  /health

POST /ingest/text
POST /ingest/file
POST /ingest/batch
POST /retrieve
GET  /documents
DELETE /documents/{source}
```

Le backend doit transmettre uniquement les données nécessaires. Les URLs internes `agent:8002` et `rag:8001` ne doivent pas être exposées publiquement en production.

## 8. Adaptation du graphe LangGraph

### 8.1 État cible

```python
class LordsMobileState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    language: str
    game_version: str | None
    player_context: dict
    intent: str
    rewritten_queries: list[str]
    retrieved_documents: list[dict]
    context: str
    sources: list[dict]
    confidence: float
    needs_clarification: bool
```

### 8.2 Nœuds à implémenter

```text
classify_intent
  -> greeting: réponse courte
  -> unclear: question de clarification
  -> out_of_scope: réponse hors périmètre
  -> autre: suite RAG

extract_game_context
  -> détecter version, sujet, entité et objectif

rewrite_query
  -> noms officiels et variantes linguistiques

retrieve
  -> recherche hybride avec filtres

validate_context
  -> vérifier score, version et fiabilité

generate_answer
  -> réponse appuyée par les documents

format_citations
  -> sources, confiance et limites
```

### 8.3 Prompt système cible

Le prompt doit imposer les règles suivantes :

```text
Tu es un guide documentaire spécialisé dans Lords Mobile.
Réponds dans la langue de la question.
Utilise uniquement les informations du contexte récupéré pour les faits précis.
Ne fabrique jamais une statistique, un coût, une durée ou un prérequis.
Si la version du jeu est inconnue et que la réponse peut varier, demande la version.
Sépare clairement les faits documentés des recommandations.
Explique les limites lorsque les sources sont insuffisantes.
Retourne une réponse utile, structurée et accompagnée de sources.
```

## 9. Adaptation Docker

### 9.1 Services à conserver

Le `docker-compose.yml` actuel contient déjà les services principaux :

- `postgres` ;
- `qdrant` ;
- `rag` ;
- `agent` ;
- `redis` ;
- `backend` ;

Les services `anomaly_detection`, `sla_forecasting` et les composants Mininet peuvent être retirés de la composition Lords Mobile si aucune fonctionnalité ne les utilise.

### 9.2 Variables d'environnement à prévoir

```text
# Backend
SPRING_DATASOURCE_URL=jdbc:postgresql://postgres:5432/lords_mobile
AI_AGENT_BASE_URL=http://agent:8002
AI_RAG_BASE_URL=http://rag:8001

# Agent
RAG_SERVICE_URL=http://rag:8001
CHECKPOINT_DB_URI=postgresql://postgres:postgres@postgres:5432/lords_mobile

# RAG
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=lords_mobile_knowledge
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
TOP_K=8

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8081
```

Les clés LLM et les secrets JWT doivent rester dans un fichier `.env` non commité ou dans le gestionnaire de secrets du déploiement.

### 9.3 Ordre de démarrage

```text
PostgreSQL + Qdrant
  -> RAG
  -> Agent
  -> Backend Spring Boot
  -> Frontend Next.js
```

Chaque service doit avoir un healthcheck. Le backend ne doit accepter les appels AI qu'après vérification de la disponibilité de l'agent et du RAG.

## 10. Ordre de réalisation recommandé

### Étape 1 : créer le socle Lords Mobile

1. Copier la structure existante sans supprimer les services actuels.
2. Créer une collection Qdrant dédiée.
3. Préparer 10 à 20 documents fiables.
4. Définir les métadonnées et le modèle `knowledge_documents`.
5. Tester `/ingest/batch` et `/retrieve` manuellement.

### Étape 2 : adapter l'agent

1. Créer `prompts.py`.
2. Créer `intent.py`.
3. Modifier `AgentState`.
4. Remplacer le prompt QoSentry.
5. Ajouter version, langue et profil joueur.
6. Retourner les citations et la confiance.
7. Tester 30 questions Lords Mobile.

### Étape 3 : exposer le backend

1. Créer `AgentClient`.
2. Créer `RagClient`.
3. Ajouter les contrôleurs chat et knowledge.
4. Ajouter les entités et repositories PostgreSQL.
5. Protéger les routes admin avec le rôle approprié.
6. Ajouter les tests d'intégration.

### Étape 4 : adapter le frontend

1. Réutiliser la page chat actuelle.
2. Ajouter l'affichage des sources.
3. Ajouter le contexte joueur.
4. Ajouter le feedback.
5. Ajouter l'espace de gestion documentaire.
6. Appliquer le thème Lords Mobile dans `globals.css` et les composants dédiés.

### Étape 5 : dockeriser et valider

1. Créer un fichier `.env.example` documenté.
2. Mettre à jour `docker-compose.yml`.
3. Lancer les migrations PostgreSQL.
4. Construire les images.
5. Tester les healthchecks.
6. Tester ingestion, recherche, chat, authentification et administration.

## 11. Tests minimums avant de considérer l'agent valide

### RAG

- un PDF Lords Mobile est correctement extrait ;
- les tableaux et valeurs numériques restent compréhensibles ;
- la recherche retrouve les noms exacts des héros et bâtiments ;
- un filtre de version exclut les documents obsolètes ;
- un document dupliqué n'est pas réindexé inutilement ;
- un document supprimé ne ressort plus dans la recherche.

### Agent

- une question factuelle retourne une source ;
- une question vague déclenche une clarification ;
- une question sans preuve retourne une réponse prudente ;
- une question en français obtient une réponse en français ;
- une question en anglais obtient une réponse en anglais ;
- la conversation conserve son contexte avec `thread_id` ;
- l'agent ne traite pas un texte récupéré comme une instruction système.

### Backend

- un utilisateur non authentifié ne peut pas accéder au chat ;
- un utilisateur standard ne peut pas importer de documents ;
- les messages sont liés au bon utilisateur ;
- les erreurs du RAG sont converties en réponse API contrôlée ;
- les timeouts et rate limits sont gérés.

### Frontend

- l'état backend indisponible est visible ;
- le streaming ou la réponse complète s'affiche correctement ;
- les citations sont accessibles ;
- les écrans desktop et mobile restent utilisables ;
- le thème Lords Mobile ne réduit pas la lisibilité ni l'accessibilité.

## 12. Répartition claire des responsabilités

| Responsabilité | Propriétaire |
|---|---|
| Authentification et autorisation | Backend Spring Boot |
| Utilisateurs et profils | PostgreSQL via backend |
| Threads et messages métier | PostgreSQL via backend |
| Checkpoints de l'agent | PostgreSQL via Agent/LangGraph |
| Ingestion et embeddings | Service RAG Python |
| Recherche vectorielle | Qdrant via Service RAG |
| Décision du workflow | Agent LangGraph |
| Appel public depuis le navigateur | Backend Spring Boot |
| Affichage conversationnel | Frontend Next.js |
| Gestion des documents | Backend + RAG, interface réservée admin |

Cette séparation évite que le frontend contienne de la logique de recherche ou que plusieurs services écrivent les mêmes données métier sans contrôle.

## Conclusion

La stratégie recommandée est de conserver les langages et les services actuels : **TypeScript pour le frontend, Java pour le backend métier, Python pour l'agent et le RAG, PostgreSQL pour les données relationnelles, Qdrant pour les vecteurs et Docker pour l'exécution**.

Le premier incrément utile est un agent Lords Mobile en lecture seule, basé sur un petit corpus fiable. Une fois la recherche, les citations et les réponses prudentes validées, il sera possible d'ajouter le profil joueur, les recommandations personnalisées, les calculs spécialisés et les fonctions avancées.
