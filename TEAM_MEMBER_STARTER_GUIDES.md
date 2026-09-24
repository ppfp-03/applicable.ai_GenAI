# Opportunity Intelligence - Team Member Starter Guides

**Role of this file:** official current coordinating and working plan
for every member.

This file owns the operational layer only: roles, assigned tasks,
current priorities, deliverables, expected format, deadlines, quality
criteria, dependencies, blockers and handoff recipients.
Product/technical truth lives in the repository-root
`PROJECT_CONTEXT.md`, which governs if the two files conflict;
completed-work evidence lives in `SESSION_LOGS.md`; assistant behavior lives in the
Project Operating Instructions.

**Project deadline:** 29 September 2026.

## How to use this file

When a member identifies themselves or asks for support, use their
current section below. Do not infer progress from the plan: a task
remains planned until repository evidence or `SESSION_LOGS.md` shows
otherwise.

Task ordering is not implementation status. Before identifying the next
action for a repository task: - check the latest repository state; -
verify merged branches, commits and pull requests when available; - use
`SESSION_LOGS.md` as historical evidence, not as a replacement for
current repository state.

A completed repository change supersedes an outdated task sequence. Do
not recommend restarting an earlier task package when repository
evidence shows that it has already been completed.

The support response should state, from this file:

1.  role, assigned tasks and current priority;
2.  required deliverables, format, deadline and quality criteria;
3.  dependencies, blocked work and people whose input is still needed;
4.  next three concrete actions.

If a task, date or dependency changes, update it here rather than
duplicating the change in `PROJECT_CONTEXT.md`.

## Repository implementation ownership

Direct repository implementation is owned by the two coding leads:

-   **Marco**: Group A coding lead for shared contracts, data/input
    integration, ingestion, normalization, snapshots and related
    repository integration.
-   **Pierpaolo**: Group B coding lead for runtime AI,
    intelligence/eligibility/ranking implementation, UI and related
    repository integration.

Other members own research, evaluation, taxonomy, testing, evidence,
reporting or presentation work as specified in their sections below.
They should not modify repository code unless Marco or Pierpaolo
explicitly delegates a bounded coding task or the team updates the
assignment here.

Git/branch mechanics, coding-agent safety rules and repository editing
workflow belong in `AGENTS.md`, not in this team coordination document.

## Quick assignment matrix

  ---------------------------------------------------------------------------
  Member            What to do first     First output       Target
  ----------------- -------------------- ------------------ -----------------
  Marco             A-05 UI data access  UI data access     24 Sep
                    boundary             helper + tests

  Giorgio M         Test                 Verified           19 Sep
                    Greenhouse/company   source/coverage
                    coverage             recommendation

  Tommaso           Execute frozen       21-case design     22-24 Sep
                    `A-TESTS-01_r02`     pack complete;
                    against an           execution evidence
                    identified build     next

  Pierpaolo         UI/design            UI on real         24 Sep
                    integration +        `JobRecord` data
                    intelligence         (pre-intelligence
                    pipeline using A     state)
                    boundaries

  Giorgio G         Define               Constraint         19 Sep
                    hard-constraint      catalogue + 3
                    taxonomy + personas  synthetic personas

  Nils              Freeze held-out      B-04 methodology   23-26 Sep
                    inputs and run the   pack complete;
                    evaluation once      execution pending
                    dependencies arrive

  Anastasia         Independently rate   Independent        from 22 Sep
                    frozen evaluation    rating/evidence
                    set                  sheet

  Madda             Independently rate,  Independent rating from 22 Sep
                    then build pitch     sheet +
                    visuals              pitch/visual
                                         proposal
  ---------------------------------------------------------------------------

Each member section below is the current operational brief for that
member.

------------------------------------------------------------------------

# Marco - Group A: Data & Integration

## Your mission

Build the reliable **input/data side** of the system so Pierpaolo can
develop the intelligence and UI against stable contracts instead of
waiting for the final dataset.

## Completed work

-   J-01 shared contracts.
-   A-01 input/snapshot path.
-   A-03 Greenhouse Batch 01 snapshot.
-   A-04 demo snapshot provider boundary.

