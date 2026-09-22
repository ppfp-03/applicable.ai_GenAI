# QuestionCard

A clarification: the single missing fact that blocks a verdict, asked with its reason and its impact. First half of the demo's recompute moment.

Consumer provides: the question (≤ 8 words), the posting quote that makes it necessary, one sentence on why the CV doesn't answer it, 2–4 answers (always including “Not sure”), the impact (verdicts unlocked, possible rank move), what happens on skip.

- Header in `clarify-soft`: “? 1 question · unlocks N verdicts”.
- Answers are pills; the chosen one inverts to `ink`.
- “Not sure” is a valid answer: the opportunity stays provisional, never assumed.
- Questions are ordered by impact across all opportunities, max 3 per week.
- Stored as a declared fact attributed to the user (`YOU` source tag), reused forever.

**Streamlit:** `@st.dialog("One quick question")` + `st.pills(options)` + `st.button("Save answer", type="primary")`; on save, recompute and show RecomputeDelta.
