"""Tests for the HTML render helpers.

Two things matter here and both are easy to get quietly wrong:

* Text from a CV, a posting or a model must never reach the page unescaped.
* The highlight span is measured against the original text, so it has to be
  applied before escaping shifts every offset after an `&` or a `<`.
"""

from __future__ import annotations

import pytest

from oi.contracts import Evidence, Source
from ui.components import hl, verdict_chip


def _ev(text, highlight=None, kind="CV", where="p.1 · Experience"):
    return Evidence(
        text=text, highlight=highlight, source=Source(kind=kind, where=where)
    )


class TestHighlight:
    def test_wraps_the_span_in_the_highlighter_class(self):
        out = hl(_ev("Your DCF model is what they want.", (5, 14)))
        assert '<span class="aa-hl">DCF model</span>' in out

    def test_keeps_the_text_around_the_span(self):
        out = hl(_ev("Your DCF model is what they want.", (5, 14)))
        assert out.startswith("Your ")
        assert out.endswith(" is what they want.")

    def test_without_a_span_returns_plain_escaped_text(self):
        out = hl(_ev("Nothing marked here."))
        assert "aa-hl" not in out
        assert out == "Nothing marked here."


class TestEscaping:
    def test_escapes_angle_brackets(self):
        out = hl(_ev("I wrote <script>alert(1)</script> in my CV."))
        assert "<script>" not in out
        assert "&lt;script&gt;" in out

    def test_escapes_ampersands(self):
        assert "Lazarde &amp; Co." in hl(_ev("Lazarde & Co."))

    def test_escapes_quotes(self):
        out = hl(_ev('He said "hello" loudly.'))
        assert '"hello"' not in out

    def test_escapes_inside_the_highlighted_span_too(self):
        # A hostile span must not become live markup just by being marked.
        out = hl(_ev("Role at <b>Lazarde & Co.</b> ended", (8, 31)))
        assert "<b>" not in out
        assert "&lt;b&gt;" in out
        assert "&amp;" in out

    def test_offsets_stay_aligned_after_escaping(self):
        # "Lazarde & Co." is 13 chars; escaping makes it 17. Applying the
        # span after escaping would slice the wrong characters.
        text = "Lazarde & Co. hired me"
        out = hl(_ev(text, (0, 13)))
        assert '<span class="aa-hl">Lazarde &amp; Co.</span>' in out

    def test_highlight_at_the_very_start_and_end(self):
        assert hl(_ev("abc", (0, 3))) == '<span class="aa-hl">abc</span>'


class TestInvalidSpans:
    """A bad span is a bug upstream. Render the text, never raise at the user."""

    @pytest.mark.parametrize(
        "span", [(5, 2), (-1, 3), (0, 99), (99, 100)]
    )
    def test_out_of_range_or_reversed_spans_fall_back_to_plain_text(self, span):
        out = hl(_ev("short text", span))
        assert "aa-hl" not in out
        assert "short text" in out

    def test_empty_span_marks_nothing(self):
        out = hl(_ev("short text", (3, 3)))
        assert "aa-hl" not in out


class TestVerdictChip:
    @pytest.mark.parametrize(
        "verdict,cls,word",
        [
            ("apply", "is-go", "Apply this week"),
            ("clarify", "is-clarify", "Answer 1 question first"),
            ("skip", "is-skip", "Not for now"),
            ("closed", "is-closed", "Closed"),
        ],
    )
    def test_each_verdict_has_its_class_and_word(self, verdict, cls, word):
        out = verdict_chip(verdict)
        assert cls in out
        assert word in out

    def test_colour_is_never_the_only_signal(self):
        # The three live verdicts carry a glyph as well as a colour, for
        # colour-blind users and for anyone reading a greyscale screenshot.
        for verdict, glyph in [("apply", "✓"), ("clarify", "?"), ("skip", "–")]:
            assert glyph in verdict_chip(verdict)

    def test_closed_is_a_dashed_chip_with_no_glyph(self):
        # Closed is history, not a decision: the design system gives it a
        # dashed outline and no glyph disc.
        out = verdict_chip("closed")
        assert "<i>" not in out
        assert "is-closed" in out

    def test_label_can_be_overridden(self):
        assert "Apply" in verdict_chip("apply", label="Apply")

    def test_a_custom_label_is_escaped(self):
        assert "<b>" not in verdict_chip("apply", label="<b>x</b>")

    def test_an_unknown_verdict_is_rejected(self):
        with pytest.raises(ValueError):
            verdict_chip("maybe")