## Current priority: A-05 UI Data Access Boundary

**Objective:** provide a thin UI-facing access layer over the existing
`JobSnapshot` boundary so Pierpaolo can build UI components using real
`JobRecord` data before intelligence enrichment is available.

**Scope:**

-   consume `get_demo_snapshot() -> JobSnapshot`;
-   expose existing `JobRecord` data to UI components;
-   preserve existing contracts.

**Do not:**

-   create duplicated UI data formats;
-   add ranking fields;
-   add eligibility fields;
-   add mock intelligence data;
-   modify `JobSnapshot` or `JobRecord` contracts.

**Dependency:** Pierpaolo uses this boundary for UI development.

## Historical completed work - original J-01/A-01 steps

Kept for reference only; these steps are complete. Current work is
A-05 above.

1.  **Open the actual repository/environment** and record the Python
    version and operating system used.
2.  **Review the shared contract with Pierpaolo.** Freeze the minimum
    serializable objects needed for independent work, especially
    `SourceDocument`, `JobRecord`, `CandidateProfile`,
    `ClarificationRequest`, `RankingResponse`, rule/config versions and
    evidence references.
3.  **Create the repository/application skeleton** with clean modules
    for contracts, job I/O, PDF text extraction, configuration and
    tests. Do not take UI ownership.
4.  **Create tiny shared fixtures immediately**: a few fake normalized
    jobs, one synthetic CV text input and example B outputs. These let A
    and B develop in parallel.
5.  **Implement the A-owned input boundaries**: snapshot loader,
    normalized job input shape and text-based PDF extraction.
6.  **Support Giorgio M's source work** by turning the accepted
    Greenhouse/company list into the first raw-to-normalized snapshot
    and manifest.
7.  **Run setup and contract tests for real**. Record exact commands and
    observed results; do not mark unexecuted checks as passed.

## Deliverables

-   `A-05`: a small UI data access helper over
    `get_demo_snapshot() -> JobSnapshot` that exposes existing
    `JobRecord` data to UI components, plus tests. Pierpaolo can consume
    it without schema patching or duplicate snapshot loading.

## Done when

-   Pierpaolo can consume your fixture/job/CV inputs without inventing
    fields.
-   The project starts using documented commands on the development
    machine.
-   PDF-to-text and snapshot loading have clear error behavior.
-   No UI or ranking logic has leaked into Group A modules.

## Do not do

-   Do not build a second ranking engine.
-   Do not add Ashby/Lever before Giorgio M's coverage evidence
    justifies it.
-   Do not introduce SQLite or extra infrastructure without a concrete
    need.

## Handoff to

**Pierpaolo** for B integration; **Tommaso** for startup/input
acceptance checks.

------------------------------------------------------------------------

# Giorgio M - Group A: Source Coverage & Data Quality

## Your mission

Determine whether **Greenhouse alone can provide a useful MVP job
universe** for the agreed candidate segment, role domain and
geographies. Your work decides whether a second ATS is worth the time.

## Start now

**Task:** A-02 source/market coverage test.\
**Deadline:** first recommendation by 19 September; final source
recommendation by 20 September.

## Step by step

1.  Use the agreed target:
    -   students/recent graduates;
    -   internships and entry-level jobs;
    -   Business, Finance, Economics, Management and related
        commercial/managerial/financial roles;
    -   target geographies listed in the project context.
2.  Identify a **small set of companies with public Greenhouse boards**
    that plausibly contain relevant jobs. Do not try to cover every
    geography evenly.
3.  Verify the public source. For each company, record the
    URL/reference, when you checked it and what you actually observed.
4.  Count or sample **relevant postings**, not total postings. A
    software-engineering-heavy board with 200 jobs may still be useless
    for this MVP.
5.  Inspect data quality on representative postings:
    -   title;
    -   company;
    -   location;
    -   description quality;
    -   source ID/URL;
    -   available timestamps;
    -   deadline if present;
    -   wording relevant to the provisional hard constraints.
