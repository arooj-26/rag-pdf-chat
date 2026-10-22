import pytest
from sqlalchemy import create_engine, text, inspect
from migrations import migrate
from services.document_loader import load_document
from services.pdf_loader import PDFExtractionError
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


def text_pdf(path):
    writer = PdfWriter()
    page = writer.add_blank_page(300, 300)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 250 Td (Mitochondria generate ATP through cellular respiration.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(path)


def test_real_pdf_text_and_page(tmp_path):
    path = tmp_path / "biology.pdf"
    text_pdf(path)
    document = load_document(path)
    assert "Mitochondria generate ATP" in document.full_text
    assert document.pages[0].page_number == 1


def test_ocr_missing_engine(tmp_path, monkeypatch):
    import pytesseract
    from config import get_settings
    path = tmp_path / "scan.pdf"
    writer = PdfWriter(); writer.add_blank_page(100, 100); writer.write(path)
    monkeypatch.setattr(get_settings(), "ocr_enabled", True)
    def missing(*args, **kwargs):
        raise pytesseract.TesseractNotFoundError()
    monkeypatch.setattr(pytesseract, "image_to_string", missing)
    with pytest.raises(PDFExtractionError, match="OCR is unavailable"):
        load_document(path)


def test_ocr_preserves_pages(tmp_path, monkeypatch):
    import pytesseract
    from config import get_settings
    path = tmp_path / "scan.pdf"
    writer = PdfWriter(); writer.add_blank_page(100, 100); writer.write(path)
    monkeypatch.setattr(get_settings(), "ocr_enabled", True)
    monkeypatch.setattr(pytesseract, "image_to_string", lambda *a, **kw: "Scanned page recovered text")
    document = load_document(path)
    assert document.pages[0].page_number == 1
    assert "recovered" in document.full_text


def test_additive_migration_preserves_data(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documents (id VARCHAR(36) PRIMARY KEY, original_filename TEXT)"))
        conn.execute(text("CREATE TABLE conversations (id VARCHAR(36) PRIMARY KEY, title TEXT)"))
        conn.execute(text("INSERT INTO documents VALUES ('legacy', 'private.pdf')"))
        conn.execute(text("INSERT INTO conversations VALUES ('old-chat', 'Private chat')"))
    migrate(engine)
    migrate(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT original_filename, owner_id FROM documents")).one() == ("private.pdf", None)
        assert conn.execute(text("SELECT title, owner_id FROM conversations")).one() == ("Private chat", None)
        assert conn.execute(text("SELECT COUNT(*) FROM schema_migrations")).scalar() == 1
    engine.dispose()
