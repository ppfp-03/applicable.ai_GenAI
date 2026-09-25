# RecomputeDelta

The payoff after an answer: the verdict flips, the number moves, and every change is itemised. Second half of the demo's key moment.

Consumer provides: the answer given, before/after verdict + priority + rank, the list of changed items (requirement, penalty, other opportunities unlocked).

- Border `go-fill` and `shadow-pop` for the first 1.2 s; entry animation `aa-pop` (600 ms), disabled under reduced motion.
- Before side muted on `surface-sunk`; after side on `go-soft`.
- Always list knock-on effects on other opportunities — it proves “asked once, reused forever”.
- If the answer makes things worse (e.g. German A2 → Not for now), use the same layout with the after side in `skip-soft`: honesty over celebration.

**Streamlit:** after the dialog closes, `st.session_state.last_delta` renders this block at the top of *Your week*, then `st.toast("Ranking updated")`.
