"""OCR extraction for scanned / image-based PDFs.

This module is the OCR half of document ingestion. It rasterises PDF pages
and reads text off the images with Tesseract. It knows nothing about native
PDF text extraction and nothing about which strategy should be used -- that
choice belongs to `document_loader`.

Requires two system binaries in addition to the Python packages:
  * tesseract  (the OCR engine)
  * poppler    (provides pdftoppm, used by pdf2image to rasterise pages)
See README.md for installation instructions.
"""

from __future__ import annotations

import hashlib

from oi.contracts import SourceDocument

#: Rendering resolution for rasterised pages. 300 DPI is the usual floor for
#: reliable Tesseract accuracy on body text; lower loses small glyphs, higher
#: costs time and memory for little gain.
DEFAULT_DPI = 300


def extract_pdf_ocr(
    pdf_bytes: bytes,
    document_id: str,
    dpi: int = DEFAULT_DPI,
) -> SourceDocument:
    """Extract text from a scanned PDF by rasterising it and running OCR.

    Args:
        pdf_bytes: The raw bytes of the PDF file, as uploaded.
        document_id: Identifier assigned to the resulting document.
        dpi: Resolution used to rasterise each page before OCR.

    Returns:
        A SourceDocument of kind "cv" holding the OCR'd text and the SHA-256
        hash of the original bytes. Provenance is recorded as
        source_ref="uploaded_pdf" (where it came from) and
        extraction_method="ocr" (how the text was read).

    Raises:
        RuntimeError: If the OCR stack is unavailable -- either the Python
            packages or the tesseract/poppler system binaries are missing.
        ValueError: If OCR completes but finds no text at all.
    """
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "OCR support requires the 'pytesseract' and 'pdf2image' packages. "
            "Install them with: pip install -r requirements.txt"
        ) from exc

    try:
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
    except Exception as exc:
        raise RuntimeError(
            "Failed to rasterise the PDF for OCR. This usually means the "
            "poppler system dependency is missing (see README.md)."
        ) from exc

    try:
        pages = [pytesseract.image_to_string(image) for image in images]
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "The 'tesseract' binary was not found on PATH. Install the "
            "Tesseract OCR engine (see README.md)."
        ) from exc

    text = "\n".join(pages).strip()

    if not text:
        raise ValueError(
            f"OCR extracted no text from PDF '{document_id}'. The file may be "
            "blank, or the scan quality may be too low to read."
        )

    return SourceDocument(
        document_id=document_id,
        kind="cv",
        text=text,
        content_hash=hashlib.sha256(pdf_bytes).hexdigest(),
        source_ref="uploaded_pdf",
        extraction_method="ocr",
    )
