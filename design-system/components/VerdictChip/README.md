# VerdictChip

The decision label — the first thing on every opportunity. Three decisions plus Closed, never a fourth.

| Class | Word | When |
|---|---|---|
| `aa-verdict is-go` | Apply this week / Apply | All hard requirements met (rule-based) and it fits the effort budget. |
| `aa-verdict is-clarify` | Answer 1 question first | A missing fact blocks the verdict. Shows the number of questions. |
| `aa-verdict is-skip` | Not for now | A hard conflict (dates, degree, authorisation). Slate, not red: deprioritised, never hidden, never an error. |
| `aa-verdict is-closed` | Closed | Deadline passed. Kept for history. |

Always glyph (✓ ? –) + word + colour: colour is never the only signal. Pair with `aa-deadline` (add `is-soon` under 10 days) and `aa-tag` for neutral facts.

**Streamlit:** render with `st.html()`; for filters use `st.pills(["Apply","Answer first","Not for now"], selection_mode="multi")`.