6.  Keep publication time, update time and first-seen time separate.
    Never call `updated_at` a publication date unless the source
    explicitly says so.
7.  Conclude one of two things:
    -   **Greenhouse is sufficient for the MVP**, or
    -   **there is a material coverage gap**, with evidence explaining
        why Ashby or Lever should be added.
8.  Send Marco the accepted company/source shortlist and representative
    source examples.

## Deliverable

`A-02-SOURCES-01 r01` with a table containing:

  ----------------------------------------------------------------------------------------------------------------
  Source/company   Verified        Relevant            Useful    Missing/ambiguous        Approx. Recommendation
                   URL/reference   roles/geographies   fields    fields                  relevant
                                   observed                                              postings
  ---------------- --------------- ------------------- --------- ------------------- ------------ ----------------

  ----------------------------------------------------------------------------------------------------------------

End with a short recommendation: **Greenhouse only / add one additional
ATS / not enough evidence yet**.

## Done when

-   The recommendation is based on pages/endpoints you actually checked.
-   Marco can select companies and ingest a useful first snapshot.
-   You have documented important timestamp and missing-data
    limitations.

## Do not do

-   Do not chase a quota by adding irrelevant jobs.
-   Do not claim all target countries are covered if they are not.
-   Do not implement ingestion code unless Marco explicitly asks you to.

## Handoff to

**Marco**, with a copy to **Pierpaolo** if you find recurring job
wording that matters for eligibility extraction.

------------------------------------------------------------------------

# Tommaso - Group A: Acceptance & Integration Testing

## Your mission

Execute the agreed product-behavior tests against a specific application
build without changing the expected outcomes after seeing implementation
behavior.

## Current status - 23 September

`A-TESTS-01_r02.xlsx` is the current pre-execution baseline. It contains
21 planned cases mapped across FR-01 to FR-12. All 21 remain `Not run`;
no application build was executed and no PASS/FAIL evidence exists yet.

## Current priority

**Task:** prepare and execute the first acceptance/integration run as
soon as Marco/Pierpaolo supply the identified build and minimum test
materials.

## Dependencies before execution

-   a specific application version/build/commit and access instructions;
-   the agreed synthetic CV/profile inputs;
-   the agreed job snapshot/job set with stable IDs;
-   controlled scenarios/instructions for special cases such as provider
    failure, clarification and multi-location behavior;
-   developer evidence from Marco/Pierpaolo for checks that are not
    fully observable in the UI, especially privacy/persistence/log
    behavior.

## Next three actions

1.  Get the build/access details and the exact test inputs from
    Marco/Pierpaolo.
2.  Execute the existing case IDs without rewriting `Expected result`,
    starting with T-001 and then the dedicated edge cases.
3.  Record `Observed result`, `Execution status` and concise evidence
    for each executed case; escalate failures with the affected boundary
    without guessing the root cause.

## Step by step

1.  Treat `A-TESTS-01_r02.xlsx` as the frozen expected-behavior baseline
    for the first run.
2.  Identify the exact tested build/commit and record it with the run
    evidence.
3.  Use the agreed synthetic CV/profile inputs and the agreed frozen job
    set rather than ad hoc replacements.
4.  Execute the normal end-to-end path, then the
    unknown/conflict/clarification, freshness, fallback, evidence and
    privacy cases.
5.  For T-021 and any other non-UI-observable check, obtain
    repository/log/privacy evidence from Marco/Pierpaolo instead of
    assuming a pass.
6.  Preserve failures and incomplete checks. Do not rewrite expected
    behavior to fit the implementation.

## Deliverable

**Current design artifact:** `A-TESTS-01_r02.xlsx`.

**Execution deliverable:** the same case set with `Execution status`,
`Observed result` and `Status/evidence` populated against one identified
build. Expected results remain unchanged unless the team separately
approves a product-rule change.

  --------------------------------------------------------------------------------------------
  Case ID  FR/rule   Input/mode   Action   Expected   Execution   Observed   Status/evidence
                                           result     status      result
  -------- --------- ------------ -------- ---------- ----------- ---------- -----------------

  --------------------------------------------------------------------------------------------

