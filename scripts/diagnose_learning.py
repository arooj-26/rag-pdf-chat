"""Inspect one grounded generation without printing source text or model answers.

Uses the selected document's SQL chunks to avoid competing for the running app's
local Qdrant lock. A successful result is saved to its owner like ordinary generation.
"""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_id")
    args = parser.parse_args()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ["DEBUG"] = "false"
    from database import SessionLocal
    from models import Document, Chunk
    from langchain_core.documents import Document as LCDocument
    from services import learning_service
    from services.learning_schemas import LearningRequest
    from pydantic import ValidationError
    with SessionLocal() as db:
        document = db.get(Document, args.document_id)
        if document is None or document.status != "ready" or not document.owner_id:
            print("Choose a ready, owned document.")
            return 1
        rows = db.query(Chunk).filter_by(document_id=document.id, owner_id=document.owner_id).all()
        docs = [LCDocument(page_content=c.text, metadata=json.loads(c.metadata_json)) for c in rows]
        docs.sort(key=lambda d: d.metadata["chunk_index"])
        learning_service.retrieve = lambda *a, **kw: docs
        real_llm = learning_service._get_chat_llm
        normalize = lambda value: " ".join(value.split()).casefold()
        class InspectableModel:
            def with_structured_output(self, *a, **kw):
                chain = real_llm(streaming=False, temperature=0).with_structured_output(*a, **kw)
                class InspectableChain:
                    def invoke(self, messages):
                        result = chain.invoke(messages)
                        print("Structured output parsed successfully.")
                        for i, card in enumerate(result.cards, 1):
                            number = card.evidence.source_number
                            quote = normalize(card.evidence.quote)
                            matching = [n for n, doc in enumerate(docs, 1) if quote in normalize(doc.page_content)]
                            print({"card": i, "source_number": number, "quote_matches_cited_source": number in matching, "quote_matches_any_source": bool(matching)})
                        return result
                return InspectableChain()
        learning_service._get_chat_llm = lambda **kw: InspectableModel()
        try:
            result = learning_service.generate("flashcards", LearningRequest(document_ids=[document.id]), db, document.owner_id)
            print("Generation succeeded; saved ID:", result.id)
            return 0
        except ValidationError as exc:
            print("Validation fields:", [{"location": e["loc"], "type": e["type"]} for e in exc.errors(include_input=False)])
        except Exception as exc:
            print("Generation error type:", type(exc).__name__)
            if str(exc) in {"Generated too many items", "Generated evidence is not supported by retrieved content"}:
                print("Validation reason:", str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
