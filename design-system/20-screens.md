# Schermate principali

Canvas 1280–1440, sidebar 232px, colonna principale fluida + rail destro 300px (`st.columns([3,1], gap="large")`). Sotto 900px il rail scende sotto la colonna, non sparisce. Renderizzate come componenti nel gruppo *Screens*: *ScreenYourWeek*, *ScreenOpportunity*, *ScreenExplore*, *ScreenProfile*, *ScreenOnboarding*. Tracker e Compare usano a tutta pagina i componenti *TrackerBoard* e *CompareTable*.

## 1 · Your week (home)

Una colonna (max 820px), nessun rail.

```
┌ sidebar ┐┌──────────── main (max 820) ────────────┐
│ logo    ││ TUESDAY 22 SEPTEMBER                   │
│ ● Your  ││ Good morning, Giulia                   │
│   week 1││ 3 applications fit your 5 hours.       │
│ Explore ││ • UniCreda invited you… · See changes  │  ← solo se qualcosa è cambiato
│ Tracker ││                                        │
│ Compare ││ Apply this week                        │
│ Profile ││ [card 1 · primary]                     │
│         ││ [card 2 · secondary]                   │
│         ││ [card 3 · secondary]                   │
│ Budget  ││ Answer first ─────── could add a 4th   │  ← solo la domanda a impatto maggiore
│ ▮▮▮▯▯   ││ [German level?  A1–A2 · B1 · B2+ · ?]  │
│         ││ ┄ – 9 Not for now ┄┄┄┄┄┄┄┄┄┄┄ Show ┄   │
└─────────┘└────────────────────────────────────────┘
```

Dopo una risposta: `RecomputeDelta` compare al posto della domanda per una sessione, poi si chiude in un toast.

## 2 · Opportunity

Header: ← Your week · verdetto + scadenza · titolo · una riga meta (con link al posting) · [Add to my week] [Compare] · priority a destra.
Tre tab: **Overview** · **Requirements** · **How we know**. Rail: solo *Before you apply* (≤ 3 voci).
In *Requirements*: prima le righe che richiedono attenzione (aperte), poi i requisiti soddisfatti su una riga ciascuno; fonti dietro il toggle *Show sources*.

## 3 · Explore

Filtri visibili solo per verdetto (`st.pills`); paese, contratto e scadenza dietro un bottone **Filters** (`st.popover`). Toggle **Cards / Table**. Tabella a 4 colonne + selezione: Decision · Opportunity (ruolo + azienda · città) · Closes · Priority. Selezionando 2–3 righe compare la barra "Compare". Ordinamento: verdetto, poi priority.

## 4 · Compare

`CompareTable` a tutta larghezza; sopra, un `aa-ai` di una frase ("Lazarde is the stronger bet this week: best fit and least effort, but it closes first."); sotto, per ogni colonna "Add to my week".

## 5 · Tracker

`TrackerBoard`: budget in alto, quattro corsie. Clic su una tile → Opportunity con la checklist *Before you apply*. Esiti negativi restano con "What we learned" (gap ricorrenti → suggerimento sul profilo).

## 6 · My profile

Una colonna. Sottotitolo di una riga ("MSc Finance, Bocconi · 14 months of internships · 23 skills"). Tre tab: **From your CV** (prima i 2–3 dati da confermare, poi competenze — 5 visibili + "N more", la fonte appare al tocco —, poi esperienze in timeline compatta), **Preferences** (le 4 essenziali + pesi del ranking), **Facts you told us** (fatti `YOU` datati e modificabili). Versioni del CV in Settings.

## 7 · Onboarding

Tre passi con stepper, una colonna centrale da 640px:
1. **Upload** — drop zone, privacy in 2 righe, fasi di lettura nominate ("Reading · Experience · Skills · Profile").
2. **This is what we understood** — riepilogo in 4 numeri + solo i 2–3 elementi da confermare. CTA "Looks right".
3. **Essentials** — paesi, ruoli, disponibilità (con periodi bloccati), ore a settimana, con la riga *Live effect*. CTA "Show my week". I permessi di lavoro che derivano dalla cittadinanza (es. Svizzera per cittadini UE) si risolvono con le regole, senza domande.

## Stati

- **Vuoto** (nessuna offerta in scope): "Nothing worth your hours yet" + cosa allargare ("Add Switzerland → +6 opportunities").
- **Tutto provvisorio**: la sezione *Answer first* passa in cima.
- **Budget pieno**: le card oltre il budget diventano "Next week" invece di sparire.
- **CV via OCR / bassa confidenza**: banner `clarify-soft` sul profilo, verdetti che dipendono da quei campi marcati provvisori.
- **Errore di lettura offerta**: card `skip` con "We couldn't read this posting — open it ↗", mai un verdetto inventato.