## Done when

-   Every core demo behavior has an executed result or an explicit
    blocked/not-run reason.
-   Unknown/conflict/clarification and failure-mode cases have evidence.
-   Results identify the build and inputs used.
-   Executed evidence remains clearly separated from design
    expectations.

## Do not do

-   Do not mark a test passed because the design looks correct.
-   Do not change business rules inside the test sheet to make the
    current implementation pass.
-   Do not infer repository/privacy behavior from the UI when developer
    evidence is required.

## Handoff to

**Marco + Pierpaolo**. Failed integration cases should identify which
boundary appears responsible without guessing at the root cause.

------------------------------------------------------------------------

# Pierpaolo - Group B: Intelligence, Runtime AI & UI

## Your mission

Build the **intelligence and user-facing path**: structured extraction,
profiling, clarification, eligibility, ranking, gaps/explanations and
Streamlit UI, while keeping deterministic decisions separate from LLM
interpretation.

## Current priority

**Current focus:**

-   UI/design implementation;
-   connect UI components to existing A-side data boundaries;
-   continue intelligence pipeline implementation.

**Dependency - Marco provides:**

-   `JobSnapshot` 0.2.1-draft;
-   the `get_demo_snapshot()` boundary;
-   real `JobRecord` inputs.

Do not create duplicate snapshot loading or ingestion logic. Consume
jobs through the A-side boundaries.

**The UI must support the pre-intelligence state:**

-   `JobRecord` available;
-   `JobFacts` unavailable;
-   eligibility unavailable;
-   ranking unavailable.

## Historical plan - original B implementation steps

Kept for reference only. This is the original plan, not completion
evidence: check the repository and `SESSION_LOGS.md` for what is
actually implemented. Current focus is the priority above.

1.  **Freeze the shared contract with Marco** before independent
    implementation diverges. Pay particular attention to structured
    candidate answers and `ClarificationRequest`.
2.  **Run one real cloud API spike** using a legitimate free/low-cost
    model:
    -   one synthetic CV;
    -   several representative job descriptions;
    -   structured JSON output;
    -   evidence extraction;
    -   latency measurement;
    -   exact provider/model ID;
    -   quota/terms limitations actually checked.
3.  Choose **one** runtime provider if the test is adequate. Do not
    build a multi-provider system.
4.  Implement candidate/job semantic extraction against the shared
    schema. The LLM may map job wording only to approved constraint IDs.
5.  Implement the initial questionnaire fields, including explicit
    additional citizenships plus separate work-authorization/sponsorship
    declarations.
6.  Implement missing-information detection and structured clarification
    requests. The LLM may phrase the question, but every question must
    point to a predefined field.
7.  Implement deterministic eligibility rules and unknown handling. A
    hard conflict needs supported job evidence and explicit candidate
    information where required.
8.  Implement ranking using the confirmed factor families: profile fit,
    preference fit, urgency and defensible freshness. Keep weights
    configurable and unfrozen until development testing.
9.  Build the Streamlit UI around the shared engine, not around
    UI-specific business logic.
10. Implement the demo loop: upload -\> profile -\> questionnaire -\>
    shortlist -\> targeted clarification -\> structured answer -\>
    visible recomputation.
11. Keep explanations evidence-linked and clearly distinguish
    live/cache/fixture modes.

## Deliverables

-   `B-UI-01`: Streamlit UI reading real `JobRecord` data through the
    A-side boundaries (`get_demo_snapshot()` and the A-05 helper), with
    the pre-intelligence state handled explicitly.
-   `J-02-RUNTIME-01`: runtime model decision note with measured
    evidence.
-   `B-02-INTELLIGENCE-01`: candidate/job extraction + questionnaire +
    clarification contract, connected to the UI.
-   `B-03-ENGINE-01`: eligibility/ranking/gap/explanation flow returning
    Top 5 or fewer, running on A's real snapshot through the same UI.

## Done when

-   The UI can demonstrate the clarification wow moment on a controlled
    fixture.
