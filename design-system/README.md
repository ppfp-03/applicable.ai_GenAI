Applicable.ai è un assistente AI per studenti universitari e giovani laureati: legge CV, preferenze e offerte e dice *dove vale la pena candidarsi questa settimana, e perché*. Il design system traduce un'idea sola: **decisione prima, motivo subito dopo, numero per ultimo** — e ogni motivo è una citazione evidenziata, mai una parafrasi.

Direzione visiva: **"Highlighter"** — cordiale come un quaderno di uno studente, rigorosa come un dossier. Carta calda, un arancio mandarino per agire, il giallo evidenziatore per le prove, il blu cielo per la voce dell'AI.

## Principi

1. **Decision-first.** Ogni opportunità si apre con un verdetto (`aa-verdict`): *Apply this week*, *Answer 1 question first*, *Not for now*. Il punteggio 0–100 esiste ma è secondario (`aa-meter`), a destra, sempre scomponibile.
2. **Quote or abstain.** Ogni affermazione dell'AI su di te o sull'offerta porta le parole esatte evidenziate (`aa-hl`) e la fonte (`aa-src`: `CV`, `JOB`, `YOU`, `RULE`). Se non c'è una fonte: "Not stated in your CV".
3. **Ask, don't assume.** Un fatto mancante diventa una domanda (`aa-q`) con il suo impatto dichiarato; la risposta mostra subito cosa è cambiato (`aa-delta`).
4. **Nothing hidden, only deprioritised.** Le opportunità incompatibili restano visibili in *Not for now*, in grigio ardesia, con il requisito che le blocca.
5. **Una lista finita, non un feed.** Il numero di card "Apply" è limitato dal budget di ore che l'utente ha impostato.
6. **Calma prima di tutto.** Ogni schermata risponde a una domanda sola e mostra solo ciò che serve per decidere; il resto è a un tocco di distanza (regole in *Densità*).
7. **Trasparenza a livelli.** Livello 1 sempre visibile: il motivo in parole semplici. Livello 2 su richiesta: *How we know* (metodo, fonti, incertezze). Nomi di modelli, temperature e checksum solo nel livello 2.

## Densità

Nessuna schermata deve sembrare piena. Quando le informazioni sono tante, non si rimpiccioliscono: si **ordinano, si raggruppano o si nascondono dietro un gesto**.

**Limiti per schermata**

- Una domanda sola per schermata (Your week: "cosa faccio questa settimana?"; Opportunity: "mi candido?").
- Un solo bottone primario visibile. Nelle liste, solo la prima card ha il bottone primario.
- Massimo 3 card decisionali prima dello scroll; massimo 3 sezioni per pagina.
- Rail laterale: al massimo un blocco, e solo se serve all'azione (es. *Before you apply*). La home non ha rail.
- Una card = 5 righe (verdetto · titolo · meta · perché · requisiti + azione). Mai liste, tag o fonti dentro una card.
- Tabelle: massimo 5 colonne; filtri visibili solo per il verdetto, il resto dietro "Filters".
- Testo di corpo: una frase per blocco dove possibile; il "why" ≤ 20 parole.
- Larghezza contenuto: 820px per le pagine a colonna, 1040px con rail.

