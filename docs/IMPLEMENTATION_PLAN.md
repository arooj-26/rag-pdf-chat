# Implementation plan

## Inspection and baseline (2026-10-21)
The upstream application has FastAPI routers, synchronous SQLAlchemy/SQLite models,
Jinja templates, vanilla JavaScript, LangChain LCEL, PDF loaders, a shared FAISS
index, streaming SSE, source snippets, persistent conversations, summaries and dark mode.
There is no authentication. Shared retrieval and unrestricted resource IDs are unsafe
for multiple users. Summary code calls Responses API although pinned openai 1.59.6
predates that interface. Original dependencies target Python 3.12; host is 3.14.2.
Initial pytest failed before collection due to pytest/pytest-asyncio incompatibility.
With plugin autoload disabled, collection failed on absent LangChain and host DEBUG=release.
Git working tree was clean. Requested feature branch already existed and was active.

## Preserve
MIT license, original data and FAISS files, PDF page citations, chunking, SSE event
contract, conversation history, structured summaries, templates and theme.

## Phases
1. Foundation: isolated dependencies, multi-format validated loaders, optional local
   OCR, stable chunk metadata. Run loader/chunking tests.
2. Secure backend: Argon2, signed revocable database sessions, CSRF, owner checks,
   additive versioned SQLite migration, Qdrant adapter, persisted chunks, BM25 and RRF.
   Run authentication, authorization, ingestion, retrieval and streaming tests.
3. Learning: validated quiz/flashcard/notes services and owner-scoped artifacts,
   scoring, dashboard/auth/study pages, safe rendering and frontend error states.
4. Quality: deterministic evaluation, security and integration tests, Docker,
   architecture/setup/upstream/interview documentation and measured verification report.

## Files to change
main.py, config.py, database.py, models.py, schemas.py; upload/documents/chat routers;
PDF/chunking/embedding/vector/retrieval/RAG/memory/prompt services; existing templates
and JavaScript; requirements, env example, gitignore, README, architecture and tests.

## New files
document loader, auth/security/ingestion/hybrid/learning services; auth/learning/search
routers; versioned migration runner; dashboard/login/study templates and scripts;
evaluation fixtures/runner/report; Dockerfile/compose/dockerignore; boundary tests;
upstream change log and interview guide. Preserve FAISS without deserializing it.

## Dependencies
Keep LCEL on compatible LangChain 0.3 components; remove unnecessary monolithic
LangChain/community/FAISS runtime dependencies. Add supported langchain-qdrant,
qdrant-client, rank-bm25, argon2-cffi, itsdangerous, python-docx, pytesseract and
pypdfium2. Use a newer OpenAI SDK with structured chat outputs; bounded timeouts/retries.
Resolve and lock installed transitive versions after verification in project venv.

## Persistence and migration
Add nullable owner IDs to legacy documents/conversations, source_type/content_hash
to documents. Unowned legacy rows remain inaccessible; never assign them to the
first registrant. Add users, sessions, chunks, learning artifacts and migration ledger.
Existing FAISS is retained; documented authenticated reupload is the migration path.
Use stable vector UUIDs and pending/ready/failed states; filter ready SQL records
before vector retrieval to exclude partial ingestion and orphan vectors.

## Tests
Offline fake embeddings and model responses; actual Qdrant in-memory engine for
filters, ingestion and deletion; separate opt-in server integration tests. Exercise
both users across all resource paths, CSRF/revocation, invalid loaders, metadata,
fusion, structured generation and SSE. Evaluate identical safe corpus/questions
with deterministic embeddings and report actual scores, without claiming OpenAI quality.
