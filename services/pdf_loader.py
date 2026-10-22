"""Compatibility entry point for PDF extraction and existing chunking callers."""
from dataclasses import dataclass
from pathlib import Path

class PDFExtractionError(ValueError):
    pass

@dataclass
class ExtractedPage:
    page_number: int | None
    text: str
    section: str | None = None

@dataclass
class ExtractedPDF:
    pages: list[ExtractedPage]
    page_count: int
    source_type: str = "pdf"

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)

    def is_empty(self) -> bool:
        return not self.full_text.strip()


def validate_pdf_header(file_path: Path) -> bool:
    with file_path.open("rb") as stream:
        return stream.read(5) == b"%PDF-"


def extract_pdf_text(file_path: Path) -> ExtractedPDF:
    from services.document_loader import load_document
    return load_document(file_path, ".pdf")
