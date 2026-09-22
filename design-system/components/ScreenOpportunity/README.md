# ScreenOpportunity

Header: back link · verdict + deadline · title · one meta line (the posting link lives here) · primary "Add to my week" + secondary "Compare" · priority meter right. Then three tabs:

- **Overview** (default from a card): the why in two sentences, top 3 strengths and top 3 gaps side by side, one uncertainty line.
- **Requirements**: RequirementRow — attention rows open, met rows as one line, sources behind the toggle.
- **How we know**: factor breakdown of the priority, method, sources, what the system is unsure about.

Rail: only *Before you apply* (≤ 3 checklist items with a time estimate). Content width ≤ 1040px.

**Streamlit:** `st.tabs(["Overview","Requirements","How we know"])`; rail with `st.columns([3,1])`; checklist with `st.checkbox`.
