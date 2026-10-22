# Executed verification and remaining limits

Date: 2026-10-21 (Asia/Karachi). Workspace branch:
`feature/research-study-assistant`. No push or production deployment performed.

## Baseline

- Initial working tree: clean. Requested branch already existed and was active.
- `python -m pytest -q`: failed before collection. Global pytest 7.4.4 could not
  import FixtureDef required by the installed pytest-asyncio plugin.
- Plugin-autoload-disabled baseline: two collection errors, missing langchain_core
  and Settings validation failure from the host's DEBUG=release variable.
- Host interpreter: Python 3.14.2, not the upstream 3.12 target. Global installed
  FastAPI was 0.109.0 and did not match upstream requirements.

## Implementation checkpoints

| Checkpoint | Actual result |
|---|---|
| Loader/chunking foundation | 13 passed |
| Secure RAG backend | 36 passed |
| Learning tools | 42 passed |
| Evaluation, migration, OCR and API expansion | 56 passed, 1 skipped |
| Reindex and verification additions | 58 passed, 1 skipped |
| Final suite | **60 passed, 1 skipped, 70 warnings in 5.76 seconds** |

The final executed command was `.venv\Scripts\python -m pytest -q`.
Tests cover registration/login/logout/expiry/cookie flags/CSRF; ownership across
documents, summaries, downloads, reindex, deletion, conversations, chat/stream,
retrieval and learning artifacts; real text PDF and DOCX extraction, TXT/Markdown,
corrupt/empty/encrypted sources; metadata/chunking; actual Qdrant in-memory ingestion,
filtered search and deletion; partial failure visibility/cleanup; duplicate uploads;
three retrieval modes and fusion; citations in non-streaming and SSE; quiz/flashcard
schemas/evidence/scoring; additive migration preservation; upload/rate errors; and
evaluation reproducibility. Model and OCR recognizer calls are mocked.

The single skipped test requires QDRANT_TEST_URL for a running Qdrant server.
Warnings come from upstream Python 3.14 compatibility/deprecation paths in LangChain,
Pydantic v1 compatibility, FastAPI/Starlette and asyncio. No warnings are suppressed.

## Other checks actually run

- `.venv\Scripts\python -m pip check`: no broken requirements found.
- `python -m compileall -q` over application, router, service, evaluation and test
  modules: passed.
- `node --check` for auth.js, dashboard.js, chat.js and upload.js: passed.
- `git diff --check`: passed; Git reports a harmless LF/CRLF normalization notice
  for the architecture Markdown file.
- OpenAI SDK Responses signature inspected locally: text/max_output_tokens exist.
  Real ChatOpenAI structured-output chains and strict JSON-schema conversion built
  successfully for Quiz, Flashcards and StudyNotes, without making API calls.
- Uvicorn started successfully at 127.0.0.1:8000 using a separate ignored ui-review.db
  and an empty OpenAI key; startup/migrations completed. Review server was stopped.
- Browser check attempted through computer-use: no browsers available. HTML API
  smoke tests passed; runtime interactions, accessibility behavior, layout and visual
  polish could not be checked in a browser.
- Original LICENSE was inspected and remains unchanged. Only runtime placeholder
  files are tracked under data; private databases/uploads/FAISS are ignored.

## Measured retrieval evaluation

Executed with DEBUG=false:

```powershell
.venv\Scripts\python -m evaluation.run --output docs/evaluation_report.json --k 3
```

8 safe documents, 8 questions, 64-dimensional deterministic token-hash embeddings:

| Mode | Hit Rate@3 | MRR@3 | Supporting context@3 | Mean retrieval ms |
|---|---:|---:|---:|---:|
| Dense fixture | 1.000 | 0.792 | 1.000 | 5.857 |
| BM25 | 1.000 | 1.000 | 1.000 | 2.079 |
| Hybrid | 1.000 | 1.000 | 1.000 | 4.183 |

The report records the actual measurement timestamp and individual rankings. Timing
varies by run. No OpenAI embeddings or generation were used. Answer faithfulness and
generation latency are NULL/unmeasured. This is not an upstream FAISS performance
comparison or evidence of general semantic/hybrid quality on real research documents.