-   A high semantic fit cannot override a deterministic hard conflict.
-   Missing facts stay unknown rather than being guessed.
-   The same engine can run on A's real snapshot without UI-specific
    schema patches.

## Do not do

-   Do not infer citizenship/work authorization from names, schools or
    nationality proxies.
-   Do not let free-form LLM text directly decide eligibility.
-   Do not spend money or enable billing without explicit approval.
-   Do not add job-specific CV generation; it is backlog.

## Handoff to

**Marco** for integration, **Giorgio G** for rule/evidence audit,
**Nils** for evaluation harness inputs, **Tommaso** for acceptance
testing.

------------------------------------------------------------------------

# Giorgio G - Group B: Eligibility Taxonomy & Synthetic Scenarios

## Your mission

Define the **closed hard-constraint language** that the engine can
safely use, and provide synthetic scenarios that force the rules to
behave correctly.

## Start now

**Task:** B-01 hard-constraint catalogue + persona/scenario packet.\
**Deadline:** initial version by 19 September; refine/freeze with
Pierpaolo by 20-21 September.

## Step by step

1.  Start from the provisional constraint families in the context:
    -   location/geographic availability;
    -   work authorization/sponsorship;
    -   required student/graduate status;
    -   graduation date/window;
    -   mandatory degree level;
    -   mandatory field of study;
    -   mandatory language;
    -   explicit minimum prior experience.
2.  For **each constraint**, define:
    -   candidate field required;
    -   job evidence required;
    -   wording that is truly mandatory;
    -   wording that must remain non-hard (`preferred`, `nice to have`,
        etc.);
    -   deterministic `met / conflict / unknown / not_applicable` rule;
    -   whether a clarification question can resolve missing candidate
        information.
3.  Create ambiguous examples deliberately. The expected result should
    often be `unknown`, not a forced answer.
4.  Review real wording supplied by Giorgio M/Pierpaolo. Use testing to
    propose additions/removals, but do not silently expand the taxonomy.
5.  Create three clearly synthetic development personas that exercise
    different rules and preferences.
6.  For each persona, specify known facts, exact supporting CV text,
    initial questionnaire answers and at least one intentionally missing
    fact that can trigger clarification.

## Deliverables

-   `B-01-CONSTRAINTS-01 r01`: hard-constraint catalogue.
-   `B-01-PERSONAS-01 r01`: three synthetic development
    personas/scenarios.

## Done when

-   Pierpaolo can implement each hard rule without interpreting vague
    business prose.
-   Every hard rule has positive, conflict and ambiguous examples.
-   The LLM has a closed target taxonomy rather than permission to
    invent gates.

## Do not do

-   Do not treat preferred qualifications as automatic ineligibility.
-   Do not infer legal/work status from citizenship unless the exact
    supported semantics are explicitly approved.
-   Do not claim expected persona facts are model outputs.

## Handoff to

**Pierpaolo** for implementation; **Nils** for evaluation-case design;
**Tommaso** for expected tests.

------------------------------------------------------------------------

# Nils - Group B: Evaluation Design

## Your mission

Run the frozen, reproducible evaluation once the held-out personas, job
pool, system outputs and independent human ratings are available. The
methodology itself is now frozen.

## Current status - 23 September

B-04 methodology is reported complete; execution inputs are pending. The
session log reports nine supporting artifacts: evaluability review,
protocol, rater sheet, evaluation case matrix, frozen-pool QA plan,
baseline run spec, run manifest, clarification audit and dependency
handoff. This context-integration session received the log but not those
nine files, so detailed artifact-level QA is still pending before
execution.

## Frozen methodology

-   comparison systems: embedding-only baseline, generic-LLM baseline,
    hybrid system;
-   three separate held-out personas, distinct from B-01 development
    personas;
-   factual `MET / CONFLICT / UNKNOWN` hard-constraint judgments plus
    anchored 0-3 application priority;
-   independent first-pass ratings and per-rater primary metrics;
-   explicit Top-5 tie handling;
-   atomic Top-5 evidence audit;
-   overall candidate-job unknown rate reported separately from
    constraint-level `UNKNOWN`;
