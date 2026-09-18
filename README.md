[README.md](https://github.com/user-attachments/files/32371177/README.md)
# applicable.ai_GenAI

## AI-powered assistant for prioritising job applications

Opportunity Intelligence helps university students and recent graduates
decide which job opportunities deserve their application time first.

The system combines: - explicit eligibility checks; - candidate-job fit
analysis; - user preferences; - posting freshness; - evidence-backed
explanations.

## Problem

Students and recent graduates often face many possible internships and
graduate roles across different platforms. The challenge is deciding:

> Which applications should I complete first?

## Solution

Opportunity Intelligence is a hybrid AI assistant.

### Generative AI is used for:

-   CV and job description understanding;
-   structured information extraction;
-   skill and requirement analysis;
-   clarification question generation;
-   evidence-linked explanations.

### Deterministic logic is used for:

-   hard eligibility rules;
-   uncertainty handling;
-   ranking calculations;
-   transparent decisions.

## Key Features

### CV Understanding

Extracts: - education; - skills; - experience; - candidate information.

### Job Analysis

Extracts: - role information; - requirements; - locations; - evidence
from postings.

### Eligibility Checking

Classifies opportunities as: - Eligible; - Ineligible; - Uncertain.

### Clarification Loop

When information is missing, the system asks targeted questions and
updates the candidate profile.

### Transparent Ranking

Prioritises opportunities using: - profile fit; - preference fit; -
deadline urgency; - freshness.

## Technology Stack

  Component    Technology
  ------------ ----------------------
  Language     Python
  Interface    Streamlit
  AI           OpenAI API
  Similarity   Sentence embeddings
  Data         JSON/JSONL snapshots
  Testing      Pytest

## Running the Project

``` bash
git clone <repository-url>
cd Opportunity-Intelligence

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

streamlit run app.py
```

## Project Structure

    Opportunity-Intelligence/
    ├── app.py
    ├── src/
    ├── data/
    ├── tests/
    ├── prompts/
    ├── requirements.txt
    └── README.md

## Evaluation

The system is evaluated against: 1. Hybrid Opportunity Intelligence
system 2. Embedding-only baseline 3. Generic LLM baseline

Metrics include: - ranking agreement; - explicit constraint
violations; - evidence support; - duplicate handling; - clarification
quality.

## Demo Flow

1.  Upload synthetic CV
2.  Extract profile
3.  Review preferences
4.  Analyse opportunities
5.  Answer clarification questions
6.  Recalculate ranking
7.  Display prioritised applications

## Privacy & Safety

The project uses: - synthetic candidate data; - explicit declarations
only; - evidence-based decisions; - protected API keys.

## Team

**Pasta, Pretzel & Prompts**

Members: - Marco - Pierpaolo - Giorgio M. - Giorgio G. - Tommaso -
Nils - Anastasia - Madda

## Status

🚧 MVP under development

## AI Usage Disclosure

AI tools assisted with documentation drafting and writing refinement.
Final technical decisions and implementation remain the responsibility
of the team.