## Environmental blockers and unverified work

- No Docker executable: image build, Compose startup and Python 3.12/Linux locked
  environment installation were not executed. The tested lock resolution is Windows
  Python 3.14; Python 3.12/3.13 is recommended for the retained LangChain line.
- No external Qdrant server URL: local engine verified; REST/server integration test
  is available but skipped. Server-specific operational behavior remains unverified.
- No Tesseract executable: real recognizer quality/language packs are unverified.
  Real PDF rendering and mocked recognizer success/missing-engine paths passed.
- No browser: frontend JavaScript syntax and served HTML verified, browser behavior
  and visual/mobile/accessibility checks remain outstanding.
- No real OpenAI request was made: credentials, quota, model availability, generated
  content quality, live SSE latency and actual provider schema acceptance remain
  unverified. SDK chain construction and model-call handling are covered offline.

## Deliberate scope limits

No automatic FAISS/ownership conversion: reupload under intended account. Legacy data
is preserved and NULL-owned rows are inaccessible. No password recovery, email
verification, account deletion, persistent quiz-attempt history, neural reranker,
antivirus scanning, distributed rate limiter or background ingestion queue. The
optional reranker uses lexical overlap. Corpus-wide BM25 is intended for modest local
collections. A reverse proxy must enforce upload body/read limits for production,
including chunked requests; declared-size and per-file limits alone are insufficient
for hostile slow/large multipart traffic. Failed cleanup can leave invisible orphan
vectors; retry reindex/deletion after Qdrant recovers. Generated evidence checks
confirm source quote presence, not the full semantic truth of every model claim.

## Primary interface references consulted

