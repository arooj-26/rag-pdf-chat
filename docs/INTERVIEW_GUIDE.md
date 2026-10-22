# Technical interview guide

## Problem and product

The application turns private research/learning documents into a searchable and
interactive study workspace. Users upload several formats, ask source-grounded
questions, and generate quizzes, flashcards and notes. It extends the MIT-licensed
PDF Chat repository instead of replacing the entire frontend/backend stack.

## Explain the pipeline in one minute

"I validate the uploaded bytes, extract text locally, split it into overlapping
chunks, and preserve source and ownership metadata. OpenAI embeds those chunks;
Qdrant stores vectors with stable IDs. For each query I first derive the user's
authorized, ready document IDs in SQL. Dense search and scoped BM25 return ranked
chunks, which Reciprocal Rank Fusion combines. The model answers using only those
numbered excerpts, and the UI streams text with source references. Conversations
and study materials are stored under the user's account."

## Components and choices

- **FastAPI/Pydantic:** validated API schemas and composable auth dependencies;
  separate request contracts from ORM models and generation schemas.
- **SQLAlchemy/SQLite:** lightweight local persistence for identities, sessions,
  documents/chunks, conversations and learning artifacts. Versioned additive migration
  avoids destroying existing installations. SQLite is a local scaling limit.
- **LangChain:** keep upstream LCEL chains, splitters, messages and structured model
  integration while isolating retrieval/storage details in services.
- **OpenAI:** embeddings and bounded generation; SDK supports the original Responses
  summaries. Tests replace paid calls and never need a real key.
- **Qdrant:** metadata filters run inside search; stable UUID upserts are retryable.
  The adapter implements ingestion/search/deletion and checks cosine dimensions.
- **BM25 and RRF:** exact identifiers benefit from lexical retrieval. RRF uses ranks,
  avoiding a fragile direct comparison of cosine and BM25 score scales. Default fusion
  contribution is `1/(60+rank)`. Deduplication preserves chunk metadata.
- **Jinja/vanilla JS:** preserves the original application, theme and SSE client;
  no unnecessary SPA rewrite or separate frontend build.
- **Tesseract/pypdfium2:** optional local OCR preserves privacy and PDF page references.

## Document processing and embeddings

PDF parsing preserves page numbers; DOCX headings/tables and Markdown headings become
sections; plain text uses chunk references. File suffix, content parsing, UTF-8 checks,
ZIP expansion limits and size/page/text/pixel limits protect the processing path.
Chunk IDs derive from document/index; metadata includes owner, document, source type,
page/section and chunk index. Overlap reduces information loss at chunk boundaries.
Embedding dimensions must match the collection. Changing model, even at equal
dimensions, requires a new index; vector spaces are not interchangeable.

## Authentication and isolation

Passwords are Argon2 hashes. A signed HttpOnly cookie carries an unpredictable token;
SQL stores its hash, expiry and CSRF token. Logout revokes the session record. Browser
JavaScript keeps the CSRF token in memory; unsafe methods require its header.
SameSite and production Secure cookies complement CSRF rather than replacing it.
Backend ownership checks protect direct resource IDs, not just UI links. SQL scopes
lists, Qdrant filters scope vectors, and BM25 uses only authorized SQL chunks.
Two-user tests exercise chat/stream, history, document download/summary/reindex/delete,
retrieval, study generation/read/delete and quiz submission.

## Changes from the original

Originally the application was anonymous PDF-only chat over a global FAISS index.
I retained the service/router design, splitter metadata, SSE event contract,
persistent messages, summaries and dark mode, then added authentication/ownership,
Qdrant, multi-format loaders, hybrid retrieval, structured study tools and evaluation.
The original OpenAI pin predates Responses; the updated compatible SDK fixes that
interface mismatch. FAISS files remain untouched, with authenticated reupload as the
safe migration path. Legacy data is not automatically granted to a newly registered user.

## Reliability and key challenges

**Cross-store ingestion:** SQLite and Qdrant do not share a transaction. I compute
embeddings first, write deterministic points, and commit SQL `ready` only after success.
Queries use SQL ready IDs and known chunk metadata, so failed/partial indexing remains
invisible. Cleanup is attempted; retry/reindex repairs failures when infrastructure
recovers. This is a visibility guarantee, not a distributed atomicity claim.

**Generated content:** schemas enforce four distinct options and valid answer indices;
every study item has a quote that must occur in its referenced retrieved chunk. Quiz
answers stay server-side until submission. Exact quote checks help catch fabricated
citations, but cannot verify every semantic inference. Chat prompts treat excerpts
as untrusted and return an explicit fallback for empty retrieval.

**Testing on an imperfect host:** baseline collection failed from mismatched global
pytest, absent LangChain and DEBUG=release. A project venv and test environment fixed
isolation without altering system packages. Python 3.14 still reports upstream
compatibility/deprecation warnings; Python 3.12/3.13 is recommended.

## Tests and measured results

See `VERIFICATION.md` for the final executed test count and commands. Offline tests
use disposable SQLite, real Qdrant local engine and deterministic embeddings, with
mocked LLM/recognizer responses. They cover boundaries, extraction, metadata, deletion,
partial failures, validation, SSE and migration preservation. A separate opt-in server
test needs QDRANT_TEST_URL; it was skipped here because no server is available.

Measured evaluation: 8 documents/questions, K=3. Dense fixture MRR was 0.792; hybrid
and keyword MRR were 1.000; each mode had Hit Rate@3 and supporting-context rate 1.000.
These are actual fixture results, not OpenAI scores, upstream FAISS comparisons,
production benchmarks or proof of general hybrid superiority. LLM faithfulness and
generation latency were not measured. See JSON per-question rankings and measured
retrieval timings; exact timings vary by run/machine.

## Honest limitations and next steps

No real OpenAI/Qdrant server/Tesseract integration, container build or browser visual
QA was verified on this host. A production rollout needs shared rate limiting,
background jobs, stronger operational quotas, monitoring, backups, recovery/account
features and a larger representative evaluation dataset with a faithfulness rubric.
BM25 currently materializes the authorized corpus per request; this is simple and
auditable but should be indexed/cached for larger tenants. The optional reranker is
lexical overlap rather than a cross-encoder. Quiz attempts are scored but not stored.
