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

### System dependencies for OCR

Scanned, image-based PDFs are read with OCR. That path needs two programs
installed on the system itself, alongside the Python packages above:

- **Tesseract** — the OCR engine.
- **Poppler** — provides `pdftoppm`, used to render PDF pages as images.

On macOS with Homebrew:

```bash
brew install tesseract poppler
```

On Debian or Ubuntu:

```bash
sudo apt-get install tesseract-ocr poppler-utils
```

On Windows, install the
[Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki) and the
[Poppler binaries](https://github.com/oschwartz10612/poppler-windows/releases),
then add both `bin` directories to `PATH`.

Text-based PDFs work without these; only the OCR fallback requires them.
Verify an installation with `tesseract --version` and `pdftoppm -v`.

Optionally copy the environment template for future development:

```bash
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env`.
The template contains `KIMI_API_KEY=` and `KIMI_MODEL=`. Candidate extraction
calls the Kimi API and requires a valid `KIMI_API_KEY`; the rest of the
application (PDF and OCR ingestion) runs without one. Keep real secrets out of
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

The `tests/` package is a placeholder with no tests yet. Pytest will report no
tests collected and return exit code 5 until tests are added.

## Structure

- `app.py`: Streamlit application shell.
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
- `tests/`: reserved for future tests.

Both configuration files use version `development-0.1` and contain provisional
development values. The three hard constraints are marked `development` and
define no rules yet. The four ranking factors each have a provisional weight
of `0.25`. No eligibility rules or ranking algorithms consume this configuration yet.

## Team

**Pasta, Pretzel & Prompts**

Marco, Pierpaolo, Giorgio M., Giorgio G., Tommaso, Nils, Anastasia, and Madda.