- [Official OpenAI documentation: structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
  describes JSON-schema output and refusal/truncation edge cases. Application-side
  Pydantic/evidence validation and safe errors remain necessary.
- [LangChain Qdrant integration](https://docs.langchain.com/oss/python/integrations/vectorstores/qdrant)
  documents QdrantVectorStore, metadata filtering and local/server modes.
- [Qdrant client documentation](https://qdrant.tech/documentation/) and local pinned
  package interfaces informed filtered search/upsert/delete usage.


## Windows launcher follow-up

Added `Run Research Assistant.bat` and `scripts/start_local.py`. Preparation-only
execution successfully created an ignored `.env` with local Qdrant storage and a
random session secret, leaving the OpenAI key blank. Python compilation passed.
Existing `.env` files are preserved. Chrome launch is deferred until server health
responds; actual browser launch remains unverified because browser tools have no
available browsers. No server was started by preparation-only verification.


## Upload selection regression fix

The upload handler awaited authentication before reading the live FileList. The
file input change handler cleared its value immediately, so the continuation saw
an empty list and displayed the supported-format warning for valid files. Dragged
files could likewise become inaccessible after the drop event returned.

Added a Node VM/DOM test harness for file selection and drop-event lifetimes. Before
the fix, six supported-file/drop tests failed and the unsupported-format test passed.
The handler now snapshots selected File objects synchronously before awaiting auth;
the upload script URL is versioned to refresh cached clients. After the fix, all
seven JavaScript regression tests passed. Run:
`node --test tests/js/test_upload.test.cjs`. JavaScript syntax and git diff whitespace
checks also passed. These tests simulate browser event behavior; they do not claim
an actual Chrome end-to-end run or a real OpenAI indexing request.


## Indexing failure follow-up

Current .env was checked without printing secrets. A real OpenAI embeddings request
using only the public diagnostic string "Connection test." succeeded (1536 dimensions).
The LangChain path also succeeded after a separate tokenizer download completed.
Sandbox-only connection failures were rechecked with authorized network access;
they are not evidence that the user's running app had the same network restriction.
The original saved error was generic, so its historical cause cannot be proven.
Local configured Qdrant storage opened; no collection had yet been created. A separate
persistent temporary Qdrant instance successfully ingested from a worker thread,
searched, deleted and closed using deterministic vectors. No uploaded document text
was sent by these diagnostics, and the failed PDF itself has not been reindexed.

Already chunked text now goes directly to the embedding API, avoiding the extra
first-use tokenizer download, with batches bounded to 64 chunks. OpenAI still enforces
per-input token limits; reduce CHUNK_SIZE if custom large chunks are rejected.
Embedding and vector failures preserve a stage label and sanitized, actionable UI
messages for invalid keys, quota, connectivity, timeouts and Qdrant configuration.
Raw provider errors, keys and document text are never shown in these messages.

Latest full run: 67 passed, 1 external server test skipped, 70 dependency warnings
in 13.98 seconds. Seven frontend upload regression tests also passed. New coverage
verifies tokenizer-free text submission, safe indexing error classification, and
user-facing authentication failures. Restart the app and choose Reindex / retry
for the existing failed document; its stored file has been preserved.


## Confirmed stale-server recovery and actual PDF retry

The user reported that upload still showed the original generic indexing error.
Read-only process inspection confirmed the project launcher/server started at
20:40 local time, while the embedding/error fixes were written at 21:26. The live
server was therefore still executing old imported code. Unrelated Python processes
were not stopped. The saved PDF extracted successfully into 12 pages and 12 chunks.

With authorized network access, stopped only the verified outdated project server
and retried the explicitly identified failed document using scripts/retry_document.py.
The real OpenAI embedding and Qdrant ingestion completed: status=ready, page_count=12,
chunk_count=12. SQL verification found all 12 owner-scoped persisted chunks and a
cleared error message. The original uploaded PDF is preserved. An older duplicate
failed upload remains untouched; the latest failed record was the one repaired.

Restarted the updated app at http://127.0.0.1:8000 and verified status=ok and the new
instance identifier. The app is running in the background, with output redirected
to ignored data/app.stdout.log and data/app.stderr.log. Launcher readiness now checks
its own instance identifier before opening Chrome, so an occupied port cannot cause
it to silently open an older server. Two mocked launcher tests cover this behavior.
The actual upload recovery used the shared indexing service, not a new browser upload
or a chatbot question. Browser interaction itself remains unverified.

Final recovery verification: 69 Python tests passed, 1 external server test skipped;
7 JavaScript upload regression tests passed. Full Python run: 6.42 seconds.


## Flashcard generation repair

The user reported that clicking Generate appeared to do nothing. A diagnostic request
through the running authenticated API reproduced HTTP 502 with an evidence/output
validation error after a successful OpenAI response. The exact rejected model draft
was not logged, so the original mismatch cannot be identified conclusively. The UI
placed errors only in the top-of-page status area, away from the study form.

Added regression tests that initially failed for incorrect source pointers despite
an exact authorized quote, lack of a bounded evidence repair retry, and missing
inline loading/error/selection feedback. The learning service now presents retrieved
excerpts in source order, explicitly distinguishes Source numbers from section/stage
numbers, corrects a citation pointer only if its exact quote occurs in the selected
authorized context, and retries invalid generation once. Unsupported evidence is still
rejected and never persisted. Failure logs contain kind/attempt/type, without source
text or model answers. Study feedback now appears beside the Generate button with
ARIA status/alert roles, and completed materials remain visible if list refresh fails.

After restarting only this project server, the actual flashcard API returned HTTP 201
and saved five flashcards with twelve source references from the user's selected PDF.
Saved material ID: 2220677c-2c60-43fe-9bdc-2bc9d624d905. A diagnostic generation had
also saved a separate valid set; neither set was deleted. Temporary diagnostic login
sessions were removed on completion. No passwords or existing sessions were changed.
Updated dashboard HTML was fetched and confirmed to contain inline study feedback.
Browser visual interaction remains unverified; JS tests simulate DOM interactions.

Final executed checks: 71 Python tests passed, one server integration test skipped,
70 upstream dependency warnings in 8.80 seconds; all 10 JavaScript upload/dashboard
tests passed; JavaScript syntax and Git whitespace checks passed. The updated app
remains available at http://127.0.0.1:8000.
