"""Extracts plain text from an uploaded regulation document.

This is a thin utility, not part of the compiler: it only turns bytes on
disk into a string. The actual "understand this text" work still happens
in app/compiler, via whichever LLMProvider is configured.
"""

from __future__ import annotations

import io

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB


class DocumentExtractionError(ValueError):
    pass


def extract_text_from_upload(filename: str, content: bytes) -> str:
    if len(content) > MAX_UPLOAD_BYTES:
        raise DocumentExtractionError("File is too large (15 MB limit).")
    if not content:
        raise DocumentExtractionError("The uploaded file is empty.")

    name = (filename or "").lower()

    if name.endswith(".pdf"):
        return _extract_pdf_text(content)

    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return content.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise DocumentExtractionError(
                "Could not decode this file as text. Upload a .txt, .md, or .pdf file."
            ) from exc


def _extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentExtractionError(
            "pypdf is required to read PDF uploads. Install it with 'pip install pypdf'."
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:  # noqa: BLE001 - pypdf raises several exception types
        raise DocumentExtractionError(f"Could not read this PDF: {exc}") from exc

    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 - a single bad page shouldn't fail the whole file
            continue

    text = "\n\n".join(p.strip() for p in pages if p.strip())
    if not text:
        raise DocumentExtractionError(
            "No extractable text was found in this PDF. It may be a scanned "
            "image without a text layer."
        )
    return text
