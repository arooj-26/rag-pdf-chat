"""
services/chunking_service.py
------------------------------
Splits extracted PDF text into overlapping chunks suitable for
embedding, using LangChain's `RecursiveCharacterTextSplitter`. Each
chunk is returned as a LangChain `Document` with rich metadata
(document id, filename, page number, chunk index) so the retriever
can later cite exact sources.
"""

from __future__ import annotations

from typing import List

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import get_settings
from services.pdf_loader import ExtractedPDF

settings = get_settings()


def build_text_splitter(
    chunk_size: int | None = None, chunk_overlap: int | None = None
) -> RecursiveCharacterTextSplitter:
    """Create a configured RecursiveCharacterTextSplitter.

    The recursive splitter tries a prioritized list of separators
    (paragraph, then line, then sentence, then word) so chunks break
    at natural language boundaries whenever possible, which keeps
    each chunk semantically coherent for embedding.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=settings.chunk_overlap if chunk_overlap is None else chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
    )


def chunk_document(
    extracted: ExtractedPDF,
    document_id: str,
    filename: str,
    owner_id: str | None = None,
) -> List[LCDocument]:
    """
    Convert an ExtractedPDF into a flat list of LangChain Documents,
    one per chunk, each carrying metadata used later for citations.
    """
    splitter = build_text_splitter()
    all_chunks: List[LCDocument] = []
    chunk_index = 0

    for page in extracted.pages:
        if not page.text or not page.text.strip():
            continue

        page_chunks = splitter.split_text(page.text)
        for chunk_text in page_chunks:
            if not chunk_text.strip():
                continue
            metadata = {
                "document_id": document_id,
                "document_name": filename,
                "page": page.page_number,
                "chunk_index": chunk_index,
                "chunk_id": f"{document_id}:{chunk_index}",
                "owner_id": owner_id,
                "source_type": extracted.source_type,
                "section": page.section,
            }
            all_chunks.append(LCDocument(page_content=chunk_text, metadata=metadata))
            chunk_index += 1

    return all_chunks
