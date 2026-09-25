"""PDF input handling: turn uploaded PDF bytes into a SourceDocument.

This module does text extraction only. It performs no OCR, makes no network
calls, and applies no business rules to the extracted text.
"""

from __future__ import annotations

import hashlib
from io import BytesIO

from pypdf import PdfReader

from oi.contracts import SourceDocument


class PdfExtractionError(ValueError):
    """Uploaded PDF bytes could not be turned into usable text.

    Covers malformed or unreadable files, encrypted files this module cannot
    open, and text-free files such as scans. It stays a `ValueError` so
    existing callers of the previous contract keep working.
    """


def extract_pdf_text(pdf_bytes: bytes, document_id: str) -> SourceDocument:
    """Extract the text of a PDF and wrap it in a SourceDocument.

    Args:
        pdf_bytes: The raw bytes of the PDF file, as uploaded.
        document_id: Identifier assigned to the resulting document.

    Returns:
        A SourceDocument of kind "cv" holding the extracted text, the
        SHA-256 hash of the original bytes, and a "uploaded_pdf" source ref.

    Raises:
        PdfExtractionError: If the bytes cannot be read as a PDF, cannot be
            decrypted, fail during text extraction, or yield no text. A
            text-free file is typically a scanned image, which would need
            OCR (not supported here).
    """
    # Uploaded bytes are untrusted input and pypdf signals damage with
    # whatever the underlying parse happens to raise, not one error family,
    # so every read failure is caught and re-raised as one stable error.
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as error:
        raise PdfExtractionError(
            f"PDF '{document_id}' could not be read: {error}"
        ) from error

    try:
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as error:
        raise PdfExtractionError(
            f"Text extraction failed for PDF '{document_id}': {error}"
        ) from error

    text = "\n".join(pages).strip()

    if not text:
        raise PdfExtractionError(
            f"No text could be extracted from PDF '{document_id}'. "
            "The file may be a scanned image; OCR is not supported."
        )

    return SourceDocument(
        document_id=document_id,
        kind="cv",
        text=text,
        content_hash=hashlib.sha256(pdf_bytes).hexdigest(),
        source_ref="uploaded_pdf",
    )
