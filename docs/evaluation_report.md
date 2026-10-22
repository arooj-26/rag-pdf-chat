# Measured offline retrieval evaluation

Offline retrieval mechanics only; semantic mode uses toy dense embeddings, not OpenAI. Not an upstream FAISS benchmark.

Measured: 2026-10-21T14:07:34.678176+00:00. 8 questions, 8 documents, K=3.

| Mode | Hit Rate@K | MRR@K | Supporting context@K | Mean retrieval ms |
|---|---:|---:|---:|---:|
| semantic | 1.000 | 0.792 | 1.000 | 5.857 |
| keyword | 1.000 | 1.000 | 1.000 | 2.079 |
| hybrid | 1.000 | 1.000 | 1.000 | 4.183 |

No LLM calls made; generated-answer faithfulness and latency are not measured.

A tiny lexical fixture cannot establish general retrieval superiority. Inspect per-question rankings in the JSON report. Latency includes SQL corpus loading and varies by machine; ingestion time is excluded.
