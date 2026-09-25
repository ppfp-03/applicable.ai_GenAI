# Opportunity Intelligence - Team Member Starter Guides

**Role of this file:** official current coordinating and working plan
for every member.

This file owns operational ownership: roles, tasks, priorities,
deliverables, deadlines, dependencies, handoffs and quality criteria.
Product truth remains in `PROJECT_CONTEXT.md`; completed evidence
remains in `SESSION_LOGS.md`.

**Project deadline:** 29 September 2026.

------------------------------------------------------------------------

# Repository implementation ownership

Direct repository implementation is owned by five feature owners.

All coding work follows a feature-branch + pull-request workflow. Each
feature has one owner and one controlled integration path.

## Marco - AI Runtime & Intelligence Integration

**Branch:** `feature/ai-runtime-marco`

**Mission:** Implement the AI layer connecting candidate/job documents
to structured intelligence outputs.

**Owns:** - provider abstraction; - LLM runtime integration; - candidate
extraction; - job requirement extraction; - evidence-backed outputs; -
extraction provenance; - prompt versioning; - runtime decision support.

**Deliverables:** - AI extraction pipeline; - provider-neutral model
client; - extraction tests; - documented runtime configuration.

**Does not own:** - eligibility rules; - ranking; - UI; - contract
changes without approval.

------------------------------------------------------------------------

## Pierpaolo - UI Production Integration

**Branch:** `feature/ui-production-pierpaolo`

**Mission:** Convert the approved design system into the production
Streamlit experience using canonical contracts.

**Owns:** - onboarding; - profile screens; - opportunities list; -
opportunity details; - clarification screens; - loading/error states; -
UI integration.

**Does not own:** - separate business logic; - duplicate ranking; -
duplicate eligibility engine.

------------------------------------------------------------------------

## Giorgio G - Eligibility Engine

**Branch:** `feature/eligibility-engine-giorgio-g`

**Mission:** Implement deterministic eligibility evaluation.

**Owns:** - RuleCatalogue; - hard-constraint evaluation; - MET /
CONFLICT / UNKNOWN / NOT_APPLICABLE handling; - eligibility tests.

**Principle:** LLM outputs may provide structured information, but
deterministic rules decide eligibility.

------------------------------------------------------------------------

## Giorgio M - Ranking Engine

**Branch:** `feature/ranking-engine-giorgio-m`

**Mission:** Implement opportunity prioritization.

**Frozen MVP ranking configuration:**

-   Profile fit: 40%
-   Preference fit: 25%
-   Deadline urgency: 20%
-   Freshness: 15%

Missing factors are renormalized among available factors.

**Owns:** - ranking engine; - embedding boundary; - scoring
configuration; - ranking tests.

**Does not own:** - eligibility decisions.

------------------------------------------------------------------------

## Tommaso - Clarification Engine & Acceptance

**Branch:** `feature/clarification-engine-tommaso`

**Mission:** Implement the missing-information loop.

Flow:

`Unknown fact → ClarificationRequest → Structured answer → Profile update → Recompute`

**Owns:** - clarification logic; - structured answers; - profile
updates; - recomputation tests.

After integration: - execute acceptance tests from
`A-TESTS-01_r02.xlsx`.

------------------------------------------------------------------------

# Feature branch workflow

Every coding task follows:

1.  Create a dedicated feature branch.
2.  Modify only the assigned feature scope.
3.  Run verification.
4.  Open a pull request.
5.  Review before merge.

Example:

``` bash
git checkout main
git pull
git checkout -b feature/task-name
```

If a feature depends on unfinished work, branch from the dependency
branch and document the dependency.

Each PR handoff must include:

-   branch name;
-   base commit;
-   changed files;
-   verification commands;
-   unresolved issues.

------------------------------------------------------------------------

# Integration order

1.  AI Runtime (`feature/ai-runtime-marco`)
2.  Eligibility (`feature/eligibility-engine-giorgio-g`)
3.  Ranking (`feature/ranking-engine-giorgio-m`)
4.  Clarification (`feature/clarification-engine-tommaso`)
5.  UI integration (`feature/ui-production-pierpaolo`)

The UI consumes stabilized outputs and should not define business logic.

------------------------------------------------------------------------

# Team members not on the coding critical path

## Nils

Evaluation methodology, frozen inputs and metrics.

## Anastasia

Independent evaluation rating and evidence review.

## Madda

Independent evaluation rating and presentation visuals.

------------------------------------------------------------------------

# Team gates

-   24 Sep: feature freeze and coding redistribution.
-   27 Sep: report/walkthrough/presentation draft.
-   28 Sep: fixes, evidence checks and rehearsal.
-   29 Sep: submission and presentation.
