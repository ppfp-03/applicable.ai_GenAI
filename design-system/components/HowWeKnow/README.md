# HowWeKnow

Two layers of transparency. Layer 1, always visible: `aa-ai` — the AI's plain-language reason, labelled in `ai` with the ✦ glyph. Layer 2, on demand: `aa-hwk` — a disclosure with method, sources, stored facts and what the system is unsure about.

- Layer 1 is one or two sentences a student would say to a friend. No jargon, no numbers beyond counts.
- Layer 2 uses `aa-kv` rows; machine values in `aa-mono`. Always include an “Unsure about” row, even when it says “Nothing”.
- Model names, temperatures and checksums belong only in layer 2 (or Settings → AI).
- Sky (`ai`, `ai-soft`) marks the AI's voice and nothing else.

**Streamlit:** layer 1 via `st.html()`; layer 2 is `st.expander("How we know")` — style it with the Streamlit CSS in the brand book.
