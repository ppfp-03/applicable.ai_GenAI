# RequirementRow

Requirement vs evidence, in two densities. **Attention rows** (`aa-req`: to confirm, conflict) are shown open with *They ask / You have* and their action. **Met rows** (`aa-reqline`) collapse to one line: ✓ · requirement · your highlighted evidence. Sources are hidden until the user flips **Show sources** (`aa-toggle`, adds `.show-src` on the container).

Consumer provides per row: status, requirement in plain words, the user's evidence (highlighted span, a `YOU` fact, a `RULE` outcome, or "Not stated in your CV"), source strings (`CV`, `JOB`, `YOU`, `RULE`).

- Order: attention rows first, then met rows. Header states the count in words: "5 of 6 met · 1 to confirm".
- The action on an attention row is secondary ("Answer") — the page's primary stays "Add to my week".
- No "Must / Nice to have" pills on met rows; on attention rows only when it changes the decision.
- **Work authorisation** is always a `RULE` row, never a model judgement. Switzerland, EU/EFTA citizens: ≤ 3 months → no permit; > 3 and < 12 months → L permit (EU/EFTA) for the contract length; ≥ 12 months or permanent → B permit (EU/EFTA), valid 5 years. Contract length missing from the posting → attention row "To confirm", never a guessed band.

**Streamlit:** header row with `st.toggle("Show sources")`; rows via `st.html()`; the Answer button native, opening the QuestionCard dialog.
