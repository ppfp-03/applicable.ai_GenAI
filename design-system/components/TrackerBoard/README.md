# TrackerBoard

Where decisions become applications: four lanes — Shortlisted → Preparing → Sent → Outcome — plus the weekly budget bar (`aa-budget`, one segment per hour; `on` planned, `half` partial).

Consumer provides per tile: monogram, role, company, the single next step, days to deadline (brand-ink when < 10).

- Every tile shows exactly one next step (“tailor bullet 3”, “answer German”), taken from the Opportunity's *Before you apply* list.
- Moving a tile is a stage menu, not drag-and-drop (Streamlit-friendly and accessible).
- Outcome tiles are dashed; rejected ones stay, with “What we learned” linking back to the gaps.
- The budget bar counts estimated hours of Preparing items; over budget turns the overflow segments `clarify-fill` with “Over your 5 h” — advice, never a block.

**Streamlit:** `st.columns(4)`; each lane a `st.container(border=True)`; tiles via `st.html()`; stage change with `st.selectbox` in a `st.popover`.
