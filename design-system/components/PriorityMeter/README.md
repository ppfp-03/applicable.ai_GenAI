# PriorityMeter

The 0–100 priority, deliberately secondary: right-aligned, below the verdict and the reason. It ranks where to spend effort; it never predicts an offer.

- `aa-meter`: number + a 4-part stacked bar (CV fit `ink`, preference fit `ink-muted`, deadline `brand`, freshness `line-control`) + a caption (rank, or “Provisional” in `ink-muted` when a fact is missing).
- `aa-breakdown`: the arithmetic behind it, opened from the meter (popover) or shown on the Opportunity screen. Penalties appear as their own line in `clarify`.
- Never show the number without a verdict chip next to it, and never as a ring or gauge — rings read as “match %”.

**Streamlit:** meter via `st.html()`; breakdown inside `st.popover("How 92 is built")`.
