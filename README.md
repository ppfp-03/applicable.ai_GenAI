# Applicable.ai

Applicable.ai is an AI-powered application prioritization assistant for students
and recent graduates. The planned product will help users understand
and prioritise career opportunities.

## Current status

This repository contains only the initial application foundation: a Streamlit
shell with Candidate Profile and Top Opportunities placeholders, empty Python
modules, provisional configuration, and prompt placeholders.

No AI pipeline, LLM calls, eligibility checks, ranking logic, or generated AI
outputs are implemented. There is no database, authentication, Docker setup,
vector database, or ATS integration.

## Setup

Run these commands from the existing repository directory with Python 3.10+
installed.

Create and activate a virtual environment on macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the initial dependencies:

```bash
python -m pip install -r requirements.txt
```

Optionally copy the environment template for future development:

```bash
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env`.
The template contains only `GEMINI_API_KEY=`. No API key is needed to run this
foundation, and the application does not load or use it yet. Keep real secrets
out of version control; `.env` files are ignored.

## Run the application

```bash
python -m streamlit run app.py
```

## Tests

```bash
python -m pytest
```

The `tests/` package is a placeholder with no tests yet. Pytest will report no
tests collected and return exit code 5 until tests are added.

## Structure

- `app.py`: Streamlit application shell.
- `config/`: development-only hard constraint and ranking factor definitions.
- `data/synthetic/`: reserved for future synthetic data; currently empty.
- `prompts/`: candidate and job extraction prompt placeholders.
- `src/oi/contracts.py`: reserved for shared data contracts.
- `src/oi/io/`: reserved for document input utilities.
- `src/oi/providers/`: reserved for provider integration.
- `src/oi/intelligence/`: reserved for future intelligence modules.
- `src/oi/ui/`: reserved for reusable interface components.
- `tests/`: reserved for future tests.

All configuration entries are marked `development/provisional`. Hard constraint
values remain `null`; the four ranking factors each have a provisional weight
of `0.25`. No eligibility rules or ranking algorithms consume this configuration yet.

## Team

**Pasta, Pretzel & Prompts**

Marco, Pierpaolo, Giorgio M., Giorgio G., Tommaso, Nils, Anastasia, and Madda.
