# Implementation Plan - Alignment with V3.0 Documentation

This plan outlines the steps to align the existing codebase with the provided V3.0 design documentation, addressing missing features, placeholders, and architectural constraints.

## Phase 1: Models & Infrastructure Refinement

### 1.1 Configuration Expansion
- Update `app/core/config.py` to include:
    - `OLLAMA_TIMEOUT_SECONDS` (120)
    - `AI_RATE_LIMIT_PER_MINUTE` (5)
    - `AUTO_SAVE_INTERVAL_SECONDS` (60)
    - `TASK_MAX_RETRIES` (3)
    - `GIN_CLEANUP_BATCH_SIZE` (5000)
    - `SIP_SECRET_KEY` (Use `SECRET_KEY` as fallback but prefer a dedicated one)
    - `ARCHIVE_ROOT` (For database snapshots)
    - `PROMPTS_ROOT` (`app/prompts`)

### 1.2 Model Alignment
- Update `app/models/knowledge.py`:
    - Add `parse_status` (Enum: UPLOADED, PARSING, READY, FAILED) to `KnowledgeBaseHierarchy`.
    - Add `security_level` (Enum: GENERAL, IMPORTANT, CORE) to `KnowledgeBaseHierarchy`.
- Verify `AsyncTask` in `app/models/task.py` matches `实体模型设计方案.md`.

### 1.3 Prompt Management
- Implement `app/services/prompt_service.py` with `PromptLoader` singleton:
    - Load `.txt` files from `app/prompts/`.
    - Support `reload()` for hot-reloading.
    - Provide `get_prompt(name: str)` method.
- Create initial prompt files in `app/prompts/`:
    - `system_chat.txt`
    - `system_polish.txt`
    - `vocab_blacklist.txt`

## Phase 2: Knowledge Base & AI Service Enhancement

### 2.1 Security Level Consistency (Strict Bidirectional)
- Update `app/services/knowledge_file.py`:
    - Implement logic: if a physical file is reused, but the new logical node has a different security level, enforce a re-parse to ensure `KnowledgeChunk` records have the correct `security_level` tag.

### 2.2 Advanced Chunking & RAG
- Refine `app/services/ai_service.py`:
    - Update `chunk_markdown` to correctly track and inject the full title path (e.g., `H1 > H2 > H3`) into `metadata_json`.
    - Implement `BM25` + `Vector` RRF fusion logic in `chat_completion` (if possible with current PG extensions, else mock the fusion).
    - Ensure `CORE` security level filtering in RAG.

### 2.3 Background Task Refinement
- Update `app/tasks/worker.py`:
    - `polish_document`: Use `PromptLoader` for `system_polish.txt`.
    - `format_document`: Use `python-docx` to implement the GB/T 9704-2023 rules (margins, fonts, line spacing 28pt).
    - Implement `cleanup_gin_index` task using `SKIP LOCKED` as per `实施约束规则.md`.

## Phase 3: API & Lifecycle Implementation

### 3.1 Document Lifecycle
- Update `app/api/v1/endpoints/documents.py`:
    - Add Redis lock token validation in `auto_save`.
    - Implement `POST /{doc_id}/snapshots` for manual snapshots.
    - Ensure `apply-polish` and `discard-polish` clear `ai_polished_content` AND `draft_suggestion`.

### 3.2 System & Maintenance API
- Implement `app/api/v1/endpoints/sys.py`:
    - `GET /status`: DB/Redis/Celery/AI connectivity probe.
    - `GET /prompts`, `PUT /prompts/{filename}`, `POST /reload-prompts`.
    - `POST /db-snapshot`: Trigger asynchronous `pg_dump`.
    - `PUT /config`: Update `SystemConfig` model.

### 3.3 SSE & Real-time Notifications
- Implement `app/api/v1/endpoints/sse.py`:
    - `POST /ticket`: Generate short-lived Ticket tied to `user_id` and `task_id`.
    - `GET /{task_id}/events`: EventStream with Ticket validation (one-time use).
    - `GET /user-events`: Global event stream for `LOCK_RECLAIMED` etc.

## Phase 4: Validation & Compliance
- Run SIP verification tests.
- Verify state machine transitions (Drafting -> Submitted -> Approved/Rejected).
- Verify recursive soft delete of KB directories.
