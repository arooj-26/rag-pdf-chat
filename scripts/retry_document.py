"""Retry one explicitly identified failed upload using the current app code.

Uses the configured embedding provider; document text is sent for embedding.
Existing ready documents are left alone. Never prints credentials or source text.
"""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_id", help="UUID of the stored failed document")
    args = parser.parse_args()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ["DEBUG"] = "false"
    from database import SessionLocal
    from models import Document
    from services.document_updates import reindex
    from services.errors import indexing_error_message
    from services.vector_store import get_backend
    with SessionLocal() as db:
        document = db.get(Document, args.document_id)
        if document is None:
            print("Document not found.")
            return 1
        if document.status == "ready":
            print("Document is already indexed; no changes made.")
            return 0
        if document.status != "failed":
            print("Document is not in a failed state. Wait for active processing to finish.")
            return 1
        print("Retrying the stored PDF using the current indexing code...", flush=True)
        try:
            result = reindex(document, db)
            print(f"Indexing succeeded: status={result.status}, pages={result.page_count}, chunks={result.chunk_count}.")
            return 0
        except Exception as exc:
            print("Indexing failed:", indexing_error_message(exc))
            original = getattr(exc, "original", exc)
            print("Failing stage:", getattr(exc, "stage", "indexing"))
            print("Error type:", type(original).__name__)
            return 1
        finally:
            # Release the local Qdrant lock before the browser app is restarted.
            try:
                get_backend().client.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