-   at least one held-out persona with one pre-frozen withheld
    structured fact for clarification testing.

## Dependencies / blockers

-   final frozen 20-30 unique-job snapshot and manifest;
-   development-use/contamination record for candidate jobs;
-   three frozen held-out personas plus the pre-frozen clarification
    answer;
-   unresolved rule-owner values needed by the selected held-out cases;
-   final ranking weights and missing-factor normalization;
-   exact embedding-model version and LLM provider/model/runtime
    settings;
-   actual outputs and completed run manifests from Pierpaolo;
-   independent first-pass ratings from Anastasia and Madda.

## Next three actions

1.  Share the actual B-04 artifact pack with Marco/Pierpaolo and resolve
    any artifact-level review issue before the held-out run.
2.  With the rule owners, freeze the three held-out personas and
    required rule semantics, then QA/freeze the 20-30-job pool without
    inspecting system results.
3.  After both independent ratings and all three system runs exist,
    perform the evidence/clarification audits and calculate the frozen
    metrics separately for each rater.

## Step by step

1.  Do not reopen metric definitions because of observed held-out
    results. Any unavoidable change must be recorded before rerunning
    and clearly versioned.
2.  Confirm the unresolved B-01 semantics actually exercised by the
    held-out set, including the clarification destination if P02
    `HC_MIN_EXPERIENCE` is used.
3.  Freeze three held-out personas, including the one with the
    intentionally withheld approved fact and its pre-frozen answer.
4.  Receive the final snapshot, stable job IDs, source/evidence dates
    and contamination record; run the frozen-pool QA before looking at
    system outputs.
5.  Provide separate rater workbooks/instructions to Anastasia and Madda
    and preserve independent first-pass ratings.
6.  Ensure Pierpaolo runs all three systems on the same frozen universe
    and completes run manifests, including failures and retries.
7.  Compute per-rater human-referenced metrics, evidence audits,
    clarification audit and reproducibility outputs exactly as frozen.

## Current B-04 artifact pack reported in the session log

-   `B-01-EVALUABILITY-REVIEW-01_r01.xlsx`
-   `B-04-PROTOCOL-01_r01.docx`
-   `B-04-RATER-SHEET-01_r01.xlsx`
-   `B-04-EVALUATION-CASE-MATRIX-01_r01.xlsx`
-   `B-04-FROZEN-POOL-QA-PLAN-01_r01.xlsx`
-   `B-04-BASELINE-RUN-SPEC-01_r01.docx`
-   `B-04-RUN-MANIFEST-01_r01.xlsx`
-   `B-04-CLARIFICATION-AUDIT-01_r01.xlsx`
-   `B-04-DEPENDENCY-HANDOFF-01_r01.docx`

## Done when

-   The held-out pool/personas/configurations are frozen before
    system-result inspection.
-   Both raters submit independent first-pass ratings.
-   All three systems have reproducible run manifests with
    failures/retries preserved.
-   Frozen metrics and audits are computed with counts/denominators and
    no pre-filled target results.
-   The report can distinguish measured results from controlled
    synthetic edge cases and from methodology-only artifacts.

## Do not do

-   Do not tune weights using the held-out ratings.
-   Do not generate fake human ground truth with an LLM.
-   Do not pre-fill target results such as "0 violations".
-   Do not treat the session-log summary as artifact-level proof if the
    underlying B-04 file has not been reviewed.

## Handoff to

**Pierpaolo** for system execution/run manifests; **Anastasia + Madda**
for independent rating; **Marco/Giorgio/Pierpaolo** where rule or
frozen-input ownership applies; then back to **Nils** for metrics and
audits.

------------------------------------------------------------------------

# Anastasia - Group C: Independent Evaluation & Report Evidence

## Your mission

Provide an **independent human judgment** of the frozen evaluation
cases, then turn the observed results into clear report evidence. You
are deliberately not on the first technical critical path.

## Start date

**22 September**, when the frozen evaluation pack should be available.

## Step by step

