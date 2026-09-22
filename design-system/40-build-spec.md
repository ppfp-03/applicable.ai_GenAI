# Build spec per Claude Code

Questa sezione è scritta per l'agente che costruirà l'interfaccia. Le altre sezioni dicono *come deve essere*; questa dice *come costruirla* in Streamlit.

## Ordine di lettura

1. `README.md` — principi, **Densità**, colore, tipografia, naming.
2. `10-ux-architecture.md` — navigazione, journey, regole di eleggibilità (`RULE`).
3. `20-screens.md` — layout di ogni schermata e stati.
4. `30-streamlit.md` — tema, iniezione CSS, mappa componenti → widget.
5. Per ogni componente: `components/<Nome>/README.md` (regole) + `components/<Nome>/preview.html` (markup di riferimento da riprodurre, classi `aa-` incluse).
6. `tokens.css` (radice di design-system/, font in `fonts/`) e `components/bundle.css`: da copiare in `ui/` così come sono (i font vanno in `static/` e gli url in `tokens.css` aggiornati a `app/static/...`).
7. `screenshots/` (PNG di ogni schermata e componente, chiaro e scuro) e `previews/` (HTML autonomi da aprire nel browser): il riferimento visivo da raggiungere.

Le schermate `Screen*` sono **riferimenti visivi**, non codice da incollare: la sidebar e i bottoni vanno fatti con widget Streamlit nativi.

## Struttura del progetto

```
app.py                      # st.navigation + inject() del tema
.streamlit/config.toml      # tema (30-streamlit.md)
static/                     # font .woff2 + logo svg
ui/
  tokens.css  bundle.css    # dal design system, non modificare a mano
  theme.py                  # inject()
  components.py             # render_*() -> str, funzioni pure
pages/
  your_week.py  explore.py  opportunity.py  tracker.py  compare.py  profile.py  onboarding.py
core/
  models.py                 # dataclass qui sotto
  rules.py                  # eleggibilità deterministica (date, titolo di studio, permessi)
  ranking.py                # priority = somma pesata; penalità; nessun output del modello aggiunto
  llm.py                    # estrazione + spiegazioni, con obbligo di citazione
data/demo.json              # persona Giulia Rossi + opportunità fittizie
```

## Contratti dati (`core/models.py`)

```python
from dataclasses import dataclass, field
from typing import Literal, Optional

Verdict = Literal["apply", "clarify", "skip", "closed"]
ReqStatus = Literal["met", "confirm", "conflict"]
SourceKind = Literal["CV", "JOB", "YOU", "RULE"]

@dataclass
class Source:
    kind: SourceKind
    where: str                    # "p.1 · Experience", "§Requirements, l.2", "CH · EU/EFTA · contract ≥ 12 months"

@dataclass
class Evidence:
    text: str                     # frase completa, verbatim
    highlight: Optional[tuple[int, int]]  # span evidenziato (start, end) dentro text; None = niente evidenziatore
    source: Source

@dataclass
class Requirement:
    ask: str                      # "Master's, graduating 2027–28"
    kind: Literal["must", "nice"]
    status: ReqStatus
    evidence: Optional[Evidence]  # None -> "Not stated in your CV"
    job_source: Source
    question_id: Optional[str] = None   # se status == "confirm"

@dataclass
class Opportunity:
    id: str
    title: str; company: str; city: str; contract: str
    contract_months: Optional[int]
    deadline_days: int
    verdict: Verdict
    why: Evidence                 # la frase "why" della card, con uno span evidenziato
    requirements: list[Requirement]
    priority: int                 # 0–100
    factors: dict[str, float]     # {"cv_fit":34.0, "pref_fit":27.0, "deadline":16.4, "freshness":9.5, "penalty":-2.0}
    provisional: bool
    before_you_apply: list[tuple[str, float]] = field(default_factory=list)  # (voce, ore)

@dataclass
class Question:
    id: str; text: str; reason: Evidence
    options: list[str]            # sempre incluso "Not sure"
    unlocks: list[str]            # id delle opportunità
    impact: str                   # "could move #3 → #2"

@dataclass
class Fact:                       # risposta dell'utente, riusata per sempre
    key: str; value: str; date: str

@dataclass
class Delta:
    opportunity_id: str
    before: tuple[Verdict, int, int]    # verdetto, priority, rank
    after: tuple[Verdict, int, int]
    changes: list[tuple[str, str]]      # ("Requirement “German B2”", "To confirm → Met")
```

## Funzioni di render (`ui/components.py`)

Una funzione pura per componente; restituisce HTML con le classi di `bundle.css`. Tutto il testo esterno passa da `html.escape`, poi si avvolge lo span evidenziato in `<span class="aa-hl">`.

| Funzione | Componente di riferimento |
|---|---|
| `verdict_chip(verdict, label=None)` | VerdictChip |
| `hl(evidence)` · `quote(evidence)` | EvidenceQuote |
| `card_top(opp, show_verdict=True)` | OpportunityCard (tutto tranne il bottone) |
| `req_attention(req)` · `req_line(req)` | RequirementRow |
| `priority_meter(opp)` · `breakdown(opp)` | PriorityMeter |
| `question_head(q)` | QuestionCard (le risposte sono `st.pills`) |
| `delta(d)` | RecomputeDelta |
| `why_block(text)` · facts come `st.expander` | HowWeKnow |
| `tracker_tile(app)` | TrackerBoard |
| `compare_table(opps)` | CompareTable |

## Stato e interazioni

- `st.session_state`: `profile`, `facts`, `opportunities`, `answers`, `last_delta`, `week_plan`, `compare_ids`.
- **Risposta a una domanda** → salva `Fact` → `rules.evaluate()` + `ranking.score()` su tutte le opportunità in `unlocks` → calcola `Delta` → `st.session_state.last_delta` → `st.rerun()`. La home mostra `delta()` al posto della domanda, poi `st.toast`.
- **Add to my week** → crea la tile nel Tracker (stage "Preparing") con il primo elemento di `before_you_apply` come "Next".
- Il ricalcolo è deterministico e istantaneo: nessuna chiamata al modello per cambiare un verdetto.

## Checklist di accettazione

- [ ] Il nome è solo **Applicable.ai**; nessun'altra dicitura di prodotto.
- [ ] Aziende solo fittizie (Lazarde & Co., Bolton Consulting Group, Nestella, J.P. Morrow, Roshe, Morgan Stanfield, UniCreda, Deutsch Bank, Mediobanco, Replai), sempre come monogrammi.
- [ ] Interfaccia in inglese.
- [ ] Ogni schermata rispetta i limiti di **Densità** (un primario, ≤ 3 card prima dello scroll, ≤ 1 blocco nel rail, tabelle ≤ 5 colonne).
- [ ] Ogni affermazione dell'AI ha una fonte (`CV`, `JOB`, `YOU`, `RULE`) o dice "Not stated in your CV".
- [ ] Permessi svizzeri per cittadini UE calcolati da `rules.py` secondo la tabella in *Architettura UX*.
- [ ] Il numero di priority non compare mai senza un verdetto accanto.
- [ ] Tema chiaro e scuro; focus visibile; nessun testo sotto 4.5:1.
- [ ] Nessun bottone HTML che dovrebbe eseguire codice Python: le azioni usano widget nativi.
