# Applicable.ai — istruzioni di progetto

Stiamo costruendo **Applicable.ai** in **Streamlit**: un assistente AI che aiuta studenti e neolaureati a decidere dove vale la pena candidarsi questa settimana, e perché.

Il design system completo è in `./design-system/`. È la fonte di verità per interfaccia, testi e comportamento.

## Prima di scrivere codice

1. Leggi `design-system/README.md` (principi, **Densità**, colore, tipografia, naming).
2. Poi `10-ux-architecture.md`, `20-screens.md`, `30-streamlit.md` e soprattutto `40-build-spec.md`.
3. Per ogni componente: `design-system/components/<Nome>/README.md` + `preview.html`.
4. Guarda `design-system/screenshots/` per il risultato visivo da raggiungere; `design-system/previews/*.html` si aprono nel browser.
5. Proponi un piano breve prima di iniziare.

## Regole non negoziabili

- Il prodotto si chiama solo **Applicable.ai**. Nessun altro nome o sottotitolo.
- Interfaccia in **inglese**.
- Aziende solo fittizie (Lazarde & Co., Bolton Consulting Group, Nestella, J.P. Morrow, Roshe, Morgan Stanfield, UniCreda, Deutsch Bank, Mediobanco, Replai), mostrate come monogrammi.
- Schermate calme: rispetta i limiti della sezione **Densità** (un solo bottone primario, ≤ 3 card prima dello scroll, dettagli dietro toggle/tab/expander).
- Ogni affermazione dell'AI ha una fonte (`CV`, `JOB`, `YOU`, `RULE`) o dice "Not stated in your CV".
- Eleggibilità (date, titolo di studio, permessi di lavoro — inclusi i permessi svizzeri per cittadini UE) solo con regole deterministiche in `core/rules.py`.
- HTML (`st.html`) solo per mostrare; ogni azione usa widget Streamlit nativi.
- Non modificare `design-system/`: copia `tokens.css`, `components/bundle.css`, font e logo in `ui/` e `static/`.

## Ordine di lavoro

1. Struttura del progetto, `.streamlit/config.toml`, tema e iniezione CSS.
2. `data/demo.json` con la persona Giulia Rossi e le opportunità fittizie degli screenshot.
3. Pagina **Your week** + flusso domanda → ricalcolo (il momento chiave della demo).
4. **Opportunity** (tab Overview / Requirements / How we know).
5. Explore, Tracker, Compare, My profile, Onboarding.
6. Niente LLM reale finché la demo non funziona end-to-end con i dati demo.

Dopo ogni pagina: `streamlit run app.py`, confronta con lo screenshot e verifica la checklist in `40-build-spec.md`.
