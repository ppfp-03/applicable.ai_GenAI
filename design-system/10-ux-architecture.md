# Architettura UX

## Il cambio di prospettiva

Il prototipo era organizzato per **funzioni** (profilo, preferenze, dashboard, chiarimenti, spiegazione del ranking come pagine separate). Il redesign è organizzato per **la domanda dell'utente in quel momento**:

| Domanda dell'utente | Dove risponde | Cosa cambia rispetto al prototipo |
|---|---|---|
| "Su cosa lavoro questa settimana?" | **Your week** (home) | Non più una dashboard con 4 KPI e 4 pannelli: una colonna, ≤ 3 decisioni + 1 domanda, nessun rail. |
| "Cosa c'è là fuori?" | **Explore** | Nuova: il sistema raccoglie le offerte, serve un posto per sfogliarle e filtrarle per verdetto. |
| "Perché questa? Ce la faccio?" | **Opportunity** (tab Overview / Requirements / How we know) | Dettaglio + spiegazione del ranking fusi in un'unica pagina a schede. |
| "Meglio A o B?" | **Compare** | Nuova: confronto affiancato su requisiti, gap, scadenza, sforzo. |
| "A che punto sono?" | **Tracker** | Nuova: corsie Shortlisted → Preparing → Sent → Outcome, con budget ore. |
| "Cosa sa di me l'AI?" | **My profile** | Profilo estratto + preferenze + fatti dichiarati in un'unica pagina, con fonti. |

Le **domande di chiarimento** non sono più una pagina: vivono dove servono (card inline nella home, riga "Answer now" nei requisiti) e si aprono in un dialog. Il badge nella sidebar conta quelle aperte.

## Navigazione (sidebar `st.navigation`)

```
Applicable.ai
├─ Your week        ← home, badge = domande aperte
├─ Explore          ← tutte le offerte raccolte, filtri per verdetto/paese/scadenza
├─ Tracker          ← pipeline candidature + budget settimanale
├─ Compare          ← 2–3 opportunità affiancate
├─ My profile       ← CV estratto · preferenze · fatti dichiarati · versioni CV
└─ Settings         ← privacy, AI settings, account (in fondo, secondario)

Opportunity/<id>    ← pagina di dettaglio, raggiunta da card, Explore, Tracker, Compare
Onboarding          ← flusso lineare, solo al primo accesso
```

## User journey

1. **Onboarding (≈ 4 min, 3 passi).** Carica il CV → "This is what we understood" (conferma solo i 2–3 dati incerti) → **Essentials**: paesi, tipi di ruolo, disponibilità, ore a settimana. Tutto il resto (visti, lingue, patente…) *non* si chiede qui: diventa una domanda solo quando un'offerta reale ne ha bisogno.
2. **Primo "aha" — Your week.** Il sistema ha già raccolto e valutato le offerte: 3 da candidare questa settimana, 1 domanda, il resto spiegato.
3. **Capire — Opportunity › Requirements.** Requisito per requisito: *They ask* ↔ *You have* con le parole evidenziate. ← **momento demo #1**
4. **Chiarire.** Una domanda (es. "What's your German level?") → risposta → il verdetto passa da *Answer first* ad *Apply*, rank #3 → #2, e sblocca anche un'altra offerta. ← **momento demo #2**
5. **Decidere.** "Add to my week" (o Compare se indeciso) → la card entra nel Tracker con il primo passo concreto ("tailor bullet 3", ~1.5 h).
6. **Tornare.** Ogni lunedì *Your week* si rigenera; *What changed* spiega cosa si è mosso e perché.

## Regole trasversali

- Ogni numero ha accanto un verdetto e porta alla sua scomposizione.
- Ogni fatto porta alla sua fonte (`CV`, `JOB`, `YOU`).
- Ogni verdetto porta al requisito che lo produce.
- Ogni domanda dichiara quante decisioni sblocca prima di essere posta.
- Nessun auto-apply, nessun confronto con altri candidati, nessuna probabilità di offerta.

## Cosa cambia rispetto agli HTML originali

**Eliminato / ridotto**

- L'anello del punteggio come elemento dominante → sostituito da verdetto + barra dei requisiti; il numero diventa secondario.
- 4 KPI in testa alla dashboard, pannello pesi ripetuto in 4 schermate, "This week's plan" statico → un'unica frase-budget e il Tracker.
- Pagina *Clarifications* separata e pagina *Ranking explanation* separata → dialog contestuale e tab dell'Opportunity.
- Dettagli tecnici (temperature, sha256, "GPT-class LLM") nelle schermate principali → solo in *How we know* e Settings.
- 6 blocchi di preferenze nell'onboarding → 4 essenziali; il resto chiesto "just in time".
- Magenta per i conflitti → ardesia: nessun rosso nel prodotto.

**Aggiunto**

- *Explore* (le offerte arrivano dal sistema), *Compare*, *Tracker* con budget ore.
- Evidenziatore come linguaggio unico delle prove, logo compreso.
- Stati vuoti e di errore (vedi *Screens*).
- Tema scuro reale, non solo descritto.

**Corretto nei dati demo**

- L'esempio svizzero ("la cittadinanza UE non basta") era sbagliato. Ora il permesso svizzero è un **controllo a regole** (tabella sotto) e la domanda demo diventa la **lingua** (German B2), un fatto che il CV davvero non dice.
- Aziende reali sostituite con nomi fittizi somiglianti (Lazarde & Co., Bolton Consulting Group, Nestella, J.P. Morrow…): riconoscibili in demo, senza attribuire dati inventati a datori di lavoro veri.
- Date allineate a oggi (22 Sep 2026) e al semestre a Fudan (Sep 2026 – Feb 2027).

## Regole di eleggibilità (deterministiche, fonte `RULE`)

L'autorizzazione al lavoro non è mai giudicata dal modello: è una tabella di regole applicata a cittadinanza dichiarata, paese e durata del contratto. Il modello si limita a spiegarla.

**Svizzera — cittadini UE/AELS**

| Durata del contratto | Esito | Come appare |
|---|---|---|
| ≤ 3 mesi (studente UE) | Nessun permesso | ✓ Met · "No permit needed for ≤ 3 months" |
| > 3 e < 12 mesi | Permesso di breve durata L UE/AELS, per la durata del contratto | ✓ Met · "L permit (EU/EFTA) for the contract length" |
| ≥ 12 mesi o tempo indeterminato | Permesso B UE/AELS, valido 5 anni | ✓ Met · "B permit (EU/EFTA), valid 5 years" |

- Esempio demo: *Nestella · Graduate Programme, Zurich, 18 mesi* → Giulia (cittadina italiana) → **B permit (EU/EFTA), 5 anni** → requisito soddisfatto, nessuna domanda.
- Se la durata del contratto non è scritta nell'offerta, il requisito diventa *To confirm* e il sistema non sceglie una fascia.
- Le regole vanno versionate (data di validità) e mostrate in *How we know*; non sono consulenza legale.
