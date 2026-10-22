# Changes from upstream

Foundation: [OlehDatsyk/pdf-chat](https://github.com/OlehDatsyk/pdf-chat), MIT.
The existing LICENSE and copyright notices are unchanged. No remote push or deployment
was performed. Work is on `feature/research-study-assistant` (already present at inspection).

| Area | Original | Implemented change |
|---|---|---|
| Product | PDF Chat | AI Research & Study Assistant |
| Input | PDF only, community loader with pypdf/PyPDF2 fallback | Local bounded PDF/DOCX/UTF-8 TXT/Markdown loader registry; optional OCR |
| Security | Anonymous, shared resources | Argon2 registration/login, signed revocable session cookies, CSRF, owner enforcement |
| Database | Documents, conversations, messages | Additive migration; users, sessions, owned resources, extracted chunks, learning artifacts |
| Vectors | Shared persisted FAISS; unsafe pickle deserialization enabled | Qdrant abstraction, supported LangChain integration, stable UUIDs, scoped prefilters; FAISS untouched |
| Retrieval | Dense-only, optional document filter | Semantic, BM25 and hybrid RRF; SQL ready/owner gates, optional lexical reranking |
| Chat | LCEL, SSE, snippets, history | Preserved with ownership, scope persistence, safe errors and empty-result fallback |
| Summaries | Raw Responses API but SDK pinned before Responses existed | SDK updated; general loader and validation retained |
| Learning | Absent | Source/evidence-validated quizzes, scoring, flashcards, notes; owner-scoped saved materials |
| UI | Landing/upload/chat, dark mode | Preserved plus auth, workspace/library, study tools, retrieval modes and evaluation |
| Evaluation | No benchmark framework | Deterministic fixture runner, actual JSON/Markdown reports, UI results |
| Tests | Chunking + anonymous health/API smoke tests | Retained/adapted health tests; new security, format, ingestion, migration, OCR, retrieval, learning, SSE and evaluation tests |
| Packaging | Older pins, local launch scripts | Compatible LCEL component pins, full tested lock, non-root Dockerfile, Compose, env examples |

No upstream FAISS benchmark was executed. The functional comparison above is based
on inspected source; measured retrieval comparisons use the **new** Qdrant pipeline
under semantic and hybrid modes on the same deterministic fixture. They do not prove
a real-model quality gain or measure answer faithfulness. See `evaluation_report.md`.

Legacy SQL rows and uploaded files remain intact. NULL-owned legacy rows are private
and unavailable to new accounts. Reupload originals with the correct account to
reindex; no automatic ownership migration or pickle ingestion is provided.

The obsolete redundant PDF backends, monolithic LangChain/community and active FAISS
runtime imports were removed. The PDF extraction dataclasses and compatibility entry
point remain for existing chunking callers. The old anonymous API assertions were
updated to sign in or assert security errors; tests were not removed to hide failures.
Original launch scripts remain, but README commands using the isolated environment
are the supported setup path for the new application.
