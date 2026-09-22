# Button

Four variants; one `aa-btn-primary` (tangerine) per view — it is always the next step of the decision ("Add to my week", "Answer", "Continue").

- `aa-btn-primary` — the one next step. Label in `on-brand` (ink), never white.
- `aa-btn-secondary` — neutral actions (Open posting, Compare). Border `line-control`.
- `aa-btn-ghost` — dismissive or low-stakes (Not interested, Skip for now).
- `aa-btn-ai` — opens an explanation (Why #1?, How we know). Sky = the AI's voice.
- Add `aa-btn-sm` in dense rows (cards, tables).

Labels are verbs in sentence case, max 3 words. No icons except ↗ for leaving the app.

**Streamlit:** native `st.button(type="primary")` is restyled by the theme (`primaryColor` = brand) — prefer it over HTML buttons wherever a click must reach Python. Use HTML `aa-btn` only in static mockups or links.
