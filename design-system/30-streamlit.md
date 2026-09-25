# Streamlit

Il sistema è costruito perché ogni schermata sia realizzabile con layout nativi Streamlit + un blocco CSS iniettato una sola volta.

## 1 · Tema (`.streamlit/config.toml`)

```toml
[server]
enableStaticServing = true          # serve ./static/ (font, logo)

[theme]
base = "light"
primaryColor = "#F26A3D"            # brand
backgroundColor = "#FBF7F2"         # canvas
secondaryBackgroundColor = "#F3EDE4" # surface-sunk (input, expander)
textColor = "#1F1B16"               # ink
linkColor = "#B63F16"               # brand-ink
borderColor = "#E7DFD3"             # line
baseRadius = "12px"                 # radius-md
font = "Figtree"
headingFont = "Bricolage Grotesque"
codeFont = "JetBrains Mono"

[[theme.fontFaces]]
family = "Figtree"
url = "app/static/figtree-latin-400-normal.woff2"
weight = 400
# …ripetere per 500/600/700, Bricolage 600/800, JetBrains Mono 400/500

[theme.sidebar]
backgroundColor = "#FFFFFF"         # surface
```

Le chiavi `font`/`headingFont`/`fontFaces`/`baseRadius`/`borderColor` richiedono una versione recente di Streamlit (1.46+): verificare con `streamlit --version`. Per il tema scuro, stesso file con i valori `dark` dei token.

## 2 · CSS una volta sola

```python
# ui/theme.py
import streamlit as st
from pathlib import Path

def inject():
    css = Path("ui/tokens.css").read_text() + Path("ui/bundle.css").read_text()
    st.html(f"<style>{css}</style>")
```

`tokens.css` è generato da questo design system (sezione *Consuming this system*); `bundle.css` è `components/bundle.css`. Chiamare `inject()` in cima a `app.py`, prima di `st.navigation`.

## 3 · Mappa componenti → Streamlit

| Componente | Render | Interazione nativa |
|---|---|---|
| OpportunityCard | `st.container(border=True)` + `st.html(card_top(opp))` + `st.columns([3,1])` per requisiti e azione | un solo `st.button` per card; `type="primary"` solo sulla prima della lista |
| VerdictChip, PriorityMeter, EvidenceQuote, RequirementRow | `st.html(render_x(data))` | `st.popover("Source")` per la citazione completa |
| QuestionCard | `@st.dialog("One quick question")` | `st.pills(options)` + `st.button("Save answer", type="primary")` |
| RecomputeDelta | `st.html()` in cima a Your week, da `st.session_state.last_delta` | `st.toast("Ranking updated")` |
| HowWeKnow | livello 1 `st.html()`, livello 2 `st.expander("How we know")` | — |
| TrackerBoard | `st.columns(4)`, corsie `st.container(border=True)` | `st.popover` + `st.selectbox("Stage")` |
| CompareTable | `st.html()` | selezione da `st.dataframe(on_select="rerun")` in Explore |
| Tabs Opportunity | `st.tabs(["Overview","Requirements","How we know"])` | `st.toggle("Show sources")` in Requirements |
| Filtri | `st.pills(..., selection_mode="multi")` | — |
| Navigazione | `st.navigation([...], position="sidebar")` + `st.logo("static/applicable-lockup.svg", icon_image="static/applicable-mark.svg")` | — |

## 4 · Regole di implementazione

- **HTML per mostrare, widget per agire.** Un bottone dentro `st.html()` non arriva a Python: usarlo solo per link.
- Ogni componente è una funzione pura `render_x(data) -> str` (Jinja o f-string) in `ui/components.py`; i dati arrivano già con fonti e span evidenziati dal backend.
- Escape obbligatorio di tutto il testo proveniente da CV/offerte (`html.escape`) prima di inserirlo nei template; solo lo span evidenziato viene poi avvolto in `<span class="aa-hl">`.
- Il ricalcolo è deterministico: salvare prima/dopo in `st.session_state` e renderizzare il delta, non ricalcolare due volte.
- `st.cache_data` per il parsing delle offerte; `st.fragment` per la card che si ricalcola, così la pagina non lampeggia.
