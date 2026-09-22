# CompareTable

Side-by-side decision for 2–3 opportunities, asking the same questions of each. The best answer per row is tinted `go-soft`; ties get no tint.

Rows, in order: Requirements met · Biggest gap · Deadline · Effort to apply · Your preferences · Priority. Priority is the last row on purpose.

- Only compares; never recommends one silently — a one-line AI summary above the table (`aa-ai`) may say which and why.
- Max 3 columns; on narrow screens stack into cards.

**Streamlit:** `st.html(table_html)`; selection via `st.multiselect` capped at 3 on the Explore page, or “Compare” on a card.
