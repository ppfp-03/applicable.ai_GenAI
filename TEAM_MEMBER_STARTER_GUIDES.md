# Opportunity Intelligence - Team Member Starter Guides

This is the updated operational version.

## Immediate project-wide priority - Demo Stabilization

**Approved by Marco on 2026-09-27.** Before non-blocking feature work, the team must triage and close the final demo-feedback package recorded in the 27 September session log. The source list contains two different entries both numbered "(14)", so execution tracking treats it as **18 distinct observations** (`DEMO-01` to `DEMO-18`). No item is dropped or silently merged.

The feedback contains both observed problems and suggested remedies. The priority change is approved; the individual suggested remedies are not automatically new product decisions. Owners must implement within the existing contracts and product decisions, and escalate any conflict before changing behavior.

### Stabilization routing within existing ownership

- **Pierpaolo:** primary owner for UI/navigation/layout/state-persistence issues across onboarding, profile review, Explore/Fine-tune, ranking/job cards, clarification screens and application details.
- **Marco:** investigate/runtime-fix any incorrect AI-extracted or AI-generated candidate/job values surfaced by the issues, especially language representation and unsupported profile-derived text.
- **Giorgio G:** verify deterministic eligibility semantics where work authorization, sponsorship, `UNKNOWN` states or clarification-trigger conditions are implicated.
- **Giorgio M:** verify ranking behavior where clarification can change the top role or where ranking state is shown inconsistently.
- **Tommaso:** maintain the stabilization acceptance register, retest each resolved issue on the integrated target build, then execute the frozen final acceptance suite.

### Demo issue register

| ID | Reported issue / desired outcome | Primary routing |
|---|---|---|
| DEMO-01 | Welcome / "Here’s how it works" panel and text are too small; improve readability. | Pierpaolo |
| DEMO-02 | After CV upload/extraction completes, avoid leaving the user on a completed read-only step; evaluate automatic progression to the next step. | Pierpaolo |
| DEMO-03 | Step-introduction panels for later steps are too small; improve readability/scale. | Pierpaolo |
| DEMO-04 | In "Here’s what we found", clicking a missing-information area should lead to the relevant input/edit flow rather than a dead-end insufficient-information screen. | Pierpaolo + Tommaso |
| DEMO-05 | A native Italian language entry is displayed as "level not stated"; verify extraction/representation and user-facing native-language wording. | Marco + Pierpaolo |
| DEMO-06 | The right-side duplicate CV summary is low-value and extracted facts need an obvious correction/edit path; evaluate the proposed edit-first layout. | Pierpaolo |
| DEMO-07 | Adding EU work authorization unexpectedly populates sponsorship countries that were not selected. | Pierpaolo + Giorgio G |
| DEMO-08 | Expanded profile sections remain narrow and waste screen space; use the expanded state more effectively. | Pierpaolo |
| DEMO-09 | Step 3 Explore needs a way to review/change previous answers before continuing. | Pierpaolo |
| DEMO-10 | Review the Step 3 Explore explanatory copy beginning "Just for you..." for clarity and fit with the confirmed Explore-to-Fine-tune behavior. | Pierpaolo |
| DEMO-11 | Fine-tune shows unexplained profile-derived locations and can show eligibility facts as "not answered" without an obvious resolution path; verify source logic and interaction. | Marco + Pierpaolo + Giorgio G |
| DEMO-12 | Step 4 is unclear, shows repeated "8" values and low-value side content; clarify what the step technically represents. | Pierpaolo |
| DEMO-13 | Step 5 can state that one answer could make a role #1 but does not let the user answer or inspect/switch to other jobs. | Pierpaolo + Tommaso + Giorgio M |
| DEMO-14 | Step 5 job cards are not interactive enough to inspect a job in more detail. | Pierpaolo |
| DEMO-15 | Returning to Step 5 after completing it should not unnecessarily replay the job-selection/loading animation if state is already available. | Pierpaolo |
| DEMO-16 | Transition from Step 5 can skip Clarify and jump to Step 7 even when missing information could change the top role; verify clarification gating. | Tommaso + Pierpaolo + Giorgio G |
| DEMO-17 | In Step 7, the first job offer does not open details while later offers do. | Pierpaolo |
| DEMO-18 | Application detail view has excessive empty space; evaluate a clearer job-description-versus-criteria/evidence comparison layout. | Pierpaolo |

### Stabilization exit criteria

The priority override ends only when: (1) each `DEMO-*` item is fixed and verified, shown not to reproduce, or explicitly deferred; (2) the fixes exist together in one integrated target build; (3) Tommaso reruns the relevant regressions plus the final acceptance suite; and (4) unresolved issues that could affect the live demo are explicitly surfaced before recording the walkthrough/backup demo.

### 27 September starting-state checks before duplicate work

Use the latest session evidence as a starting point, not as closure evidence for the `DEMO-*` register:

- PR #23 was explicitly observed merged and adds clickable inline `Edit profile` entry points for Work authorization and Sponsorship. Verify the behavior on the integrated target build before crediting it against any demo issue.
- PR #20, PR #21 and PR #22 were observed as submitted/ready during Giorgio M's session, but their final merge state was not recorded there. Verify their status from repository evidence before reimplementing the same UI work.
- Marco's standalone AI pipeline demo is a technical walkthrough artifact and does not replace the Streamlit product demo. AI implementation is frozen except for blocking demo defects.
- The latest Marco runtime session observed two onboarding/work-authorization test failures outside his task scope. Treat them as current acceptance inputs until the responsible owner verifies or resolves them.

