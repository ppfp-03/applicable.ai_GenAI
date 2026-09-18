"""PDF input handling: turn uploaded PDF bytes into a SourceDocument.

This module does text extraction only. It performs no OCR, makes no network
calls, and applies no business rules to the extracted text.
"""

from __future__ import annotations

import hashlib
from io import BytesIO

from pypdf import PdfReader

from oi.contracts import SourceDocument


def extract_pdf_text(pdf_bytes: bytes, document_id: str) -> SourceDocument:
    """Extract the text of a PDF and wrap it in a SourceDocument.

    Args:
        pdf_bytes: The raw bytes of the PDF file, as uploaded.
        document_id: Identifier assigned to the resulting document.

    Returns:
        A SourceDocument of kind "cv" holding the extracted text, the
        SHA-256 hash of the original bytes, and a "uploaded_pdf" source ref.

    Raises:
        ValueError: If the PDF yields no text. This typically means the file
            is a scanned image, which would need OCR (not supported here).
    """
    reader = PdfReader(BytesIO(pdf_bytes))

    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()

    if not text:
        raise ValueError(
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