1.  Receive from Nils:
    -   frozen candidate personas/declarations;
    -   frozen 20-30 job pool;
    -   job evidence;
    -   rater instructions and 0-3 scale.
2.  Rate **independently**, before discussing cases with Madda or the
    implementation team.
3.  For each candidate-job pair requested by the protocol:
    -   label supported hard-constraint status from the supplied
        evidence;
    -   assign the 0-3 application-priority rating;
    -   flag evidence that is ambiguous or insufficient.
4.  Produce your Top 5 using the protocol's tie rule.
5.  Only after both raters finish, participate in disagreement review.
    Do not retroactively rewrite your independent first-pass ratings.
6.  Support the evidence audit: check whether selected system claims are
    actually supported by the quoted CV/job evidence.
7.  After results are computed, help write report-ready observations
    that describe what was measured, not what the team hoped to see.

## Deliverable

`C-RATER-A-01`: completed independent rater sheet + evidence-audit
notes + short results observations.

## Done when

-   Ratings are complete without seeing/being influenced by the other
    rater's answers first.
-   Ambiguity is recorded instead of forced into certainty.
-   Report statements are traceable to measured tables/results.

## Do not do

-   Do not let an LLM choose the ratings for you.
-   Do not alter ratings to make the hybrid system look better.
-   Do not call yourself an external/unbiased expert; you are an
    independent team rater.

## Handoff to

**Nils** for metrics and **Madda/Group C** for report consolidation
after independent rating is complete.

------------------------------------------------------------------------

# Madda - Group C: Independent Evaluation, Presentation & Visuals

## Your mission

Provide the second **independent human rating** and then turn the
project's verified results into a concise visual/demo story for the
final presentation.

## Start date

**22 September**, when the frozen evaluation pack should be available.

## Step by step

1.  Complete the same frozen evaluation task as Anastasia
    **independently** using Nils's instructions.
2.  Do not compare answers with Anastasia until both first-pass rating
    sheets are complete.
3.  After ratings are locked, document important disagreements and what
    they reveal about ambiguity or subjectivity.
4.  Once measured results are available, identify the 1-2 strongest
    evidence-backed messages for Demo Day.
5.  Build visuals around real outputs, for example:
    -   the eligibility/clarification wow moment;
    -   a simple comparison of hybrid vs baselines;
    -   evidence/unknown handling;
    -   one limitation worth stating openly.
6.  Keep the live pitch within the course's 8-minute maximum. Avoid
    agenda/filler slides and protect time for the demo.
7.  Coordinate the final narrative with Anastasia and the technical
    leads without inventing performance claims.

## Deliverables

-   `C-RATER-M-01`: independent rater sheet.
-   `C-PITCH-01`: proposed pitch flow / visuals grounded in measured
    results.

## Done when

-   Your ratings are genuinely independent.
-   Every quantitative slide is backed by the frozen evaluation results.
-   The presentation emphasizes the product problem, the live demo and
    1-2 strongest verified strengths.

## Do not do

-   Do not use unmeasured claims such as "more accurate" or "better"
    without evidence.
-   Do not overload the 8-minute pitch with every feature.

## Handoff to

**Nils** for evaluation metrics and the **presentation team** for final
rehearsal.

------------------------------------------------------------------------

# Team gates everyone should know

-   **18 Sep:** shared contract freeze + first real cloud-model spike +
    repository skeleton.
-   **21 Sep:** Group A data/input path and Group B UI/intelligence path
    work separately and pass a small contract smoke test.
-   **22-23 Sep:** end-to-end flow works, including the clarification
    loop.
-   **24 Sep:** feature freeze; evaluation running; no new feature scope
    after this point.
-   **27 Sep:** report v1 + walkthrough v1 + presentation v1.
-   **28 Sep:** fixes, evidence checks, final recording, backup
    environment and rehearsal.
-   **29 Sep:** submission and presentation.

If the schedule slips, cut second ATS integration, public hosting, broad
career-advice polish, extra visuals and elaborate freshness scenarios
before cutting real CV extraction, structured profiling/clarification,
eligibility correctness, evidence, evaluation or the end-to-end demo.
