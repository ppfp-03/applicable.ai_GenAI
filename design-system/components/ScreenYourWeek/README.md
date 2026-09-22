# ScreenYourWeek

The home: **one column (max 820px), no right rail.** Order: date label → greeting title → one-sentence budget → one notice line for what changed (optional) → *Apply this week* (as many cards as fit the hours budget, max 3) → *Answer first* (only the single highest-impact question) → *Not for now* collapsed to one dashed line with its count.

Rules: no KPIs, no methodology block (it lives in *How we know* on each opportunity), no weights. If nothing changed, drop the notice. If there is no open question, drop the section.

**Streamlit:** `st.columns([1,3,1])` or a max-width container; cards per OpportunityCard; question via `st.pills` + save; *Not for now* as `st.expander`.
