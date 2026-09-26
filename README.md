# Applicable.ai

Applicable.ai is an AI-powered application prioritization assistant for students
and recent graduates. The planned product will help users understand
and prioritise career opportunities.

## Current status

The Streamlit app reproduces the approved mockups (`00_Onboarding` to
`05_Ranking`) in the product's orange palette, running end to end on the
synthetic demo data in `data/demo.json` (persona: Giulia Rossi, fictional
companies only). No real LLM is called yet.

- **Home**: this week's carousel, a two-week timeline, top matches and the
  applications wallet.
- **Matches**: the top five, each score broken down into four factors with
  fixed weights (40/25/20/15).
- **Role**: eligibility against eight fixed criteria: permission to work by
  the canonical `HC_WORK_AUTH` rule (`core/eligibility.py`), the other seven
  by `core/rules.py`.
- **One quick question**: the UK work question. Saving the answer recomputes
  eligibility and ranking everywhere.
- **Profile**: review and correct what was read from the CV.
- **Onboarding**: seven steps, from uploading the CV to the updated ranking.
- **Applications** and **Explore**: no mockup; built in the same visual
  language.

## Setup

Run these commands from the existing repository directory with Python 3.10+
installed.

Create and activate a virtual environment on macOS or Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

Install the initial dependencies:

```bash
pip install -r requirements.txt
```

### PDF input

Only text-bearing PDFs are supported: the CV's text is read with `pypdf`, and
no system programs are needed. OCR is out of MVP scope, so a scanned or
image-only PDF is rejected with a clear "no usable text" error instead of
being read.

Optionally copy the environment template for future development:

```bash
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env`.
The template contains `KIMI_API_KEY=` and `KIMI_MODEL=`. Candidate extraction
calls the Kimi API and requires a valid `KIMI_API_KEY`; the rest of the
application (including PDF text extraction) runs without one. Keep real secrets out of
version control; `.env` files are ignored.

## Run the application

With Node.js and npm installed, start the development server from the repository:

```bash
npm run dev
```

The launcher uses `.venv`, or `venv` if `.venv` is absent, on macOS, Linux,
and Windows. Complete the Python setup above first; activating the environment
is not required for this command. No npm dependencies or `npm install` are needed.
Open `http://localhost:8501` and stop the server with `Ctrl+C`.

Pass optional Streamlit flags after `--`, for example:

```bash
npm run dev -- --server.port 8502
```

Alternatively, with your Python environment activated:

```bash
streamlit run app.py
```

## Tests

```bash
pytest
```

The tests cover the deterministic rules (the eight criteria, the Swiss
permit table) and the ranking arithmetic. The expected orders are the ones
the mockups show.

## Structure

- `app.py`: Streamlit entry point, with hidden navigation. The capsule in the
  top bar is the navigation.
- `views/`: one file per screen.
- `core/rules.py`: eligibility, decided only by deterministic rules.
  `core/ranking.py` holds the priority score, and `core/store.py` the demo
  data, session state and everything derived from them.
- `ui/css/`: mockup CSS, one file per screen. `ui/palette.py` maps the
  mockups' blues to the orange scale at publish time, and `ui/theme.py`
  publishes the stylesheets to `static/`.
- `ui/html.py`, `ui/shell.py`, `ui/parts.py`: markup that only displays (icons,
  top bar, score bars). Every action is a native Streamlit widget, often an
  invisible button placed over the mockup element.
- `package.json` and `scripts/dev.cjs`: npm development launcher for Streamlit.
- `config/`: development-only hard constraint and ranking factor definitions.
- `data/synthetic/`: reserved for future synthetic data; currently empty.
- `prompts/`: candidate and job extraction prompt placeholders.
- `src/oi/contracts.py`: reserved for shared data contracts.
- `src/oi/io/`: reserved for document input utilities.
- `src/oi/providers/`: LLM provider integration — `model_client.py` defines the
  generic interface, `kimi.py` implements it for the Kimi API.
- `src/oi/intelligence/`: reserved for future intelligence modules.
- `src/oi/ui/`: reserved for reusable interface components.
- `tests/`: rules and ranking tests.

Both configuration files use version `development-0.1` and contain provisional
development values. The three hard constraints are marked `development` and
define no rules yet. The four ranking factors each have a provisional weight
of `0.25`. No eligibility rules or ranking algorithms consume this configuration yet.

## Team

**Pasta, Pretzel & Prompts**

Marco, Pierpaolo, Giorgio M., Giorgio G., Tommaso, Nils, Anastasia, and Madda.
