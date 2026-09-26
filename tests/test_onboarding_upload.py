"""Onboarding step 1 reads text-based PDFs only: a scan fails clearly, no OCR."""

import importlib
import sys
import types
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core import store
from oi.providers import kimi
from tests.test_candidate_extraction import FakeModelClient, make_fields
from tests.test_io import build_pdf, build_text_pdf

ONBOARDING = str(Path(__file__).resolve().parents[1] / "views" / "onboarding.py")
NO_TEXT = "No usable text was found in this PDF. Scanned PDFs/OCR are not supported in this MVP."


class Tripwire(types.ModuleType):
    """A stand-in OCR package that records any use of it."""

    def __init__(self, name: str, used: list[str]) -> None:
        super().__init__(name)
        self._used = used

    def __getattr__(self, attr: str):
        if attr.startswith("__"):  # introspection (inspect, pickle), not use
            raise AttributeError(attr)
        self._used.append(f"{self.__name__}.{attr}")
        raise AssertionError(f"OCR was invoked: {self.__name__}.{attr}")


@pytest.fixture
def ocr_used(monkeypatch) -> list[str]:
    """Replace the OCR packages with tripwires; the list holds any use."""
    used: list[str] = []
    for name in ["pytesseract", "pdf2image"]:
        monkeypatch.setitem(sys.modules, name, Tripwire(name, used))
    return used


@pytest.fixture
def model(monkeypatch) -> FakeModelClient:
    """The model client onboarding builds, faked; its calls are recorded."""
    client = FakeModelClient(fields=make_fields(education=[], experience=[]))
    monkeypatch.setattr(kimi, "KimiClient", lambda: client)
    return client


def upload(pdf_bytes: bytes) -> AppTest:
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = "1"
    at.run()
    at.file_uploader(key="ob-cv").set_value(("cv.pdf", pdf_bytes, "application/pdf"))
    at.run()
    assert not at.exception
    return at


def test_a_new_account_does_not_show_the_demo_cv() -> None:
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = "1"
    at.run()

    page = "".join(m.value for m in at.markdown)
    assert "Synthetic_CV_Giulia_Rossi.pdf" not in page
    assert "184 KB · 2 pages" not in page
    assert "Reading text · 64%" not in page


def test_a_text_pdf_is_read_into_a_profile(model, ocr_used) -> None:
    at = upload(build_text_pdf("Skills: Python"))

    profile = at.session_state[store.CANDIDATE]
    assert profile is not None
    assert [f.value for f in profile.skills] == ["Python"]
    assert model.calls == ["Skills: Python"]
    assert at.session_state[store.EXTRACTION_ERROR] is None
    assert not at.error
    assert ocr_used == []


def test_the_file_card_shows_the_cv_read_not_the_demo_file(model) -> None:
    pdf = build_text_pdf("Skills: Python")
    at = upload(pdf)

    page = "".join(m.value for m in at.markdown)
    assert "cv.pdf" in page and "Read · 100%" in page and "1 KB" in page
    for demo in ["Synthetic_CV_Giulia_Rossi.pdf", "184 KB · 2 pages", "Reading text · 64%"]:
        assert demo not in page


def test_a_pdf_without_text_fails_clearly_without_ocr_or_extraction(model, ocr_used) -> None:
    at = upload(build_pdf(b""))

    assert at.session_state[store.CANDIDATE] is None
    assert at.session_state[store.EXTRACTION_ERROR] == NO_TEXT
    assert [e.value for e in at.error] == [f"We couldn’t read your CV. {NO_TEXT}"]
    assert model.calls == []
    assert ocr_used == []


def test_an_unreadable_pdf_shows_no_parser_internals(model, ocr_used) -> None:
    at = upload(b"this is not a pdf")

    assert at.session_state[store.CANDIDATE] is None
    assert [e.value for e in at.error] == [f"We couldn’t read your CV. {NO_TEXT}"]
    for internal in ["Poppler", "pdftoppm", "Tesseract", "pypdf", "Traceback"]:
        assert internal.lower() not in at.error[0].value.lower()
    assert model.calls == []
    assert ocr_used == []


def test_no_ocr_ingestion_module_remains() -> None:
    for name in ["oi.io.ocr", "oi.io.document_loader"]:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(name)