## Repository implementation ownership

Direct repository implementation is owned by five feature owners.

All coding work follows a feature-branch + pull-request workflow. Each
feature has one owner and one controlled integration path.

## Marco - AI Runtime & Intelligence Integration

Branch: `feature/ai-runtime-marco`

Mission: Implement the AI layer connecting candidate/job documents to
structured intelligence outputs.

Owns: - provider abstraction - LLM runtime integration - candidate
extraction - job requirement extraction - evidence-backed outputs -
extraction provenance - prompt versioning - runtime decision support

Does not own: - eligibility rules - ranking - UI - contract changes
without approval

Current 27 Sep priority: AI implementation is frozen unless a blocking demo defect requires runtime/extraction work. During stabilization, Marco investigates AI/runtime-backed issues such as `DEMO-05` and the unsupported-profile-text portion of `DEMO-11`, and provides the standalone cached pipeline as technical walkthrough evidence.

## Pierpaolo - UI Production Integration

Branch: `feature/ui-production-pierpaolo`

Mission: Convert the approved design system into the production
Streamlit experience using canonical contracts.

Owns: - onboarding - profile screens - opportunities list - opportunity
details - clarification screens - loading/error states - UI integration

Does not own: - separate business logic - duplicate ranking - duplicate
eligibility engine

Current 27 Sep priority: lead the single integrated Streamlit demo-stabilization build, verify the final merge state of relevant UI PRs before duplicating work, and close the UI/navigation/layout/state items in the `DEMO-*` register through one reviewable integration path.

## Giorgio G - Eligibility Engine

Branch: `feature/eligibility-engine-giorgio-g`

Mission: Implement deterministic eligibility evaluation.

Owns: - RuleCatalogue - hard-constraint evaluation - MET / CONFLICT /
UNKNOWN / NOT_APPLICABLE handling - eligibility tests

Principle: LLM outputs may provide structured information, but
deterministic rules decide eligibility.

Current 27 Sep priority: support only stabilization defects that reproduce inside eligibility ownership, especially work-authorization/sponsorship state, `UNKNOWN` handling and clarification-trigger semantics. Do not expand rule scope during the demo freeze unless an approved decision requires it.

## Giorgio M - Ranking Engine

Branch: `feature/ranking-engine-giorgio-m`

Mission: Implement opportunity prioritization.

Current implementation status: ranking Phases 1-3 are complete for the currently available dependencies, including deterministic ranking primitives, the internal ranking pipeline and the eligibility-to-ranking adapter. No new ranking implementation is unlocked by the 27 September runtime review.

Development configuration used in tests: Profile fit 40%, Preference fit 25%, Deadline urgency 20%, Freshness 15%. **These weights are not frozen project truth.** `PROJECT_CONTEXT.md` D-022/Q-05 governs: final ranking weights/configuration remain TO VALIDATE and must be approved before held-out evaluation. Missing-factor renormalization is likewise an implemented development semantic, not a substitute for project-level freeze.

Current blockers: approved profile-fit/embedding method; real-job country codes; real-job deadlines; `role_family`; shared `RankingConfig`/`RankingItem`/`RankingResponse` freeze; canonical project-level ranking configuration.

Owns: - ranking engine - embedding boundary - scoring configuration -
ranking tests

Does not own: - eligibility decisions

Current 27 Sep priority: during demo stabilization, investigate only ranking-owned regressions such as the ranking/clarification behavior behind `DEMO-13`; otherwise remain blocked rather than inventing missing factors or configuration. At the start of the next repository session, verify the final merge state of PR #20, PR #21 and PR #22 before further UI follow-up.

## Tommaso - Clarification Engine & Acceptance

Branch: `feature/clarification-engine-tommaso`

Mission: Implement the missing-information loop.

Flow: Unknown fact → ClarificationRequest → Structured answer → Profile
update → Recompute

Owns: - clarification logic - structured answers - profile updates -
recomputation tests

After integration: Execute acceptance tests from `A-TESTS-01_r02.xlsx`.

Current 27 Sep priority: maintain the stabilization regression register, verify the exact integrated SHA, retest every closed `DEMO-*` issue that affects behavior, reconcile current onboarding/work-authorization failures, and then execute the frozen final acceptance suite without combining results from separate builds.

## Feature branch workflow

Every coding task follows:

1.  Create a dedicated feature branch.
2.  Modify only the assigned feature scope.
3.  Run verification.
4.  Open a pull request.
5.  Review before merge.

Each PR handoff must include: - branch name - base commit - changed
files - verification commands - unresolved issues

## Integration order

The normal dependency order remains:

1.  AI Runtime
2.  Eligibility
3.  Ranking
4.  Clarification
5.  UI integration

During the final demo-stabilization override, issue routing and the requirement for one integrated target build take precedence over starting new non-blocking work. The UI consumes stabilized outputs and should not define business logic.

## Non-coding members

Nils: Evaluation methodology, frozen inputs and metrics.

Anastasia: Independent evaluation rating and evidence review.

Madda: Independent evaluation rating and presentation visuals.
