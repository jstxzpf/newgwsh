# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Docker (primary workflow)

```bash
# Start full dev environment (DB, Redis, API with hot-reload, worker, frontend with HMR)
docker compose -f docker-compose.dev.yml up --build

# Production mode
docker compose up -d

# Rebuild a single service after dependency changes
docker compose -f docker-compose.dev.yml up --build api
```

### Backend (without Docker)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
celery -A app.tasks.worker worker --loglevel=info --concurrency=2
```

### Frontend (without Docker)

```bash
cd frontend
npm install
npm run dev        # Vite dev server on :5173, proxies /api to :8000
npm run build      # TypeScript check + Vite production build
npm run lint       # ESLint
```

### Seed data

```bash
docker compose -f docker-compose.dev.yml exec api python scripts/seed_data.py
```

### Database migrations

Alembic config is at `backend/alembic.ini`. Run from `backend/`:

```bash
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Architecture

This is **泰兴调查队公文处理系统 V3.0** — a government document processing system for a Chinese statistics bureau. The stack is FastAPI backend + React frontend, orchestrated via Docker Compose.

### Backend (FastAPI + Celery)

**Entry point**: `backend/app/main.py` registers 12 API routers under `/api/v1/`:
`auth`, `locks`, `documents`, `sse`, `tasks`, `kb`, `approval`, `chat`, `notifications`, `sys`, `audit`, `exemplars`

**Layer pattern**: `api/v1/*.py` (route handlers) → `services/*.py` (business logic) → `models/*.py` (SQLAlchemy ORM)

**Dual database engines** (`backend/app/core/database.py`):
- `async_engine` (asyncpg) for FastAPI routes — async session via `get_db()` dependency
- `sync_engine` (psycopg2) for Celery workers — sync session via `SyncSessionLocal()`

**Celery workers** (`backend/app/tasks/worker.py`): Three task types — `POLISH` (AI polishing), `FORMAT` (docx generation), `PARSE` (knowledge base chunking). Redis is both broker and result backend. Workers use `select_for_update()` row locks as a state-change gate before mutating documents.

**Redis distributed lock** (`backend/app/core/locks.py`): Per-document editing lock with acquire/heartbeat/release. Lock value stores `{user_id, username, token}`. TTL defaults to 180s, heartbeat interval 90s. Force-release available for admins with audit trail.

**Document workflow** (state machine in `backend/app/models/document.py:VALID_TRANSITIONS`):
`DRAFTING → SUBMITTED → APPROVED` or `SUBMITTED → REJECTED → DRAFTING`
Status transitions are validated via SQLAlchemy `@validates`.

**SIP integrity** (`backend/app/core/sip.py`): HMAC-SHA256 hash over normalized content + reviewer_id + timestamp. Used to detect tampering of approved documents.

**Knowledge base** (`backend/app/models/knowledge.py`): Hierarchical tree (adjacency list with `parent_id`), with `KnowledgeChunk` storing pgvector embeddings (1024-dim, bge-m3 model). HNSW index for vector search + GIN index on content for full-text. Soft-delete cascades down the tree via WITH RECURSIVE and nulls out embeddings.

**Auth**: JWT access tokens (12h) + refresh tokens (7d) via python-jose. Password hashing via argon2 (passlib). Session tracking in `users_sessions` table. `SIP_SECRET_KEY` for content integrity, `SECRET_KEY` for JWT.

**SSE streaming** (`/api/v1/sse`): Server-Sent Events for real-time task progress and chat response streaming.

### Frontend (React 19 + Vite 6)

**Entry**: `frontend/src/App.tsx` — React Router 7 with `AuthGuard` wrapping authenticated routes.

**Routes**: `/login`, `/dashboard`, `/documents`, `/knowledge`, `/approvals`, `/chat`, `/settings`, `/workspace/:doc_id`

**State management**: Zustand stores — `authStore` (JWT token, user info), `editorStore` (document editor state), `taskStore` (async task tracking)

**API client** (`frontend/src/api/client.ts`): Axios instance at `/api/v1`, auto-attaches Bearer token, handles 401 → logout, displays error toasts via antd message.

**Key patterns**:
- `AntiLeakWatermark` component renders user-identifying watermark overlay across all authenticated pages
- `GlobalTaskWatcher` polls SSE task events site-wide
- `EditorA4Paper` renders a physical A4 paper preview with live word count
- Vite proxies `^/api` to the backend container (`http://api:8000`) in dev mode

### Infrastructure

- **PostgreSQL 16** with `pgvector` extension for vector embeddings
- **Redis 7.2** for distributed locks, Celery broker/backend, and SSE pub/sub
- **Ollama** for local LLM inference (configurable via `OLLAMA_BASE_URL`)
- **Nginx** (frontend Dockerfile.prod) serves static assets and reverse-proxies in production

### Configuration

All settings via env vars, loaded by `backend/app/core/config.py` (pydantic-settings). Key vars: `POSTGRES_*`, `REDIS_URL`, `OLLAMA_BASE_URL`, `SECRET_KEY`, `SIP_SECRET_KEY`. The `.env` file at repo root (and `backend/.env`) are gitignored.
