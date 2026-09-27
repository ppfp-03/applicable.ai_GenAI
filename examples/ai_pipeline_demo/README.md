# AI pipeline demo

A standalone technical demonstration of the intelligence layer, separate from the Streamlit app. It takes one synthetic CV (`synthetic_cv.txt`) and the prepared Batch 01 JobSnapshot, then prints:

1. the CandidateProfile extracted from the CV, with every fact linked to a verbatim CV quote;
2. the JobFacts for each job, including hard constraints and the posting text behind them;
3. the eligibility result for each job.

Extraction and evidence are the demonstration. Ranking is left out by default (see [Ranking diagnostic](#ranking-diagnostic)).

Each step calls the existing modules (`extract_candidate`, `oi.runtime.jobs.load_jobs`, `assess_eligibility`, and with `--include-ranking`, `rank_with_eligibility`). The demo adds no AI logic of its own.

## Run

From the repository root:

```bash
# Default: CV cache + job cache. No model call, no API key, same output on every run.
PYTHONPATH=src python -m examples.ai_pipeline_demo.run_demo

# Live CV extraction against Kimi (needs KIMI_API_KEY in .env), jobs from cache
PYTHONPATH=src python -m examples.ai_pipeline_demo.run_demo --cv-mode live

# Offline plumbing check with a handcrafted model reply
PYTHONPATH=src python -m examples.ai_pipeline_demo.run_demo --cv-mode fixture

# Write the full machine-readable report as well
PYTHONPATH=src python -m examples.ai_pipeline_demo.run_demo --json report.json

# Add the ranking, labeled as a development diagnostic
PYTHONPATH=src python -m examples.ai_pipeline_demo.run_demo --include-ranking
```

Other options: `--cv PATH` (a `.pdf` or a text file), `--job-mode snapshot|cache|live`, `--now ISO8601` (the ranking clock, so only with `--include-ranking`).

## Modes

The CV mode and the job mode are chosen separately, and both are printed at the top of the report. A mode never falls back to another one.

In `cache` mode the report shows both the mode of this run and how the cached result was originally produced, for example:

```
  CV provenance    current mode CACHE, cached result originally produced LIVE
                   provider/model kimi / moonshotai/kimi-k3 | prompt sha256:... | produced 2026-09-26T15:32:37.892867Z
```

No model is called in this run. The committed caches were recorded by an earlier live run, and their receipts are shown unchanged.

| Mode | CV | Jobs |
|---|---|---|
| `live` | Kimi reads the CV during this run | Kimi enriches all 8 postings during this run (slow) |
| `cache` | `cv_cache.json`, served only if its receipt matches the CV hash, provider/model, prompt version and schema version | `data/snapshots/greenhouse_batch01_enriched.json`, checked the same way |
| `fixture` | `cv_fixture_reply.json`, a handcrafted reply passed through the real extraction code and labeled `fixture`. It is not evidence of model quality | not offered |
| `snapshot` | not offered | Jobs as ingested, with no facts |

If the cache no longer matches (for example because the CV or the candidate prompt changed), the run stops with `StaleCacheError`. To re-record the cache:

```bash
PYTHONPATH=src python -m examples.ai_pipeline_demo.run_demo --cv-mode live --record-cv-cache
```

`tests/test_ai_pipeline_demo.py` fails whenever the committed cache is stale, so this is caught before the demo.

## Ranking diagnostic

`--include-ranking` adds section `[4]`, labeled `DEVELOPMENT DIAGNOSTIC`. Its scores are not a product result, so it should not be presented as the demo's job ranking:

- the weights (`config/ranking.json`, version `development-0.1`) and the 30-day deadline and freshness horizons are development values, not approved ones;
- with the synthetic CV and Batch 01, only `freshness` has a value. `profile_fit`, `preference_fit` and `deadline_urgency` are missing for every job, so each score is the freshness value alone.

The section prints the weights version and weights, the horizons, the clock, the active and missing factors, and, per job, each factor value and the effective weights actually applied. Missing factors are reported as missing, never filled in.
