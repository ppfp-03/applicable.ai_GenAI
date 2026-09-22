# Decisioni di design e deviazioni

Questo file registra le scelte prese durante il redesign che **si discostano**
da `design-system/` o dal brief, e perché. `design-system/` non va modificato
(regola di `CLAUDE.md`), quindi le deviazioni vivono qui.

## 1 · Densità: vince il brief

Il design system dice: massimo 3 card decisionali prima dello scroll, nessun
rail nella home. La direzione approvata chiede una dashboard più densa.

**Scelta:** Today mostra 4 card e un rail destro (domande aperte + budget).
Al posto di una riga di KPI c'è una *attention band* di tre celle, ognuna delle
quali è un filtro con un'azione dichiarata, non un numero decorativo.

**Da aggiornare in `design-system/`** quando verrà toccato:
`README.md` § Densità (limiti per schermata) e `20-screens.md` § 1 · Your week.

## 2 · Il verdetto viene dall'eleggibilità, non dai requisiti

Il brief chiede di tenere i vincoli duri visivamente distinti dai fattori
soffici. Applicarlo fino in fondo cambia anche la logica: `verdict_for()` del
design system trasformava una domanda aperta su PowerPoint in *Answer first*,
cioè trattava un gap come una porta chiusa.

**Scelta:** `ranking.verdict_for_opportunity()` decide dall'eleggibilità
(`core/eligibility.py`), più un requisito `must` che l'annuncio esclude
esplicitamente. Un requisito soltanto *da confermare* resta un gap: nominato,
mostrato, ma non blocca. `verdict_for()` resta e viene usata al suo interno.

## 3 · `profile_fit` è calcolato, non scritto nei dati

Nei mockup i punteggi erano fissati a mano. Ora `ranking.profile_fit()` è la
quota di requisiti con una citazione a supporto, e `rescore()` la ricalcola
dopo ogni risposta. I numeri che si vedono nell'app differiscono quindi da
quelli dei mockup: sono il risultato dell'aritmetica, non una decorazione.

## 4 · `pages/` è diventato `views/`

Streamlit attiva la navigazione multipagina legacy in presenza di una cartella
`pages/`, e quella ha la precedenza su `st.navigation`. Con `pages/` la sidebar
mostrava i nomi dei file e il corpo restava vuoto. La cartella si chiama
`views/`; `40-build-spec.md` § Struttura del progetto dice ancora `pages/`.

## 5 · Il CSS è a tre strati

`ui/tokens.css` e `ui/bundle.css` sono copie dal design system e non si
modificano a mano. Tutto ciò che il redesign aggiunge o cambia sta in
`ui/redesign.css`, caricato per ultimo. Così le due copie restano
aggiornabili dal design system senza perdere il lavoro.

## 6 · Il Tracker resta come nel design system

Il brief esclude CRM e task manager. Il design system specifica quattro
corsie, un budget di ore e una checklist *Before you apply*. Su richiesta
esplicita il Tracker resta com'era: è il punto in cui brief e prodotto
divergono, ed è una scelta consapevole.

## 7 · Cosa manca ancora al prodotto, non al design

- **Freshness**: `config/ranking.json` pesa il fattore, ma nessun componente
  registra quando un annuncio è stato visto la prima volta.
- **Pesi per utente**: gli slider in Preferences calcolano l'effetto con
  `ranking.score_with()`, ma `config/ranking.json` è globale: il salvataggio
  non persiste ancora.
- **Vincoli duri**: `config/hard_constraints.json` marca HC_LOCATION,
  HC_WORK_AUTH e HC_GRAD_WINDOW come `development`. `core/eligibility.py` li
  implementa tutti e tre; il file di configurazione va allineato.
