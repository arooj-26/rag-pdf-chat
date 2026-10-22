"""python -m evaluation.run --output docs/evaluation_report.json --k 3"""
import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path


def run(k: int = 3) -> dict:
    # Evaluation never opens the application's configured DB or vector collection.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from qdrant_client import QdrantClient
    from langchain_core.documents import Document as LCDocument
    from database import Base
    from models import Chunk, Document, User
    from services.hybrid_retrieval import retrieve
    from services.vector_store import QdrantBackend, point_id
    from evaluation.embeddings import FixtureEmbeddings
    dataset = json.loads(Path(__file__).with_name("dataset.json").read_text())
    embeddings = FixtureEmbeddings()
    client = QdrantClient(":memory:")
    backend = QdrantBackend(client, embeddings, "evaluation", embeddings.dimensions)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            db.add(User(id="evaluation", email="fixture@example.test", password_hash="unused-fixture"))
            for source in dataset["documents"]:
                doc_id = source["id"]
                metadata = {"owner_id": "evaluation", "document_id": doc_id, "chunk_id": doc_id + ":0", "chunk_index": 0, "page": None, "document_name": source["filename"], "source_type": "txt"}
                db.add(Document(id=doc_id, owner_id="evaluation", filename=source["filename"], original_filename=source["filename"], file_path="unused-fixture", status="ready"))
                db.add(Chunk(id=point_id(doc_id, 0), owner_id="evaluation", document_id=doc_id, text=source["text"], metadata_json=json.dumps(metadata)))
                backend.ingest([LCDocument(page_content=source["text"], metadata=metadata)])
            db.commit()
            results = {}
            for mode in ("semantic", "keyword", "hybrid"):
                rows = []
                for question in dataset["questions"]:
                    started = time.perf_counter()
                    docs = retrieve(db, "evaluation", question["question"], mode=mode, k=k, backend=backend)
                    milliseconds = (time.perf_counter() - started) * 1000
                    ranks = [i for i, d in enumerate(docs, 1) if d.metadata["document_id"] == question["expected_document"]]
                    rows.append({"question": question["question"], "retrieved": [d.metadata["document_id"] for d in docs], "hit": bool(ranks), "reciprocal_rank": 1 / ranks[0] if ranks else 0,
                                 "support_found": any(question["support"].lower() in d.page_content.lower() for d in docs), "retrieval_latency_ms": round(milliseconds, 3)})
                results[mode] = {"hit_rate_at_k": statistics.mean(r["hit"] for r in rows), "mrr_at_k": statistics.mean(r["reciprocal_rank"] for r in rows),
                                 "support_rate_at_k": statistics.mean(r["support_found"] for r in rows), "mean_retrieval_latency_ms": round(statistics.mean(r["retrieval_latency_ms"] for r in rows), 3), "questions": rows}
            return {"measured_at": datetime.now(timezone.utc).isoformat(), "k": k, "document_count": len(dataset["documents"]), "question_count": len(dataset["questions"]),
                    "embedding_model": "deterministic SHA256 token hash fixture (64 dimensions)", "scope": "Offline retrieval mechanics only; semantic mode uses toy dense embeddings, not OpenAI. Not an upstream FAISS benchmark.",
                    "answer_groundedness": None, "generation_latency_ms": None, "generation_note": "No LLM calls made; generated-answer faithfulness and latency are not measured.", "results": results}
    finally:
        client.close()
        engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/evaluation_report.json")
    parser.add_argument("--k", type=int, choices=range(1, 21), default=3)
    args = parser.parse_args()
    report = run(args.k)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = ["# Measured offline retrieval evaluation", "", report["scope"], "", f"Measured: {report['measured_at']}. {report['question_count']} questions, {report['document_count']} documents, K={args.k}.", "", "| Mode | Hit Rate@K | MRR@K | Supporting context@K | Mean retrieval ms |", "|---|---:|---:|---:|---:|"]
    for mode, result in report["results"].items():
        markdown.append(f"| {mode} | {result['hit_rate_at_k']:.3f} | {result['mrr_at_k']:.3f} | {result['support_rate_at_k']:.3f} | {result['mean_retrieval_latency_ms']:.3f} |")
    markdown.extend(["", report["generation_note"], "", "A tiny lexical fixture cannot establish general retrieval superiority. Inspect per-question rankings in the JSON report. Latency includes SQL corpus loading and varies by machine; ingestion time is excluded."])
    output.with_suffix(".md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(f"Measured report written to {output}")


if __name__ == "__main__":
    main()
