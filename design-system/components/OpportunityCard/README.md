# OpportunityCard

One opportunity as a decision, in exactly five lines: **verdict + deadline (priority number small, right) → title → company · city · contract → one "why" sentence → requirement bar + one action.** Nothing else lives on the card.

Consumer provides: verdict, deadline, priority + caption ("priority" or "provisional"), title (the whole title is the link to the Opportunity screen), meta line, one why sentence (≤ 20 words, exactly one `aa-hl` span), requirement statuses, one action.

- Classes: `aa-card aa-opp2`, children `.top`, `.title`, `.aa-small`, `.why`, `.foot` (`.req` + one button).
- One button per card. Go → "Add to my week"; clarify → "Answer (10 sec)" (opens the QuestionCard dialog). No "Details" button: the title is the link.
- In a list, only the first card's button is primary; the rest are secondary.
- Inside a section whose title already states the verdict (e.g. *Apply this week*), omit the verdict chip — don't repeat the section title.
- Not-for-now card: `aa-opp2 is-skip`, two lines only (verdict + name, the conflict + fix link).
- Never on the card: factor breakdown, sources, strengths/gaps lists, tags. They live on the Opportunity screen.

**Streamlit:** `with st.container(border=True):` → `st.html(card_top_html)` then `st.columns([3,1])` with the requirement text left and a native `st.button` right.
