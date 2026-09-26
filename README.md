<div align="center">

# 🤖 Amazon Bot Assistant

### Production-Grade, Distributed AI Customer Support Platform

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-Queue-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

> *An end-to-end, production-architecture AI support system — from raw data engineering and NLP pipelines to a React frontend, async microservices backend, persistent PostgreSQL storage, and Nginx gateway. Built to mimic how engineering teams at companies like Intercom or Zendesk would architect an AI copilot.*

</div>

---

## 📑 Table of Contents

- [What This Project Does](#-what-this-project-does)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Data Engineering Pipeline](#-data-engineering-pipeline)
- [Full-Stack Application](#-full-stack-application)
- [AI Workflow (LangGraph)](#-ai-workflow-langgraph)
- [Scaling & Infrastructure](#-scaling--infrastructure)
- [Testing](#-testing)
- [Running the Project](#-running-the-project)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [LangSmith Observability](#-langsmith-observability)

---

## 🎯 What This Project Does

Amazon Bot Assistant is a **full-stack AI customer support platform** that automates responses to customer queries using Retrieval-Augmented Generation (RAG). It:

- Processes and understands customer intent using an **LLM + vector search** pipeline
- Grounds every AI answer in **132,000+ real historical Amazon support conversations**
- Automatically **escalates low-confidence or high-risk queries** to a human agent dashboard
- Persists all conversation history in **PostgreSQL** — surviving container restarts
- Serves a **React/Next.js frontend** with authentication through a single **Nginx** entrypoint
- Handles concurrent requests without blocking via **Redis async task queues**

---

## 🏗️ Architecture

The system runs as **7 Docker containers** communicating via a single Nginx reverse proxy:

```
User Browser
     │
     ▼
┌─────────────────────────────────────────────┐
│            Nginx  :80  (Gateway)            │
│   /          →   Next.js  frontend :3000    │
│   /api/*     →   FastAPI  backend  :8000    │
└─────────────────────────────────────────────┘
          │                    │
          ▼                    ▼
   ┌─────────────┐     ┌─────────────────┐
   │  Next.js    │     │  FastAPI +      │
   │  (React UI) │     │  Uvicorn        │
   │  NextAuth   │     └────────┬────────┘
   └─────────────┘              │ enqueues
                         ┌──────▼──────┐
                         │   Redis     │◄──── RQ Worker
                         │  (Queue +   │      (LangGraph)
                         │   Cache)    │
                         └─────────────┘
                         ┌─────────────┐   ┌──────────────┐
                         │ PostgreSQL  │   │   Qdrant     │
                         │(Persistent) │   │ (Vector DB)  │
                         └─────────────┘   └──────────────┘
```

### Request Lifecycle

| Step | What Happens |
|---|---|
| **1. POST /api/chat** | FastAPI validates the query, enqueues a job to Redis Queue, returns `task_id` instantly |
| **2. Redis Queue** | Job sits in queue; the API is free to handle other requests |
| **3. RQ Worker** | Picks up the job, starts the LangGraph state machine |
| **4. Classification** | LLM classifies intent and scores confidence (0–1.0) |
| **5. RAG Retrieval** | Queries Qdrant for top 20 semantic candidates from 132,000+ conversations |
| **6. Reranking** | Cross-encoder reranker trims to top 5 most relevant examples |
| **7. Generation** | Gemini LLM generates a grounded answer |
| **8. Review Loop** | Reviewer node approves or triggers up to 3 refinement iterations |
| **9. Escalation** | Confidence < 45% or flagged keywords → PostgreSQL ticket created |
| **10. Poll result** | Frontend polls `GET /api/chat/status/{task_id}` until done |
| **11. Save history** | Conversation saved to PostgreSQL; persists across restarts |

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Next.js 15 (App Router, TypeScript) | React UI, SSR, routing |
| **Auth** | NextAuth v4 (Credentials + JWT) | Login, protected routes, session |
| **API Gateway** | Nginx | Reverse proxy, single entrypoint |
| **Backend** | FastAPI + Uvicorn | REST API, async request handling |
| **AI Orchestration** | LangGraph | Multi-step stateful AI workflows |
| **LLM** | Gemini (via LangChain) | Answer generation, classification, review |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 | Semantic query vectorization |
| **Vector DB** | Qdrant | ANN search over 132K+ conversations |
| **Task Queue** | Redis + RQ | Async background job processing |
| **Database** | PostgreSQL 15 + SQLAlchemy | Persistent conversations and tickets |
| **Data Pipeline** | Pandas, BERTopic, langdetect | NLP preprocessing and topic modeling |
| **Observability** | LangSmith | LLM trace monitoring per node |
| **Testing** | Pytest + Selenium | Unit, integration, E2E browser tests |
| **Containers** | Docker Compose (7 services) | Full-stack orchestration |

---

## 📊 Data Engineering Pipeline

The raw data source is the **[Customer Support on Twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter)** dataset — one of the largest publicly available customer service corpora.

### Dataset Numbers

| Stage | Count | Description |
|---|---|---|
| **Raw dataset** | **2,811,774** | All tweets scraped from Twitter |
| **After language filter** | **~480,000** | English-only tweets (`langdetect`) |
| **After null filter** | **~350,000** | Non-empty tweet text |
| **@AmazonHelp queries** | **99,789** | Customer messages targeting Amazon support |
| **Amazon responses** | **132,061** | Official Amazon support replies |
| **Final indexed vectors** | **132,061** | Embedded in Qdrant for RAG retrieval |

### Pipeline Steps

```
Raw CSV (2.8M rows)
    │
    ├─ 1. Load with pandas (chunked, memory-efficient)
    ├─ 2. Filter: author_id == @AmazonHelp or inbound to @AmazonHelp
    ├─ 3. Language detection: langdetect → keep only 'en'
    ├─ 4. Drop nulls, duplicates, bot-generated templates
    ├─ 5. Reconstruct conversations: (query, response) pairs
    ├─ 6. BERTopic modeling → extract semantic intent clusters
    └─ 7. Embed with all-MiniLM-L6-v2 → index into Qdrant
```

### BERTopic Intent Clusters Discovered

| Cluster | Example Queries |
|---|---|
| **Delivery & Shipping** | "Package not arrived", "tracking shows delivered but missing" |
| **Refunds & Returns** | "I need a refund", "how to return this item" |
| **Account Issues** | "Can't log in", "account hacked", "unauthorized charge" |
| **Digital Services** | "Prime Video not loading", "Kindle book not downloading" |
| **Amazon Pay** | "Cashback not received", "payment failed" |
| **Seller Issues** | "Sold by third party, damaged product" |

### Why This Matters for the RAG System

The **99,789 curated customer queries** form the semantic search space. When a user asks a question, Qdrant finds the **top 20 nearest neighbours** by cosine similarity in 384-dimensional embedding space — then a cross-encoder reranker scores and trims to **top 5**. This means every AI answer is grounded in real historical Amazon support language, not hallucinated.

---

## ⚛️ Full-Stack Application

### Frontend (Next.js + NextAuth)

The frontend is a **Next.js 15 App Router** application with TypeScript, CSS Modules, and a fully custom dark design system (no Tailwind).

**Key UI Components:**

| Component | What it does |
|---|---|
| `LoginPage` | Glassmorphism login form with animated gradient orbs |
| `ChatPage` | Full-featured chat with sidebar, message bubbles, typing animation |
| Confidence bar | Live colour-coded bar (green/amber/red) showing AI certainty per response |
| Escalation badge | Shows ticket ID when query is routed to a human agent |
| `AuthProvider` | Client-side `SessionProvider` wrapping the entire app |

**Authentication Flow:**
```
User visits http://localhost
      │
      ▼
getServerSession() → no session?
      │
      ▼
Redirect to /login
      │
User enters demo/password
      │
NextAuth CredentialsProvider → JWT token set
      │
      ▼
Redirect to / (Chat interface)
session.user.id forwarded to API on every message
```

Default credentials: **`demo` / `password`** (swap `authorize()` in the NextAuth handler for a real DB lookup).

---

## 🧠 AI Workflow (LangGraph)

The backend reasoning pipeline is a **LangGraph state machine** — each node is an isolated, testable function that transforms `GraphState`.

```
START
  │
  ▼
classify_query          ← LLM scores intent + confidence
  │
  ├─ confidence < 0.45 or irrelevant ──────────────────────────┐
  │                                                             │
  ▼                                                             │
retrieve (Qdrant: top 20 candidates)                           │
  │                                                             │
  ▼                                                             │
rerank_node (cross-encoder: top 5)                             │
  │                                                             │
  ▼                                                             │
load_user_context (synthetic user profile + orders)            │
  │                                                             │
  ▼                                                             │
generate_answer (Gemini LLM, grounded in top 5 convos)         │
  │                                                             │
  ▼                                                             │
review_answer ─── not approved AND iterations < 3 ──► refine   │
  │                                                             │
  ├─ approved ──► finalize → {status: completed}               │
  │                                                             │
  └─ requires_human ──────────────────────────────────────────►┘
                                                               │
                                                               ▼
                                               create_ticket() → PostgreSQL
                                               {status: escalated}
```

**Escalation triggers:**
- Classification confidence **< 45%**
- Keywords: `fraud`, `hacked`, `stolen`, `legal complaint`, `unauthorized`
- Reviewer explicitly flags `requires_human = True`
- Answer not approved after **3 refinement iterations**

---

## 📈 Scaling & Infrastructure

### Why This Architecture Scales

#### Problem with a naive approach
A basic FastAPI + LLM setup blocks the HTTP thread during LLM inference (typically **3–8 seconds**). Under 10 concurrent users, the server queues requests and response times multiply.

#### Solution: Async task queue
```
FastAPI (stateless, fast)  →  Redis Queue  →  N × Workers (heavy LLM work)
```

- The API returns **immediately** with a `task_id`
- Workers scale **horizontally** — add more worker containers without touching the API
- Redis acts as both the job queue and ephemeral result cache

#### PostgreSQL for persistence
| Before | After |
|---|---|
| Conversation history in Redis (evicted after TTL) | Stored in PostgreSQL (permanent) |
| Human tickets in Redis hash (lost on restart) | Stored in `human_tickets` table |
| API nodes share in-memory state | API nodes are fully **stateless** |

#### Docker Compose service map

| Service | Image | Role |
|---|---|---|
| `nginx` | `nginx:alpine` | Reverse proxy, single entrypoint `:80` |
| `frontend` | `node:20-alpine` | Next.js app `:3000` |
| `api` | `python:3.11-slim` | FastAPI `:8000` |
| `worker` | `python:3.11-slim` | RQ background job processor |
| `redis` | `redis:alpine` | Task queue + result cache |
| `postgres` | `postgres:15-alpine` | Persistent conversation storage |
| `qdrant` | `qdrant/qdrant` | Vector database for RAG |

#### Nginx routing

```nginx
/         →  proxy_pass http://frontend:3000   (Next.js)
/api/*    →  proxy_pass http://api:8000        (FastAPI, path stripped)
```

Single domain, no CORS issues, no port juggling for users.

---

## 🧪 Testing

The project uses a **3-layer test strategy** covering the full stack. The entire suite executes in **< 8 seconds**.

### Layer 1 — Unit Tests
**Files:** `tests/test_reranking.py`, `tests/test_workflow.py`

Tests individual components in pure isolation — no network, no LLM, no DB.

| Test | What it verifies |
|---|---|
| `test_reranker_orders_by_score` | Cross-encoder returns results sorted by relevance |
| `test_classify_routes_to_human_on_low_confidence` | Confidence 0.2 → escalation branch taken |
| `test_review_loop_bounded` | Refinement stops after exactly 3 iterations |
| `test_state_transitions` | Each LangGraph node returns correct keys |

### Layer 2 — API Integration Tests
**File:** `tests/test_api.py`

Tests the full FastAPI layer with **mocked Redis and PostgreSQL** — no live services needed.

| Test | What it verifies |
|---|---|
| `test_health_and_frontend_are_available` | `/health` returns 200 with all service statuses |
| `test_chat_rejects_empty_query` | 422 returned for blank queries |
| `test_chat_persists_conversation_by_session` | Session history written and retrieved from DB |
| `test_clear_session_removes_history` | `DELETE /sessions/{id}` wipes PostgreSQL record |
| `test_workflow_failure_returns_gateway_error` | Worker failure → 502 with error detail |
| `test_human_ticket_can_be_listed_and_claimed` | Full ticket lifecycle: create → list → claim |

### Layer 3 — End-to-End Browser Tests
**File:** `tests/test_selenium.py`

Runs headless Chrome against the live app using **Selenium**.

| Test | What it verifies |
|---|---|
| `test_chat_form_displays_workflow_response` | User types message → polled response renders |
| `test_chat_form_requires_a_query` | Empty submit → UI validation triggered |
| `test_new_conversation_replaces_session` | "New Chat" button resets the message history |
| `test_chat_error_is_rendered` | API error → error message displayed in UI |

### Running Tests

```powershell
# Full suite (< 8 seconds)
.\env\Scripts\python.exe -m pytest -q

# Unit + integration only
.\env\Scripts\python.exe -m pytest tests\test_api.py tests\test_workflow.py -q

# Browser tests (requires Chrome)
.\env\Scripts\python.exe -m pytest tests\test_selenium.py -q

# With coverage report
.\env\Scripts\python.exe -m pytest --cov=amazon_bot --cov-report=term-missing -q
```

---

## 🚀 Running the Project

### Prerequisites
- Docker Desktop running
- `.env` file created from `.env.example`
- `GEMINI_API_KEY` set in `.env`

### Full stack (recommended)

```powershell
# Clone and enter the project
git clone https://github.com/your-username/amazon-bot-assistant.git
cd amazon-bot-assistant

# Copy and fill in your env
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=...

# Launch all 7 services
docker compose up -d --build
```

Then open **[http://localhost](http://localhost)** in your browser.

Login with: **`demo`** / **`password`**

### Check service health

```powershell
docker compose ps
curl http://localhost/api/health
```

### View live logs

```powershell
docker compose logs -f              # all services
docker compose logs -f api          # just the API
docker compose logs -f worker       # just the background worker
docker compose logs -f frontend     # just Next.js
```

### Stop the stack

```powershell
docker compose down          # stop containers (data preserved)
docker compose down -v       # stop + wipe all volumes (fresh start)
```

### Local dev (without Docker)

```powershell
# Start only infrastructure
docker compose up -d qdrant redis postgres

# Terminal 1 — API
.\env\Scripts\python.exe -m uvicorn amazon_bot.api:app --host 0.0.0.0 --port 8000

# Terminal 2 — Worker
.\env\Scripts\python.exe -m amazon_bot.worker

# Terminal 3 — Frontend
cd frontend
npm run dev     # http://localhost:3000
```

### Index the vector database (first run only)

```powershell
docker compose exec api python data\index_data\vector_index_data.py
```

---

## ⚙️ Configuration

Copy `.env.example` to `.env`:

```dotenv
# Required
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash-lite

# Vector DB
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=amazon_customer_queries
QDRANT_CANDIDATE_LIMIT=20

# AI tuning
ESCALATION_CONFIDENCE=0.45
MAX_REVIEW_ITERATIONS=3

# Infrastructure
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://user:password@localhost:5432/amazon_bot

# Optional: LangSmith observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=amazon-bot-assistant
```

> ⚠️ Never commit `.env`. The application raises an explicit `ConfigurationError` at startup if `GEMINI_API_KEY` is missing.

---

## 📁 Project Structure

```
amazon-bot-assistant/
│
├── amazon_bot/                  # Python backend package
│   ├── api.py                   # FastAPI app, endpoints, PostgreSQL session mgmt
│   ├── config.py                # Pydantic settings (env-driven)
│   ├── database.py              # SQLAlchemy engine, SessionLocal
│   ├── models.py                # ORM: Conversation, HumanTicket tables
│   ├── human_bucket.py          # Ticket creation, listing, claiming (PostgreSQL)
│   ├── tasks.py                 # RQ job definitions
│   ├── worker.py                # RQ worker entrypoint
│   ├── retrieval.py             # Qdrant semantic search
│   ├── reranking.py             # Cross-encoder reranker
│   ├── schemas.py               # Pydantic request/response models
│   ├── synthetic_users.py       # Synthetic user/order context
│   ├── llm/
│   │   ├── client.py            # Gemini LLM client
│   │   └── prompts.py           # Classification, answer, review prompts
│   └── graph/
│       ├── builder.py           # LangGraph graph construction
│       ├── nodes.py             # All graph node functions
│       ├── edges.py             # Conditional routing edges
│       └── state.py             # GraphState TypedDict
│
├── frontend/                    # Next.js 15 application
│   ├── app/
│   │   ├── layout.tsx           # Root layout, Inter font, AuthProvider
│   │   ├── page.tsx             # Home → redirects to /login if unauthenticated
│   │   ├── globals.css          # Design system (dark glass, gradients, animations)
│   │   ├── login/page.tsx       # Login route
│   │   └── api/auth/[...nextauth]/route.ts  # NextAuth handler
│   ├── components/
│   │   ├── AuthProvider.tsx     # Client SessionProvider wrapper
│   │   ├── ChatPage.tsx         # Main chat UI (sidebar, bubbles, polling)
│   │   ├── ChatPage.module.css
│   │   ├── LoginPage.tsx        # Glassmorphism login form
│   │   └── LoginPage.module.css
│   ├── types/next-auth.d.ts     # Session type extension
│   ├── next.config.ts           # Standalone output + API proxy rewrite
│   ├── Dockerfile               # Multi-stage build (deps → builder → runner)
│   └── .env.local               # NEXTAUTH_URL, NEXTAUTH_SECRET
│
├── tests/
│   ├── test_api.py              # FastAPI integration tests (mocked Redis + DB)
│   ├── test_workflow.py         # LangGraph unit tests
│   ├── test_reranking.py        # Reranker unit tests
│   └── test_selenium.py         # Headless browser E2E tests
│
├── data_engineering.py          # NLP pipeline: cleaning, BERTopic, embedding
├── docker-compose.yaml          # 7-service orchestration
├── Dockerfile                   # Python API/worker image
├── nginx.conf                   # Reverse proxy config
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Test configuration
├── .env.example                 # Environment template
├── .dockerignore                # Optimised build context
└── .gitignore                   # Excludes secrets, models, node_modules
```

---

## 🔭 LangSmith Observability

Set these in `.env` to enable full LLM trace monitoring:

```dotenv
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=amazon-bot-assistant
```

LangSmith will automatically capture:
- Full graph run timelines per request
- Per-node latency (classify → retrieve → rerank → generate → review)
- Token usage per LLM call
- Input/output for every prompt

---

<div align="center">

Built with ❤️ as a demonstration of production AI system architecture.

**[FastAPI](https://fastapi.tiangolo.com) · [LangGraph](https://langchain-ai.github.io/langgraph/) · [Next.js](https://nextjs.org) · [Qdrant](https://qdrant.tech) · [PostgreSQL](https://postgresql.org)**

</div>
