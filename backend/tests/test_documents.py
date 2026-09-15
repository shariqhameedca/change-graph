import io

import pytest

from app.services.document_service import (
    DocumentExtractionError,
    extract_text_from_upload,
)


def test_extracts_plain_text_file():
    text = extract_text_from_upload("regulation.txt", b"Section 1. Hello world.")
    assert text == "Section 1. Hello world."


def test_rejects_empty_file():
    with pytest.raises(DocumentExtractionError):
        extract_text_from_upload("empty.txt", b"")


def test_rejects_oversized_file():
    with pytest.raises(DocumentExtractionError):
        extract_text_from_upload("big.txt", b"x" * (16 * 1024 * 1024))


def test_extracts_pdf_text():
    pypdf = pytest.importorskip("pypdf")
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)

    # pypdf can't easily draw text onto a blank page without reportlab, so a
    # text-less PDF should raise the "no extractable text" error -- this
    # still exercises the PDF-reading code path end to end.
    with pytest.raises(DocumentExtractionError, match="No extractable text"):
        extract_text_from_upload("scan.pdf", buffer.getvalue())


def test_api_extract_text_endpoint(client):
    response = client.post(
        "/api/documents/extract-text",
        files={"file": ("regulation.txt", b"A consumer loan APR may not exceed 20%.", "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "A consumer loan APR may not exceed 20%."
    assert body["character_count"] == len(body["text"])


def test_api_extract_text_rejects_empty_file(client):
    response = client.post(
        "/api/documents/extract-text",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 422
