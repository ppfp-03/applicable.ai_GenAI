"""Strategy selection for document ingestion.

This is the single entry point callers should use to turn uploaded PDF bytes
into a SourceDocument. It owns one decision and nothing else: whether a PDF
can be read natively, or whether it needs OCR.

Extraction itself lives in the modules it delegates to (`pdf`, `ocr`), which
remain independent of each other.
"""

from __future__ import annotations

import logging

from oi.contracts import SourceDocument
from oi.io.ocr import extract_pdf_ocr
from oi.io.pdf import extract_pdf_text

logger = logging.getLogger(__name__)


def load_document(pdf_bytes: bytes, document_id: str) -> SourceDocument:
    """Load a PDF into a SourceDocument, using OCR only when necessary.

    Native extraction is attempted first because it is fast, lossless and has
    no system dependencies. OCR is the fallback for scanned or image-based
    PDFs, where native extraction yields nothing.

    Args:
        pdf_bytes: The raw bytes of the PDF file, as uploaded.
        document_id: Identifier assigned to the resulting document.

    Returns:
        A SourceDocument. Both strategies set source_ref="uploaded_pdf",
        since the origin is the same either way; `extraction_method` is what
        distinguishes them -- "native_pdf" or "ocr".

    Raises:
        ValueError: If neither strategy produces any text.
        RuntimeError: If OCR was needed but the OCR stack is unavailable.
    """
    try:
        return extract_pdf_text(pdf_bytes, document_id)
    except ValueError:
        logger.info(
            "No native text layer in '%s'; falling back to OCR.", document_id
        )

    return extract_pdf_ocr(pdf_bytes, document_id)
