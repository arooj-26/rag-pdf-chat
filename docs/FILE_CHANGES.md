# File changes

29 modified tracked files; 52 new files. Generated runtime state and the virtual environment are excluded.

## Modified files

| File | Purpose |
|---|---|
| `.env.example` | Document all application, Qdrant, session, retrieval and OCR settings. |
| `.gitignore` | Exclude private runtime state and local vector files. |
| `README.md` | Replace setup guide with current product, exact commands and limitations. |
| `config.py` | Validate settings; add Qdrant, auth, retrieval, OCR and resource controls. |
| `database.py` | Apply additive versioned schema migration at startup. |
| `docs/ARCHITECTURE.md` | Document complete request, storage, security and RAG flows. |
| `main.py` | Register authentication, search, learning, evaluation and UI routes; guards. |
| `models.py` | Add ownership, users, revocable sessions, chunks and learning artifacts. |
| `pytest.ini` | Register external integration test marker. |
| `requirements.txt` | Pin compatible direct dependencies for the implemented stack. |
| `routers/health.py` | Report the launch instance identifier for reliable readiness checks. |
| `routers/chat.py` | Authorize every conversation/chat/stream action and sanitize errors. |
| `routers/documents.py` | Owner-scoped list/read/delete/summary/download/reindex routes. |
| `routers/upload.py` | Thin authenticated multi-format batch upload endpoint. |
| `schemas.py` | Extend source/document metadata without inventing page numbers. |
| `services/chunking_service.py` | Preserve source/owner/section/stable chunk metadata; honor zero overlap. |
| `services/conversation_memory.py` | Owner-aware conversation creation, lookup and lists; retain scope. |
| `services/embedding_service.py` | Configure embedding dimension, timeout and bounded retries. |
| `services/pdf_loader.py` | Keep extraction dataclasses and compatibility entry point. |
| `services/prompt_templates.py` | Treat source instructions as untrusted and request citations. |
| `services/rag_service.py` | Threaded streaming retrieval, source references, fallback and bounded generation. |
| `services/retriever.py` | Maintain LangChain BaseRetriever integration over scoped hybrid service. |
| `services/vector_store.py` | Replace active FAISS implementation with Qdrant adapter/protocol. |
| `static/js/chat.js` | CSRF-compatible fetch, section/chunk citations and conversation scope changes. |
| `static/js/upload.js` | Multiple formats, CSRF, timeout and escaped error rendering. |
| `templates/chat.html` | Retain streamed chat and add workspace/auth navigation. |
| `templates/index.html` | Rename product and expose account/workspace links. |
| `templates/upload.html` | Multi-format accept/labels and account navigation. |
| `tests/test_health.py` | Retain smoke tests and adapt protected API expectations; add new page/report checks. |

## New files

- `tests/js/test_dashboard.test.cjs`
- `scripts/diagnose_learning.py`
- `scripts/verify_learning.py`
- `tests/test_launcher.py`
- `scripts/retry_document.py`
- `.dockerignore`
- `Run Research Assistant.bat`
- `scripts/start_local.py`
- `Dockerfile`
- `docker-compose.yml`
- `docs/CHANGES_FROM_UPSTREAM.md`
- `docs/FILE_CHANGES.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/INTERVIEW_GUIDE.md`
- `docs/VERIFICATION.md`
- `docs/evaluation_report.json`
- `docs/evaluation_report.md`
- `evaluation/__init__.py`
- `evaluation/dataset.json`
- `evaluation/embeddings.py`
- `evaluation/run.py`
- `migrations.py`
- `requirements.lock`
- `routers/auth.py`
- `routers/evaluation.py`
- `routers/learning.py`
- `routers/search.py`
- `services/document_loader.py`
- `services/document_updates.py`
- `services/errors.py`
- `services/hybrid_retrieval.py`
- `services/ingestion.py`
- `services/learning_schemas.py`
- `services/learning_service.py`
- `services/request_guard.py`
- `services/security.py`
- `static/css/research.css`
- `static/js/auth.js`
- `static/js/dashboard.js`
- `templates/auth.html`
- `templates/dashboard.html`
- `tests/conftest.py`
- `tests/js/test_upload.test.cjs`
- `tests/test_api_quality.py`
- `tests/test_evaluation.py`
- `tests/test_hybrid.py`
- `tests/test_indexing_errors.py`
- `tests/test_learning.py`
- `tests/test_loaders.py`
- `tests/test_migration_ocr.py`
- `tests/test_qdrant_integration.py`
- `tests/test_security_rag.py`

The existing MIT LICENSE, original copyright, legacy data files and FAISS artifacts were not changed. New source, tests, fixtures, packaging and documentation remain uncommitted for review; no push was performed.
