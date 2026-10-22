# AI Research & Study Assistant

A private, multi-user document research and learning application built on
[Oleh Datsyk's PDF Chat](https://github.com/OlehDatsyk/pdf-chat). The original
[MIT license and copyright](LICENSE) are preserved.

Upload PDF, DOCX, UTF-8 TXT or Markdown, ask cited questions with streamed answers,
search with semantic retrieval/BM25/hybrid RRF, and generate quizzes, flashcards and
study notes. FastAPI + SQLAlchemy/SQLite + LangChain/OpenAI + Qdrant, with the original
Jinja/HTML/CSS/JavaScript architecture and dark mode.

## Local setup (Windows PowerShell)

On this workspace, double-click `Run Research Assistant.bat` to start the app and
open Chrome. It creates `.env` only if missing, generates a session secret, and
defaults to local Qdrant storage without Docker. Add `OPENAI_API_KEY` to `.env`
for AI features, then restart the launcher. Leave its terminal open while using
the app; Ctrl+C stops it. Alternatively run `python scripts/start_local.py`
using the project virtual environment.

Python 3.12 or 3.13 is recommended. The actual automated run on this host used
Python 3.14.2 and passed, with compatibility/deprecation warnings from LangChain's
Pydantic v1 compatibility imports. Docker targets Python 3.12 but was not built here.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
Copy-Item .env.example .env
.\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Edit `.env`: supply your own `OPENAI_API_KEY` and generated `SECRET_KEY`. No API key
is needed to register, sign in, inspect the UI, or run offline tests/evaluations.
Embeddings, chat, summaries and learning generation require a funded OpenAI account.
Your selected document excerpts are sent to OpenAI for generation; uploaded content
is also sent for embedding. OCR stays local. Remote tracing is disabled by default;
do not enable document-bearing LangSmith traces for private material unintentionally.

Start Qdrant with Docker (if installed):

```powershell
docker compose up -d qdrant
$env:DEBUG = "false"
.\.venv\Scripts\python -m migrations
.\.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/register, create an account, then use `/dashboard`, `/upload`
and `/chat`. API documentation: `/docs`. `DEBUG=false` explicitly overrides this
machine's unrelated `DEBUG=release` system variable. Startup applies the same additive
migrations as the explicit migration command.

**Without Docker:** set `QDRANT_PATH=./data/qdrant` in `.env` to use Qdrant's persistent
local engine. Use one application process; local Qdrant has an exclusive storage lock.
Keep the collection and embedding dimensions consistent. Changing embedding model
requires a new collection and reindexing; equal dimensions do not imply compatible models.

**macOS/Linux:** use `.venv/bin/python` in place of `.\.venv\Scripts\python`,
`cp .env.example .env`, and `export DEBUG=false`. The direct requirements are in
`requirements.txt`; `requirements.lock` records the complete tested resolution,
with a platform marker for the Windows-only pywin32 package.

## Docker Compose

After creating `.env`, run `docker compose up --build`. FastAPI listens on localhost
port 8000; Qdrant on localhost port 6333. Named volumes retain application data and
vectors. The app image runs without root and includes Tesseract English OCR.
Qdrant is lazy-connected: check it is ready before uploading. The app health endpoint
reports application liveness, not OpenAI or Qdrant readiness. Container execution was
not verified in this environment because Docker is unavailable.

For HTTPS production set `APP_ENV=production`, `COOKIE_SECURE=true`, `DEBUG=false`
and a random secret of at least 32 characters. Terminate HTTPS at a trusted proxy;
configure forwarded headers only for trusted proxy IPs. Keep Qdrant on a private
network and configure its server authentication for any non-local deployment.

## Using the application

1. Register with a valid email and a password of 12?128 characters; sign in using the
   same browser origin you use for the app.
2. Upload up to ten documents per request (25 MB each by default). Invalid binary
   text, corrupt formats, encrypted PDFs and empty sources receive validation errors.
   Batch ingestion is per-file: successful earlier files remain if a later file fails;
   refresh the library to inspect results before retrying.
3. Select sources in the dashboard. Search any of the three retrieval modes; no
   selection searches all your ready documents. Chat supports all documents or one
   document per conversation; changing scope starts a new conversation.
4. Generate a quiz, flashcards or notes from selected sources and a topic. The backend
   verifies evidence quotes; quiz submission reveals answers, explanations and score.
   Reopen saved materials from the dashboard. Delete them independently if desired.
5. Reindex/retry a failed document in the library. Unchanged ready documents are a
   no-op. Deleting removes its vectors, stored chunks, file and scoped conversations.
   Saved learning materials are retained until explicitly deleted.

Non-paginated citations use section/chunk references; PDF references retain real page
numbers. Source snippets are candidate supporting passages, not a guarantee that every
model claim is correct. Empty context produces a fixed grounded fallback without an
answer-generation call. An LLM can still misinterpret a source; verify important claims.

## Authentication API and CSRF

Sessions use signed, HttpOnly, SameSite=Lax cookies backed by expiring, revocable
hashed session records. Passwords use Argon2. No session credentials enter localStorage.
`POST /api/auth/register` and `/login` accept JSON and reject cross-origin browser
requests. `GET /api/auth/me` returns the current CSRF token; send it in `X-CSRF-Token`
for every authenticated POST/DELETE. `/logout` revokes the server session. Browser JS
handles this automatically. APIs return 401 for missing/expired sessions, 403 for
foreign resources or bad CSRF, and 404 for missing resources.

Document APIs: `/api/upload`, `/api/documents`, `/{id}/summary`, `/{id}/download`,
`/{id}/reindex`; chat: `/api/chat`, `/api/chat/stream`, `/api/conversations`;
search: `/api/search`; learning: `/api/learning/generate/{quiz|flashcards|notes}`,
`/api/learning/{id}`, `/api/learning/{id}/submit`. See `/docs` for schemas.

## Existing installations and FAISS

Back up SQLite and uploads before running a changed application. The versioned SQLite
migration adds columns/tables and leaves legacy ownership NULL. Existing unowned rows
are intentionally inaccessible to every registered user. FAISS files are retained,
never loaded/deserialized, and never silently attributed to the first registrant.
Reupload originals under their intended owner accounts to populate Qdrant. There is
no automatic legacy ownership assignment or FAISS-to-Qdrant conversion. No reset is
needed. This migration runner supports SQLite only.

## Optional OCR

Set `OCR_ENABLED=true` after installing Tesseract and the required language pack.
On Windows install Tesseract from a trusted distribution and add its executable to
PATH. On Debian/Ubuntu: `apt-get install tesseract-ocr tesseract-ocr-eng`.
Set `OCR_LANGUAGE` for installed languages. pypdfium2 renders pages locally; Tesseract
runs only for pages with fewer than 30 extracted characters, with a 30-second per-page
recognition timeout and a pixel limit. Ordinary text PDFs work without Tesseract.
The container includes English; install additional packs to use other languages.
Automated OCR tests use the real renderer with a mocked recognizer; actual Tesseract
recognition was not tested here.

## Tests and measured evaluation

```powershell
.\.venv\Scripts\python -m pytest -q
node --test tests/js/test_upload.test.cjs tests/js/test_dashboard.test.cjs
.\.venv\Scripts\python -m pip check
$env:DEBUG = "false"
.\.venv\Scripts\python -m evaluation.run --output docs/evaluation_report.json --k 3
```

Tests isolate SQL, uploads and Qdrant and mock all paid model calls. Run the opt-in
Qdrant server test with `$env:QDRANT_TEST_URL="http://localhost:6333"` followed by
`python -m pytest -m integration`. It creates/deletes only a uniquely named test
collection. No ordinary tests contact the configured application collection.

See [verification results](docs/VERIFICATION.md) and the actual
[measured evaluation](docs/evaluation_report.md). The evaluation compares identical
questions and documents with deterministic toy embeddings, measuring Hit Rate@K,
MRR@K, expected support and retrieval latency. It does not measure OpenAI semantic
quality, answer faithfulness or a quantitative upstream FAISS baseline.

## Boundaries and limitations

This is a local-development implementation with security boundaries, not a completed
production certification. SQLite, process-local rate limits and corpus-wide in-memory
BM25 suit modest collections and one worker. Use a shared rate limiter, a task queue,
resource quotas, monitored backups and a properly migrated production database before
scaling. Multipart parsing spools before per-file ingestion limits; configure a reverse
proxy request body limit (maximum 251 MB by default) and read timeout. The application
also rejects oversized declared request lengths. Long OCR and ingestion are synchronous
worker tasks; interrupted processing may need explicit reindex/retry. Failed vector
cleanup can leave invisible orphans; retry deletion/reindex when Qdrant recovers.
No email verification, password reset, account deletion, antivirus scanning, distributed
transaction, neural reranker, or real-model groundedness evaluator is included.
Quiz scores are returned on submission; attempt history is not persisted.
DOCX paragraph/table content is extracted; pagination, headers, text boxes and embedded
images are not reconstructed. TXT/Markdown require UTF-8. Browser runtime/visual QA
could not be performed because no browser is available to the automation tools.

[Architecture](docs/ARCHITECTURE.md) ? [Implementation plan](docs/IMPLEMENTATION_PLAN.md) ?
[Changes from upstream](docs/CHANGES_FROM_UPSTREAM.md) ? [Interview guide](docs/INTERVIEW_GUIDE.md) ?
[File inventory](docs/FILE_CHANGES.md)