**Come alleggerire (in quest'ordine)**

1. **Togli ciò che si ripete**: un chip che ripete il titolo della sezione, pesi e metodologia mostrati in più punti.
2. **Comprimi ciò che va bene**: i requisiti soddisfatti diventano una riga; le opportunità "Not for now" diventano una riga tratteggiata con il conteggio.
3. **Metti prima ciò che richiede attenzione**: righe da confermare e conflitti aperti, il resto sotto.
4. **Sposta i dettagli dietro un gesto**: fonti → toggle *Show sources*; scomposizione del punteggio → tab *How we know*; storico → *See changes*.
5. **Dividi in tab** solo quando un'area ha davvero domande diverse (Overview / Requirements / How we know). Massimo 3 tab.

**Mai nella vista principale**: KPI decorativi, pesi del ranking, parametri del modello, checksum, più di una citazione per card, testo esplicativo sul prodotto.

## Naming

- Il prodotto si chiama solo **Applicable.ai**. Nessun sottotitolo, descrittore o nome alternativo nell'interfaccia, nei materiali o nel codice.
- Le aziende nei dati demo sono nomi fittizi somiglianti ai reali (Lazarde & Co., Bolton Consulting Group, Nestella, J.P. Morrow, Roshe, Morgan Stanfield, UniCreda, Deutsch Bank, Mediobanco, Replai), sempre con monogramma, mai col logo vero.

## Voce e contenuti

L'interfaccia è in **inglese**, tono da compagno di corso più esperto: diretto, caldo, mai da recruiter.

- Seconda persona, frasi brevi, sentence case: "3 applications fit the 5 hours you set for this week."
- Verbi d'azione sui bottoni, max 3 parole: "Add to my week", "Answer (10 sec)", "Compare".
- Il "why" di una card è una frase ≤ 25 parole con **una** citazione evidenziata (qui tra ==…==): "Your ==DCF model for a €40M target== is exactly the valuation work they ask for."
- Mai probabilità di offerta, mai confronti con altri candidati, mai "Recommended for you" senza motivo.
- Niente emoji, niente punti esclamativi. Glifi ammessi: ✓ ? – (verdetti), ✦ (AI), ↗ (link esterno), ⏱ (scadenza), → (cambiamento).
- Le incertezze si dicono: "Rolling selection may close earlier — treat 6 days as optimistic."

## Colore

La pagina è per il ~90% neutra calda. Il colore significa sempre qualcosa.

| Ruolo | Token | Uso |
|---|---|---|
| Fondo | `canvas` → `surface` → `surface-sunk` | Pagina, card, pozzetti interni (citazioni, corsie del tracker). |
| Testo | `ink`, `ink-muted` | `ink` per contenuto, `ink-muted` per metadati e fonti. `ink-faint` solo per disabilitato. |
| Azione | `brand` + `on-brand` | Un solo bottone primario per vista, etichetta scura (mai bianco su mandarino). `brand-ink` per link e ".ai". |
| Evidenza | `highlight` | Solo dentro citazioni (`aa-hl`) e nel logo. |
| Voce AI | `ai`, `ai-soft`, `ai-line` | Etichette "Why", blocchi di spiegazione, *How we know*, anello di focus. |
| Verdetti | `go` / `clarify` / `skip` (+ `-soft`, `-fill`) | Apply / Answer first / Not for now. Sempre con glifo e parola. |

- `skip` è grigio ardesia, **non rosso**: "non ora" non è un errore. Non esiste un rosso nel sistema.
- Tutte le coppie di testo sono ≥ 4.5:1 in chiaro e scuro; i riempimenti delle barre (`*-fill`) e i bordi dei controlli (`line-control`) ≥ 3:1 sulle superfici.
- Il tema scuro rispecchia gli stessi ruoli; sul mandarino il testo resta scuro (`on-brand`).

## Tipografia

- **Bricolage Grotesque** (`display`, `title`, `heading`, `numeral`): titoli, nomi delle opportunità, numeri grandi. Un tocco di personalità, mai per paragrafi.
- **Figtree** (`lead`, `body`, `body-strong`, `small`, `label`): tutto ciò che si legge e si tocca. Numeri tabulari sempre attivi.
- **JetBrains Mono** (`mono`): solo nelle righe di fonte e nel livello *How we know*.
- Gerarchia di una schermata: `label` (data/contesto) → `title` → `lead` → sezioni in `heading`.

## Spazio, forma, profondità

- Scala a 4px: `space-4` tra elementi di una card, `space-5` padding card e tra card, `space-6` tra sezioni.
- Raggi: `radius-lg` (20) card e dialoghi, `radius-md` (12) bottoni/input/citazioni, `radius-pill` chip e barre. Forme morbide = tono amichevole.
- Ombre: `shadow-card` a riposo, `shadow-pop` per dialoghi e per la card appena ricalcolata. Nessun'altra.
- Focus: 2px solido `focus` con 2px di offset, su ogni elemento interattivo.

## Movimento

- Transizioni 150ms ease su hover; ingresso del ricalcolo `aa-pop` 600ms. Tutto disattivato con `prefers-reduced-motion`.
- Il movimento serve solo a mostrare un cambiamento causato dall'utente (risposta → nuovo verdetto). Niente animazioni decorative.

## Iconografia e immagini

- Nessuna illustrazione, nessuna foto, nessun logo reale di aziende: le aziende sono **monogrammi** (`aa-mono-logo`) su `surface-sunk`, tinti col verdetto solo nella top 3.
- Glifi tipografici invece di un set di icone (vedi Voce). Se servono icone in Streamlit, usare Material Symbols Rounded (`:material/...:`), tratto regolare, mai colorate se non con un token di verdetto.

## Logo

- `assets/Logos/applicable-mark.svg`: tessera mandarino con spunta `ink` su un tratto di evidenziatore. Favicon, avatar, sidebar compatta.
- `applicable-lockup.svg` su fondi chiari, `applicable-lockup-on-dark.svg` su fondi scuri. Altezza minima 24px; spazio libero = metà dell'altezza della tessera.
- Non ricolorare la tessera, non separare la spunta dall'evidenziatore, non usare il logo come decorazione.

## Componenti

| Gruppo | Componenti |
|---|---|
| Decision | `VerdictChip`, `OpportunityCard`, `PriorityMeter` |
| Evidence | `EvidenceQuote`, `RequirementRow`, `HowWeKnow` |
| Clarify | `QuestionCard`, `RecomputeDelta` |
| Track / Decide | `TrackerBoard`, `CompareTable` |
| Actions | `Button` |
| Screens | `ScreenYourWeek`, `ScreenOpportunity`, `ScreenExplore`, `ScreenProfile`, `ScreenOnboarding` |

Tutti i componenti sono HTML + CSS puro (`components/bundle.css`, prefisso `aa-`), pensati per Streamlit: si rendono con `st.html()`; ogni clic che deve arrivare a Python usa i widget nativi, restyled dal tema. Dettagli nella sezione *Streamlit*.

**Per chi implementa (Claude Code):** parti dalla sezione *Build spec per Claude Code* — ordine di lettura, struttura del progetto, contratti dati, funzioni di render e checklist di accettazione.
