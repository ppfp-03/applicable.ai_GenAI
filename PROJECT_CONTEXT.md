# Opportunity Intelligence - Project Context

**Role of this file:** current project truth only. It records confirmed facts, approved project/technical decisions, constraints, contracts, open questions, evaluation design and source boundaries. It does **not** contain member assignments, task schedules, assistant workflows, response templates or session history.

| Control | Value |
|---|---|
| Context version | 0.4.6-draft - Group A Greenhouse batch ingestion behavior approved |
| Contract version | 0.2.0-draft core frozen; JobSnapshot 0.2.1-draft jointly approved; result/config envelopes remain separately unfrozen |
| Created | 2026-09-17 |
| Last updated | 2026-09-22 |
| Project deadline | 2026-09-29; exact submission time/timezone still to confirm |
| Current-state boundary | Planning/product decisions are recorded here; implementation and measured progress require repository/session evidence |

For current roles, assignments, priorities, deadlines and handoffs use `TEAM_MEMBER_STARTER_GUIDES.md`. For chronological work evidence use `SESSION_LOGS.md`. For assistant behavior use the Project Operating Instructions. Project Guidelines remain authoritative for course requirements; the Project Proposal records the original project scope and rationale.

**Canonical storage:** the repository-root `PROJECT_CONTEXT.md` is the single editable canonical copy of current project truth. The ChatGPT Project Source copy is a convenience mirror for project conversations and must be refreshed after approved context changes. If the two copies differ, the repository-root file governs until the mirror is synchronized. This storage rule does not change the source roles defined below.


## 1. Mission and evidence boundary

Help university students and recent graduates make better decisions across the early-career application journey. The MVP is a **career/application assistant** that combines a bounded job-discovery view, structured candidate profiling, explicit eligibility checks, application prioritisation, gap analysis and targeted questions when important candidate information is missing.

The central decision problem remains: **which opportunities deserve the candidate's attention and application time first?** Discovery is useful because the system needs a relevant opportunity set, but the MVP is not trying to become a general-purpose global job-search engine. If scope pressure appears, preserve eligibility, prioritisation, evidence, clarification and evaluation before adding breadth.

The technical proposition is a hybrid system: an LLM interprets unstructured CV/job language, extracts structured facts, classifies non-hard requirements and formulates targeted clarification questions; deterministic rules apply approved hard constraints and structured answers; embeddings and transparent factors support ranking; the UI exposes evidence, uncertainty, gaps, urgency and freshness when supported. We are not building a recruiting decision system, a hiring-probability predictor, a legal eligibility service or an autonomous application bot.

The MVP target is intentionally narrow in seniority/domain even though the long-term product vision is broader: students/recent graduates applying to internship and entry-level opportunities in business, finance, economics, management and closely related commercial/managerial/financial roles.

**Source distinction:** the original proposal specifies the broader architecture and evaluation intention [P2]. This framework incorporates later team kick-off decisions and implementation recommendations. Items marked `PROPOSED`, `OPEN`, `TO VALIDATE` or `pending sign-off` are not professor-approved requirements and must not be represented as completed work. Course deliverables come from [P1]; team decisions are recorded as [P3]. The decision register and source references are included later in this document.

## 2. Deliverables and success criteria

All submission deliverables and Demo Day are due 29 September, per the team.

| Deliverable | Required or agreed scope |
|---|---|
| Working tool and live presentation | Live demo; up to 8 minutes pitch plus about 2 minutes Q&A; 2-3 speakers, other members lead Q&A [P1] |
| Recorded walkthrough | Explain functionality and implementation in greater depth than the live pitch [P1] |
| Backup recording | Reproduce the essential demo if live execution fails [P1] |
| Technical report | 6-12 pages excluding appendices; PDF, 12-point, single-spaced, 1-inch margins [P1] |
| Repository reference | Include the project repository link in the report; accessibility/visibility must be checked [P1] |
| AFU-lite technical input | Short functional specification using the structure agreed by the team; an internal report-building aid, not an additional course requirement |

The report needs team contributions, a one-page executive summary, business problem, solution/design process, data/methodology, technical implementation, results/evaluation, limitations/future work, ethics, references, repository/video links and disclosure of AI-assisted writing [P1]. The report/walkthrough rubric allocates 20 points each to problem/solution, implementation, results/analysis, walkthrough and communication. Do not substitute a polished interface for evaluation evidence.

**AFU-lite does not replace technical implementation or evaluation.** It documents what the system should do, its rules, inputs/outputs and acceptance criteria. The report must still explain actual tools, models, code structure, experiments, results and limitations. It is not represented as an official or confidential ACN template.

## 3. Scope and product decisions

### Must work

1. Load/show a bounded set of relevant internship and entry-level opportunities from a reproducible public-job snapshot.
2. Upload a **synthetic, text-based PDF CV**, extract its text, then visibly extract a structured profile using a real runtime model.
3. Offer three synthetic personas as an additional, clearly labeled route for development/demo/evaluation.
4. Let users inspect/correct extracted information and complete an initial structured questionnaire, including explicit location, work-authorization/sponsorship information and whether they hold additional citizenships.
5. Detect important candidate-profile gaps that matter to supported opportunities and generate targeted clarification questions linked to predefined structured fields.
6. Apply a **closed, versioned hard-constraint taxonomy** and distinguish `eligible`, `ineligible`, `uncertain` under the implemented rules.
7. Classify other job requirements into fit/ranking or informational categories without turning them into unapproved hard gates.
8. Produce a Top 5, or fewer when appropriate, with transparent ranking components, relevant gaps and evidence-linked explanations.
9. Recompute eligibility and ranking when a relevant candidate answer, declaration or preference changes.
10. Use profile fit, preference fit, deadline urgency and defensible freshness as the ranking factor families; exact weights remain TO VALIDATE until development testing.
11. Show truthful source timestamps, missing information, evidence provenance and runtime/cache status.
12. Run comparison baselines and an evidence-backed evaluation on a frozen set.

### Nice to have

- Strategic suggestions for improving the candidate profile beyond the immediate job comparison.
- Broader career advice beyond the supported opportunity set.
- A second ATS/source when the coverage test shows material value and integration is low risk.
- Additional visual polish or public hosting after the core/evaluation is stable.

### Backlog / not in this MVP

- Automatic job-specific CV tailoring or generation.
- Creating multiple CV variants for different postings.
- Authentication, application submission, employer-side candidate ranking, scraping restricted websites, email/notifications, production hosting as a requirement, complex multi-agent orchestration, automatic web browsing by the runtime LLM, fine-tuning, OCR for scanned CVs, multilingual evaluation and arbitrary document formats.

### Working defaults - confirm technically before freeze

- Python + Streamlit, one process, local-first execution for the demo; UI ownership is maintained in `TEAM_MEMBER_STARTER_GUIDES.md`.
- Greenhouse first. Add Ashby and/or Lever only if the coverage test shows Greenhouse is insufficient for the agreed market/domain.
- Persisted `JobSnapshot` artifacts use one UTF-8 JSON object under the jointly approved `0.2.1-draft` envelope. JSONL remains optional only for unrelated development artifacts that define their own shape; no database is required for the first version. Add SQLite only for a documented need.
- Local sentence embeddings and direct cosine similarity; no vector database.
- Explicit refresh during preparation, not a background polling service.
- One chosen cloud runtime-model provider behind a very small adapter; exact provider/model TO VALIDATE.
- English-language app/input-output handling for the initial demonstration/evaluation even when jobs come from the broader target geography; multilingual support is not an MVP claim.

### Market - KICK-OFF DECISION

**Candidate target:** university students and recent graduates applying to internships and entry-level roles. This is an MVP restriction, not a statement about the future product ceiling.

**Role families:** Business, Finance, Economics, Management and closely related commercial, managerial and financial roles. Exclude STEM-specialist, legal and clearly unrelated professional families from the MVP corpus.

**Target geographies:**
- Europe: Italy, Spain, United Kingdom, France, Germany, Switzerland, Netherlands, Luxembourg, Denmark, Ireland.
- Asia: Shanghai, Shenzhen, Singapore, Hong Kong.

Target-market support **does not require balanced or exhaustive dataset coverage across every geography**. Coverage gaps must be reported honestly. Keep countries/role families in configuration, not scattered through code.

### Deployment - RECOMMENDED

Use a **local Streamlit application** on the presentation laptop and test on a second laptop. Public hosting is a stretch item after the core works; the guidelines do not require it. A local UI calling a cloud model still requires internet. Offline capability must be demonstrated, not inferred from the word "local".

## 4. Runtime model and cost decision

Coding assistants and the model inside the app are separate components. Do not assume Codex/Claude Code access is a runtime API credential or wire the app to a personal coding session.

**Preference: zero additional spend; no paid calls without explicit approval.** No runtime provider, key or free quota has yet been verified.

### Runtime strategy - KICK-OFF DECISION

Use a **cloud API first**. The runtime owner assigned in `TEAM_MEMBER_STARTER_GUIDES.md` runs one short real extraction spike and selects one legitimate free/low-cost cloud option if it meets the MVP needs. Do not build several providers in parallel. A local model is a fallback only if the cloud-first path proves unsuitable and the team explicitly decides it is worth testing.

J-02 output: a short decision note with exact provider/model identifier, access mode, measured extraction result, approximate latency, limitations, current terms/quota evidence and approval status. Use at least one synthetic CV and several development job descriptions. A provisional target is usable extraction within about 20 seconds on the presentation setup; this is a proposed UX target, not a measured fact or course requirement.

Define a small provider adapter once. Configure provider/model identifiers outside business logic. Use bounded input size, timeouts, at most one schema-repair retry and explicit rate-limit handling.

### What GenAI does

- Extracts structured facts from synthetic CV text.
- Extracts structured facts and requirements from job descriptions.
- Maps explicit mandatory job language to **approved** hard-constraint IDs; it may not invent new hard constraints.
- Classifies non-hard requirements into approved fit/ranking or informational categories.
- Identifies important missing candidate information that blocks or materially affects supported opportunity assessment.
- Formulates natural-language clarification questions linked to predefined structured fields.
- Produces evidence-linked explanations and gap summaries where enabled.
- May produce strategic profile/career suggestions only as a secondary feature; these suggestions never change deterministic eligibility by themselves.

### What remains deterministic

- Applying candidate declarations/corrections.
- Meaning and evaluation of each approved hard constraint.
- Missing/unknown handling and eligibility aggregation.
- Ranking calculations, active-factor normalization, sorting and stable tie handling.
- Recomputing results after a structured candidate answer changes.
- Deciding whether an evidence-backed rule outcome is `met`, `conflict`, `unknown` or `not_applicable`.

Structured outputs constrain format; they do not establish that facts are correct. Validate field values and source evidence separately [S10]. Never present an invalid response as a successful extraction.

**Profiling rule:** the initial questionnaire should proactively collect persistent facts that are likely to matter repeatedly, including whether the candidate holds additional citizenships. Citizenship must be explicitly declared and is **not automatically equivalent to work authorization**; the supported work-authorization/sponsorship rule must use separately approved semantics and declarations.

## 5. End-to-end architecture and mode transparency

```text
Public job source -> A: ingest/normalize -> versioned job snapshot
                                               |
                                               v
                                  B: extract job facts once
                                               |
Synthetic PDF -> A: text extraction -> B: candidate extraction
                                               |
                         initial questionnaire + user correction
                                               |
                                               v
                    B: detect decision-relevant profile gaps
                                               |
                   B: structured clarification request (if needed)
                                               |
                         user answer -> structured candidate field
                                               |
                                               v
                          B: deterministic eligibility rules
                                               |
                          B: embeddings + ranking factors
                                               |
                     B: gaps + evidence-linked explanations
                                               |
                          B: Streamlit shortlist + what-if
                                               |
                       B/C: evaluation; A/B: evidence logs
```

A owns public-job ingestion, normalization, reproducible snapshots, PDF-to-text plumbing and data/input integration. B owns **semantic extraction from both CV text and job text, profiling/clarification, eligibility, ranking, explanations/gaps and the Streamlit UI**. Neither group creates a second implementation of the other's stage. The UI calls shared A/B boundaries rather than embedding a second ingestion or ranking engine.

The clarification loop is structured: the LLM may phrase the question naturally, but each question must point to an approved candidate field/constraint. The user's answer updates structured session data, then the deterministic engine recomputes the affected eligibility/ranking results. Do not repeatedly ask for persistent information that should have been captured in the initial questionnaire.

### Three explicitly labeled execution modes

| Mode | Meaning | Permitted use |
|---|---|---|
| `live` | A model actually processes this input during this run, via the selected cloud API | Genuine extraction/clarification demonstration and live integration tests |
| `cache` | Previously produced model output is reused for the exact supported cache key | Repeatability and disclosed fallback |
| `fixture` | Handcrafted synthetic input/output used for development | Contract tests; never evidence of model quality |

Track job-source mode and model mode separately. A cached job snapshot can legitimately be combined with live CV extraction. Reading PDF text live while reusing cached semantic output is **not** live semantic extraction.

Cache key: input content hash + provider/model ID + prompt version + schema version + relevant parameters. Persona identity or filename alone is never a valid key. A modified document must invalidate the extraction cache. Changing structured preferences/declarations should rerun the deterministic engine without re-parsing an unchanged CV unless the extracted semantic facts themselves changed.

The demo must show extraction from the uploaded file, not choose a prebuilt profile by filename. Prepare a second, visibly modified synthetic CV as a smoke test. If live inference fails, explicitly switch to the labeled cached scenario or recording. Never silently substitute outputs.

### Data acquisition and freshness

Target roughly **40-60 relevant unique postings** for development/demo, with a **frozen 20-30-job evaluation pool**. Prioritize scenario coverage and data quality over volume or balanced representation of every target geography.

Use **Greenhouse as the primary source**. The source-coverage work assigned in `TEAM_MEMBER_STARTER_GUIDES.md` determines whether Ashby and/or Lever add material value. Do not implement extra ATS integrations merely because they appeared in the original proposal.

Preserve source identifiers, URL, description, timestamps and provenance. Use bounded public GET requests; never submit applications. Source fields must be verified before relying on them.

- `source_published_at`: only an actual publication timestamp explicitly provided by the source.
- `source_updated_at`: source update time, kept separate.
- `first_seen_at`: when this system first observed this posting.
- `last_seen_at`: last successful observation.
- A failed request does not prove the job closed.
- Initial ingestion does not prove all jobs are newly published.
- A controlled new-posting demo must be labeled **simulated ingestion event**. It does not measure real-world monitoring latency.

Normalize HTML safely; do not render untrusted source HTML with unsafe execution. Deduplicate by source ID/URL first, then a conservative content signature. Do not merge distinct vacancies merely because titles match. Store a reproducible snapshot and manifest; record whether text can be redistributed before publishing source snapshots.

## 6. Shared contracts - core v0.2.0 + snapshot v0.2.1

This section contains the frozen core shared models for `0.2.0-draft`, the jointly approved `JobSnapshot 0.2.1-draft` extension, and downstream result/config design signatures whose exact serialization is still open. The document/job/requirement and candidate/clarification core models received the required joint Marco + Pierpaolo sign-off and verification on 2026-09-20. `JobSnapshot 0.2.1-draft` received joint Marco + Pierpaolo sign-off on 2026-09-20 under D-006/D-037. Any later change to a frozen cross-boundary model requires the approvals defined by project governance and an updated version/fixture.

### Freeze scope

**Frozen and verified in `0.2.0-draft`:**

- `SourceDocument`, `EvidenceRef`, `SupportedText`, `ExtractionReceipt` and the enums they directly use;
- `RequirementFact`, `JobFacts`, `JobLocation`, `JobRecord` and their approved enums;
- `CandidatePreferences`, `WorkAuthorizationDeclaration`, `UserDeclarations`, `EligibilityAnswer`, `CandidateProvenance`, `CandidateProfile`;
- `CandidateFieldPath`, `ClarificationRequest` and their approved answer/priority enums.

**Jointly approved shared extension in `0.2.1-draft`:**

- `SourceManifestEntry`, `QuarantineSummary` and `JobSnapshot`, with exact serialization and reference-integrity rules defined below. Existing embedded `JobRecord` payloads remain `0.2.0-draft` and unchanged.

**Still not frozen:**

- result/ranking envelopes in section F, including `RuleOutcome`, `RankingItem`, `RankingResponse`, and related component/error/count structures;
- `SourceConfig`, `RuleCatalogue`, `EligibilityResult`, `RankingConfig`, provider/embedding configuration types and other adapter/config envelopes named only in design signatures.

Their presence below records intended boundaries and minimum behavior only. It is **not** approval of their exact serialization. Freeze each remaining material shared envelope separately before independent implementation.

### Conventions

- UTF-8 JSON; snake_case field names; UTC ISO-8601 timestamps; stable string IDs.
- Use JSON `null` for missing scalar facts. Use explicit enum states where defined. Do not use `"N/A"`, an invented zero or an empty string to mean unknown.
- Scores are numbers, not strings. Arrays may be empty. Invalid or unsupported fields must be flagged, not guessed.
- Every extracted material fact that can affect eligibility or displayed explanations must link to evidence. A quote's presence is necessary, but semantic support also needs inspection/testing.
- All status enums serialize in lowercase. The UI may display friendly title case.
- Hard-constraint IDs come only from the approved versioned rule catalogue. Model output containing an unknown constraint ID fails validation or is treated as non-hard, never as a new gate.

### A. Evidence and documents

| Object | Required fields |
|---|---|
| `SourceDocument` | `document_id`, `kind` (`cv`, `job`, `questionnaire`, `ats_metadata`), `text`, `content_hash`, `source_ref` |
| `EvidenceRef` | `evidence_id`, `document_id`, `quote`, `field_path` |
| `SupportedText` | `value`, `evidence_ids` |
| `ExtractionReceipt` | `mode`, `provider`, `model_id`, `prompt_version`, `schema_version`, `input_hash`, `produced_at`, `latency_ms` |

`quote` must be found in the referenced document using the declared whitespace normalization. `source_ref` identifies the public source or synthetic/session document, not an invented URL. `latency_ms` is nullable when not measured; cached inference latency is not newly measured runtime latency.

Questionnaire and clarification answers become explicit `SourceDocument` inputs too, so a user override has provenance. Do not expose raw credentials or real CV content through the document registry.

### B. `JobRecord` - data/input creates, intelligence enriches

| Field | Type / rule |
|---|---|
| `schema_version`, `job_id`, `source`, `source_job_id` | Stable strings; source IDs form a namespaced job ID |
| `company`, `title`, `url` | Strings; missing essential identity fields produce a quarantined record |
| `description` | `SourceDocument`; empty/unusable descriptions cannot support semantic scoring |
| `source_documents` | Additional `SourceDocument` objects needed for ATS metadata evidence; preserve them through enrichment |
| `locations` | List of objects: `country_code` nullable string, `city` nullable string, `evidence_ids` list |
| `source_published_at`, `source_updated_at`, `deadline_at` | Nullable timestamps supported by explicit source evidence |
| `first_seen_at`, `last_seen_at` | Observation timestamps; retained across refreshes |
| `active_state` | `active`, `closed`, `unknown` |
| `discovery_kind` | `initial_snapshot`, `later_observation`, `synthetic_scenario` |
| `facts` | `JobFacts` or `null` before semantic extraction |
| `evidence` | List of `EvidenceRef` for source and extracted facts |
| `extraction` | `ExtractionReceipt` or `null` before extraction |

`JobFacts` supports `skills`, `experience`, `education`, nullable `role_family`, and `requirements`, with semantic text backed by `SupportedText` evidence IDs. For contract `0.2.0-draft`, `RequirementFact` serializes `requirement_id`, `text`, `classification`, `modality`, nullable `constraint_id`, and `evidence_ids`. `classification` is `hard_constraint`, `fit`, or `informational`; `modality` is `mandatory`, `preferred`, `optional`, or `unspecified`; `constraint_id` is required only for `hard_constraint`. `RequirementFact` represents the intelligence layer's structured interpretation of the job. Candidate-relative outcomes (`met`, `conflict`, `unknown`, `not_applicable`) are produced only by the deterministic rule engine.

Do not resolve ambiguous cities/countries through unsupported inference. A source-provided structured country or an explicit, documented normalization map can be used; ambiguous locations remain unknown. Sponsorship/work-authorization claims are usable only when their scope clearly applies to the location/role being checked.

### C. `CandidateProfile` - intelligence creates; user confirms

The jointly approved `0.2.0-draft` candidate schema is:

| Object | Fields / rules |
|---|---|
| `CandidateProfile` | `schema_version`, `candidate_id`, `cv_document_id`, `skills: list[SupportedText]`, `education: list[SupportedText]`, `experience: list[SupportedText]`, `preferences: CandidatePreferences`, `declarations: UserDeclarations`, `eligibility_answers: dict[str, list[EligibilityAnswer]]`, `provenance: CandidateProvenance` |
| `CandidatePreferences` | `allowed_country_codes: list[str] | null`, `preferred_country_codes: list[str]`, `preferred_role_families: list[str]`, `preferred_industries: list[str]` |
| `UserDeclarations` | `additional_citizenships: list[str]`, `work_authorizations: list[WorkAuthorizationDeclaration]` |
| `WorkAuthorizationDeclaration` | `country_code`, `authorized_to_work: bool | null`, `requires_sponsorship: bool | null`, `evidence_ids: list[str]` |
| `EligibilityAnswer` | `constraint_id`, non-empty `answer_key`, `state` (`known` or `unknown`), `answer_type`, `value`, `evidence_ids`, `source_document_id` |
| `CandidateProvenance` | `questionnaire_document_ids`, `clarification_document_ids`, `documents: dict[str, SourceDocument]`, `evidence: list[EvidenceRef]`, `extraction: ExtractionReceipt` |

Candidate country-code values use valid ISO 3166-1 alpha-2 codes normalized to uppercase and without duplicates. `allowed_country_codes = null` means no explicit geographic restriction has been declared; when present it must be non-empty, so `[]` is invalid. If `allowed_country_codes` is present, every preferred country must fall inside that declared perimeter. Work-authorization declarations are unique by `country_code`. `authorized_to_work` and `requires_sponsorship` are independently nullable and one must never be inferred from the other.

`EligibilityAnswer.value` is closed to JSON-safe values corresponding to `bool | str | int | date | list[str] | null`. `state=unknown` requires `value=null`; `state=known` requires a non-null value. `answer_type` and `value` must match strictly, including rejection of bool-as-int and analogous permissive coercions. The outer key in `eligibility_answers` must equal each contained answer's `constraint_id`. The shared contract validates `answer_key` shape/non-emptiness but does **not** validate membership in a `constraint_id -> answer_key` catalogue; that later membership check belongs to the deterministic `RuleCatalogue`.

Specialized facts remain canonical in their specialized objects. In particular, work authorization and sponsorship live in `UserDeclarations.work_authorizations` and are not duplicated in `eligibility_answers`.

Candidate provenance is internally resolvable. `cv_document_id` must resolve to `provenance.documents` and reference `kind="cv"`. Questionnaire and clarification document IDs must resolve to registry documents using the already-approved `kind="questionnaire"`; clarification is distinguished by its logical ID list rather than a new document kind. `evidence_id` values are unique within `provenance.evidence`. Evidence IDs referenced by candidate fields must resolve in `provenance.evidence`; every `EvidenceRef.document_id` must resolve in `provenance.documents`. `EligibilityAnswer.source_document_id` must resolve in the document registry, and any evidence IDs on that answer must belong to the same source document.

Citizenships, work authorization, sponsorship needs and protected/sensitive attributes are never inferred from names, universities or proxies. Additional citizenships are collected explicitly. Citizenship is not automatically treated as proof of work authorization unless a separately approved country-specific rule explicitly supports that inference.

### D. Clarification loop - intelligence returns; UI renders

The jointly approved serializable `ClarificationRequest` contains:

- `question_id`;
- `field_path: CandidateFieldPath | null`;
- `constraint_id: str | null`;
- natural-language `question`;
- `answer_type`;
- `allowed_choices`;
- short `reason`;
- affected `job_ids`;
- relevant `evidence_ids`;
- `priority`, using the closed enum `high | medium | low`.

At least one of `field_path` or `constraint_id` is required. `answer_type` is one of `boolean`, `single_choice`, `multi_choice`, `text`, `date`, or `integer`. `allowed_choices` is required and non-empty for `single_choice` and `multi_choice`, and must be `null` for every other answer type. No generic `validation` dictionary is part of `0.2.0-draft`.

`CandidateFieldPath` is not a free string. It is structurally restricted to these approved destination families:

- `preferences.allowed_country_codes`
- `preferences.preferred_country_codes`
- `preferences.preferred_role_families`
- `preferences.preferred_industries`
- `declarations.additional_citizenships`
- `declarations.work_authorizations.<COUNTRY>.authorized_to_work`
- `declarations.work_authorizations.<COUNTRY>.requires_sponsorship`
- `eligibility_answers.<CONSTRAINT_ID>.<ANSWER_KEY>`

For the eligibility-answer family, the shared contract validates only the approved path structure. Membership of `<ANSWER_KEY>` in a particular `<CONSTRAINT_ID>` belongs to the deterministic `RuleCatalogue`. If a clarification path is `eligibility_answers.<CONSTRAINT_ID>.<ANSWER_KEY>` and `ClarificationRequest.constraint_id` is also present, the two constraint IDs must match.

The LLM may phrase the question, but it cannot create a new destination field or rule. The answer must become structured session data before recomputation. Persistent facts that are broadly useful should be requested in the initial questionnaire rather than repeatedly as job-specific clarification.

Shared compatibility fixtures for this schema are frozen at:

```text
tests/fixtures/contracts/v0.2.0-draft/
├── candidate_profile.json
├── clarification_request.json
└── job_record.json
```

The fixture gate is not only syntactic. On 2026-09-20, all three fixtures passed load -> Pydantic validation -> serialize -> reload, and the full contract suite passed the agreed negative/reference checks (`121 passed`) at implementation commit `03a208a`. The `0.2.0-draft` shared contract is therefore frozen at that verified boundary.

### E. `JobSnapshot` - data/input persists; intelligence consumes

The jointly approved `0.2.1-draft` snapshot envelope is a backward-compatible extension around frozen `0.2.0-draft` `JobRecord` payloads. Persist each snapshot atomically as one UTF-8 JSON object, not JSONL.

| Object | Required fields / rules |
|---|---|
| `SourceManifestEntry` | `source`, `source_ref`, `retrieved_at`, `record_count`, `redistribution_allowed` |
| `QuarantineSummary` | `reason`, `count` |
| `JobSnapshot` | `schema_version`, `snapshot_id`, `created_at`, `jobs`, `documents`, `source_manifest`, `quarantine` |

`JobSnapshot.schema_version` is exactly `0.2.1-draft`. Existing `JobRecord` objects embedded in `jobs` retain their frozen `0.2.0-draft` schema and semantics. New shared models use the existing strict-extra contract behavior. `snapshot_id`, manifest source/source-ref values and quarantine reasons are non-empty. `created_at` and `SourceManifestEntry.retrieved_at` are timezone-aware and normalize to UTC. `SourceManifestEntry.record_count >= 0`; `redistribution_allowed` is `true`, `false` or `null`; `QuarantineSummary.count > 0`.

`documents` is the canonical snapshot document registry. Every registry key must equal the contained `SourceDocument.document_id`. Every job `description` and each item in `source_documents` must resolve under the same ID and match the canonical `SourceDocument` value. Every top-level `JobRecord.evidence[].document_id` must resolve in `documents`; a dangling reference makes the snapshot invalid. A-01 does not add a new rule mapping every field-level `evidence_id` to `JobRecord.evidence`, does not require uniqueness of job IDs/manifest entries/quarantine reasons, and does not reconcile manifest counts against job/quarantine totals.

`quarantine` stores summary metadata only; raw quarantined payloads are outside the shared snapshot. This extension does not change `RuleCatalogue`, ranking semantics or any frozen `0.2.0-draft` record behavior.

The A-owned loader signature is exact for A-01:

```python
def load_snapshot(path: Path) -> JobSnapshot: ...
```

The A-owned PDF boundary remains text-only and does not add OCR:

```python
class PdfExtractionError(ValueError): ...

def extract_pdf_text(pdf_bytes: bytes, document_id: str) -> SourceDocument: ...
```

Malformed/unreadable PDFs, unusable encrypted PDFs and PDFs with no extractable text surface as `PdfExtractionError`. No OCR, external process, network call or new dependency is part of this boundary.

### F. Design-only result envelopes - intelligence returns; UI renders

`RuleOutcome`: `rule_id`, `status` (`met`, `conflict`, `unknown`, `not_applicable`), `candidate_evidence_ids`, `job_evidence_ids`, `reason`.

`RankingItem`: `job_id`, `eligibility` (`eligible`, `ineligible`, `uncertain`), `rule_outcomes`, nullable `priority_score`, `components`, `gaps`, `explanations`, `warnings`.

Each score component contains `name`, nullable `value`, `effective_weight` and `evidence_ids`. Each explanation contains `claim` and `evidence_ids`. A heuristic comparison must be labeled as an interpretation, not a quoted fact.

`RankingResponse`: `schema_version`, `candidate_id`, `snapshot_id`, `evaluated_at`, `rule_version`, `ranking_config_version`, `ranked_items`, `excluded_items`, `clarification_requests`, `errors`, `counts`.

`excluded_items` retain the job ID and exclusion reason, including explicit incompatibility, closed/expired posting or unusable data. Never silently lose rows. Data-quality failure is not a finding of candidate ineligibility.

### G. Public boundaries and ownership

```python
# A-01 load/PDF signatures below are approved and exact. Other named result/config
# signatures remain design-only until separately frozen. I/O and dependencies are
# passed explicitly; business logic does not import Streamlit.

# Data/input layer
def fetch_jobs(source_config: SourceConfig) -> list[JobRecord]: ...  # design-only
def load_snapshot(path: Path) -> JobSnapshot: ...                   # approved D-037
class PdfExtractionError(ValueError): ...                            # A-owned
def extract_pdf_text(pdf_bytes: bytes, document_id: str) -> SourceDocument: ...  # approved

# Intelligence + UI caller
def extract_candidate(cv: SourceDocument, declarations: UserDeclarations,
                      model_client: ModelClient) -> CandidateProfile: ...
def apply_declarations(candidate: CandidateProfile,
                       declarations: UserDeclarations) -> CandidateProfile: ...
def enrich_jobs(jobs: list[JobRecord], model_client: ModelClient) -> list[JobRecord]: ...
def build_clarification_requests(candidate: CandidateProfile,
                                 jobs: list[JobRecord]) -> list[ClarificationRequest]: ...
def assess_eligibility(candidate: CandidateProfile, job: JobRecord,
                       rule_catalogue: RuleCatalogue) -> EligibilityResult: ...
def rank_opportunities(candidate: CandidateProfile, snapshot: JobSnapshot,
                       ranking_config: RankingConfig, embedding_client: EmbeddingClient,
                       now: datetime) -> RankingResponse: ...
```

`JobSnapshot` exact serialization and reference-integrity rules are frozen in section E under D-037. Result/config types in this section remain design-only unless separately approved.

`UserDeclarations` contains structured candidate preferences and explicit questionnaire/clarification values. `apply_declarations` is deterministic and does not call an LLM. Source, ranking, clarification and adapter configuration types must be fixed jointly rather than independently invented.

The ranking call takes **already enriched jobs and an already parsed/updated candidate**. It must not secretly re-ingest sources or generate repeated extraction calls on every UI refresh. Embeddings can be computed/retrieved by a small injected adapter and cached using model ID and content hash.

Errors are typed and actionable: unsupported PDF, extraction failure, schema validation failure, provider unavailable, missing embedding model, invalid clarification answer. Do not turn errors into plausible-looking recommendations. Partial success must identify skipped records.

## 7. Functional rules and AFU traceability

### Closed hard-constraint taxonomy - KICK-OFF DECISION

The MVP uses a **closed, versioned list of supported hard constraints**. The list is provisional until representative-job testing is complete; changes before freeze must be explicit and versioned. The runtime model may map explicit job language to an approved constraint ID and supporting evidence, but it may not invent a new hard gate or decide that an unusual formulation should exclude a candidate.

Initial constraint candidates to test:

| ID | Constraint family | Hard only when... | Missing/ambiguous handling |
|---|---|---|---|
| `HC_LOCATION` | Geographic availability / willingness | the job location and candidate restriction are sufficiently explicit | `unknown` when job country/location cannot be resolved |
| `HC_WORK_AUTH` | Work authorization / sponsorship compatibility | job/candidate declarations support a country-specific deterministic rule | `unknown`; citizenship alone is not automatically sufficient |
| `HC_STUDENT_STATUS` | Student / graduate status | the programme explicitly requires a defined status | `unknown` until explicit candidate status is available |
| `HC_GRAD_WINDOW` | Graduation date/window | the posting states a mandatory graduation window | `unknown` until candidate graduation date/window is known |
| `HC_DEGREE_LEVEL` | Degree level | the posting makes a level mandatory, not preferred | `unknown` on ambiguous wording/data |
| `HC_FIELD_OF_STUDY` | Field of study | the posting makes the field mandatory, not merely preferred | `unknown` on ambiguous wording/data |
| `HC_LANGUAGE` | Mandatory language | the posting states a required language/proficiency level clearly enough for the approved rule | `unknown` when candidate level or job level is unclear |
| `HC_MIN_EXPERIENCE` | Minimum prior experience | a numeric/clearly bounded minimum is explicitly mandatory and approved semantics exist | `unknown` rather than guessing equivalent experience |

Testing may remove, revise or add constraint families before rule freeze. Any new hard constraint requires explicit semantics, candidate input, job evidence mapping and expected test cases.

All other requirements are classified by GenAI into **fit/ranking** or **informational** categories. Preferred, optional, "nice to have" and similarly non-mandatory wording must not silently become a hard exclusion.

### Clarification behavior

When a supported opportunity cannot be assessed because a candidate field is missing, the system may create a structured `ClarificationRequest`. Prioritize questions that resolve a hard constraint or materially affect a high-priority opportunity. Do not ask free-form questions that have no predefined destination field.

The initial questionnaire should proactively collect persistent profile facts, including additional citizenships and country-specific work-authorization/sponsorship declarations. A clarification answer becomes a documented user input, updates the structured profile and reruns the deterministic engine. Do not infer legal status from proxies.

| ID | Required behavior | Minimum acceptance evidence |
|---|---|---|
| FR-01 | Extract text and semantic facts from the actual uploaded synthetic PDF | Changing a skill/fact in the file changes extracted facts; scanned/empty PDF receives a clear error |
| FR-02 | Show extracted facts and accept explicit user declarations/corrections | Corrected value is the one used by the engine, with provenance |
| FR-03 | Load normalized jobs and preserve source evidence/timestamps | A repeat snapshot gives the same records; updated time is not mislabeled as publication |
| FR-04 | Preserve eligible/ineligible/uncertain without inventing missing facts | Explicit approved conflict -> ineligible; unresolved evidence -> uncertain |
| FR-05 | Keep hard eligibility separate from scoring | High semantic fit cannot override an explicit hard conflict |
| FR-06 | Explain shortlist items with traceable evidence and score components | Source quote opens/matches; missing evidence triggers a warning, not an invented quote |
| FR-07 | Recompute after a relevant structured answer/constraint changes | Same jobs + changed candidate field produce the expected gate/ranking changes |
| FR-08 | Distinguish live extraction, cached output and synthetic fixtures | Mode/provenance remains visible during fallback |
| FR-09 | Use only session data for uploads and avoid secret leakage | No uploaded CV/secret appears in Git, persistent logs or shared cache |
| FR-10 | Support a reproducible evaluation and honest demo | Fixed snapshot/config IDs, recorded test commands and clearly labeled controlled events |
| FR-11 | Generate targeted clarification only for supported fields/rules | Missing relevant field -> question with approved destination field; unsupported question is rejected/omitted |
| FR-12 | Keep non-hard requirements from becoming hidden gates | Preferred/optional requirement may affect fit/information but cannot produce `explicit conflict` |

### Eligibility aggregation

For each clearly identified job location, assess all enabled approved hard rules. Within a location: any evidenced conflict means incompatible; otherwise any unresolved enabled rule means uncertain; otherwise compatible. Across alternative locations: at least one compatible location permits eligibility; otherwise any uncertain location makes the job uncertain; only all-known incompatible alternatives make it ineligible. With no usable location information, do not invent a country.

Closed or explicitly expired postings are excluded for availability, separately from eligibility. An unknown deadline does not imply expiry.

The UI should say **"Eligible under checked rules"**, **"Needs verification"** or **"Explicit conflict"**, and show unassessed requirements. These labels are not guarantees of legal eligibility or employer acceptance.

### Ranking - factor families confirmed; weights TO VALIDATE

First separate eligible from uncertain items; show both groups clearly. Within each group, order by the same priority score, then stable job ID for ties. Ineligible/closed/expired items are not filled into the Top 5 to make the list look complete.

Confirmed factor families:

| Factor | Definition for MVP |
|---|---|
| Profile fit | Semantic/structured fit across skills, education and experience; exact combination TO VALIDATE |
| Preference fit | Match against explicit candidate preferences such as location, role family and supported industry preferences |
| Deadline urgency | Higher urgency when a reliable explicit future application deadline is near; exact function TO VALIDATE |
| Freshness | Use only a defensible source publication time or clearly labeled discovery-time signal; exact function TO VALIDATE |

Exact weights are **not confirmed**. Treat them as explicit engineering heuristics: test on development examples, record changes and freeze before held-out evaluation. A missing factor is `null` and must not silently become zero; the missing-factor normalization rule is TO VALIDATE and then frozen.

For the initial snapshot, missing publication dates do not turn all jobs into fresh discoveries. A later first-seen time can support a **discovery freshness** factor, not a claim about posting age. Unexpected future timestamps are invalid/flagged.

Prefer concise explanations assembled from verified facts, rule outcomes, gaps and score components. If an LLM paraphrases them, it may not change status, score or evidence and must not introduce unsupported facts.

Do not include employer prestige, predicted hiring probability, subjective strategic career value or incomplete compensation data in the MVP ranking without a new explicit decision.

## 8. Technical implementation boundaries

Planned architecture/layout from the current design. Actual repository state must be verified before treating any path as implemented:

```text
app.py                         # Streamlit entry point and UI flow
src/oi/contracts.py            # shared: one model definition, both leads review
src/oi/io/                     # ATS, snapshots, PDF text extraction
src/oi/ui/                     # rendering and interaction, not duplicate business logic
src/oi/intelligence/           # extraction, clarification, eligibility, ranking, gaps/explanations
src/oi/providers/              # one chosen cloud runtime-model adapter
src/oi/evaluation/             # baselines, metrics, run manifests
config/                        # shared versions, source list, market/rule/ranking configuration
data/synthetic/                # reviewed synthetic personas and controlled scenarios
data/snapshots/                # reviewed public data, redistribution checked
prompts/                       # B: versioned runtime prompts, separate from agent instructions
tests/contracts/               # joint interface tests
tests/unit/                    # owned with the corresponding module
tests/integration/             # A/B integrated workflow tests
artifacts/evaluation/          # measured results and reproducibility manifests
```

Use a single agreed Python minor version; Python 3.12 remains a proposed compatibility baseline, not a latest-version claim. Actual library support must be checked on the development environments before the baseline is frozen. Use a virtual environment, a small dependency set and tested, pinned dependencies. Do not copy a global personal environment into the project. No Docker requirement for this MVP.

Candidate libraries to verify: Streamlit, Pydantic, pypdf, a simple HTTP client, sentence-transformers, pytest and Ruff. pypdf handles extraction from text-bearing PDFs but is not OCR [S12]. Sentence Transformers documents local embedding workflows [S13]. The chosen provider adds only its needed client dependency.

Exact setup/test/run commands belong to the verified repository documentation. Do not report commands as successful before they have been run. Use OS-neutral Python paths and document Mac/Windows environment activation differences when relevant.

## 9. Evaluation - design early, claim results only after measurement

The original proposal calls for three candidate profiles, 20-30 jobs per profile, embedding-only and generic-LLM baselines, and at least two human raters [P2]. Preserve that intent with a small, transparent protocol updated for the clarification loop and broader hard-constraint taxonomy.

### Dataset and ground truth

Use development fixtures to build/tune. Separately freeze three evaluation personas and a **20-30 unique job pool** that can be evaluated for all three personas. Report unique jobs and candidate-job pairs separately. The larger development/demo snapshot can target roughly 40-60 relevant unique postings.

Record snapshot ID, job IDs, persona version, source dates, rule catalogue version, ranking configuration, prompt/model IDs and evaluation clock. Keep controlled synthetic edge cases separate from real-posting evaluation and label them in every table.

Use the independent team raters assigned in `TEAM_MEMBER_STARTER_GUIDES.md`. They are team members, not external unbiased experts. Give each rater the same CV/profile declarations and job evidence, hide system identity/scores as far as practical, and require independent ratings **before discussing differences**. Disclose the small sample and team-member-rater limitation.

For the frozen set, obtain factual hard-constraint labels plus a simple 0-3 application-priority rating. Define the scale before viewing system outputs. Create each rater's Top 5 with a documented tie rule. Do not use the hybrid system's own labels as truth.

For clarification cases, record whether a question was actually needed, whether it targeted the correct supported field, whether the structured answer changed the expected downstream status/ranking, and whether an unnecessary/redundant question was asked. Do not claim a separate aggregate metric until the protocol defines one.

### Comparable systems

1. **Embedding-only:** same allowed candidate/job information converted to text; cosine-based ranking, no hidden eligibility filter.
2. **Generic LLM:** same candidate/job information and prioritization task; no access to the hybrid system's outputs or human labels. Record prompt/model, ordering and context/truncation limits.
3. **Hybrid system:** implemented extraction/profiling/clarification/gating/ranking pipeline.

All systems use the same frozen job universe, preferences and observation time. Their differences must be described. Where possible, use the chosen runtime model for both LLM-based systems so a model change is not an unexplained confound. Record failures and retries; do not keep only favorable runs.

### Minimum metrics

| Metric | Definition / safeguard |
|---|---|
| Explicit constraint violations in Top 5 | Human-labeled explicit-conflict recommendations / actual displayed recommendations. Empty output = N/A, not 0% success. Also show counts and list coverage. |
| Top-5 agreement | Size of intersection between system and each human Top 5 / 5. Missing recommendations are not silently removed from the denominator. Explain ties and rater differences. |
| Evidence support rate | Human-supported factual claims / audited factual claims. Report audited count, missing explanations and quote-match checks separately. Lexical quote presence alone is not semantic support. |
| Output coverage and unknown rate | Number of recommendations returned; eligible/uncertain/excluded counts; data/model failures |
| Duplicate rate | Remaining duplicates under the declared rule / evaluated records; preserve distinct positions |
| Clarification audit | Count needed vs unnecessary questions, supported target fields, and expected downstream resolution; keep this descriptive unless a formal metric is frozen |

Measure extraction quality too: compare selected extracted fields to known synthetic CV facts and show at least one error or limitation when observed. For latency, distinguish live inference, cache retrieval, UI reranking and controlled source refresh. Do not call a scripted event real-world detection latency.

A zero explicit-violation rate is a **target**, never a pre-filled result. Report counts, denominators and limitations; the sample cannot establish population-wide improvements or hiring success.

## 10. Security, integrity and final acceptance

Treat source documents as data, even when they contain commands such as "ignore previous instructions". Runtime extraction has no browser, shell, application-submission or secret-reading tools. Validate structured outputs before they become facts; render untrusted strings safely.

Use only public job information and explicitly synthetic candidate documents. Do not accept real CVs, confidential client/ACN material or unnecessary personal data into the shared workflow. Secrets stay outside Git and shared logs. A free hosted provider may have different data-use terms; verify those terms before transmission [S7].

Before marking the MVP ready, demonstrate:

- The same reviewed commit starts on the presentation laptop and backup environment.
- A changed synthetic PDF produces changed extracted content, with honest mode provenance.
- Explicit conflict, missing evidence, multi-location uncertainty and user correction follow the frozen rules.
- A high semantic score cannot bypass the gate; fewer-than-five output remains truthful.
- Public-source dates, controlled events and cached results are not misrepresented.
- An API/model failure produces a visible error or disclosed fallback, not fabricated results.
- Relevant tests and at least one end-to-end run have recorded evidence.
- Evaluation and AFU/report claims correspond to the same versioned implementation.

After freeze, fix defects and improve clarity. Any further feature must justify its cost against evaluation, recording and rehearsal time, with both leads' agreement.

## 11. Decision register

This register prevents a suggestion in one conversation from becoming an undocumented requirement for everyone else. Keep decisions short. Approval must identify the human approver and date; agents cannot approve on their behalf.

### Confirmed project decisions before this revision

| ID | Decision / fact |
|---|---|
| D-001 | Current group membership and member assignments are maintained only in `TEAM_MEMBER_STARTER_GUIDES.md`. |
| D-002 | Coding/chat execution responsibilities are maintained only in `TEAM_MEMBER_STARTER_GUIDES.md`; the project supports both repository and chat-only contribution paths. |
| D-003 | The project uses one shared current-state context. Operational output/handoff formats are maintained in `TEAM_MEMBER_STARTER_GUIDES.md` and `SESSION_LOGS.md`, not duplicated here. |
| D-004 | Visible extraction from an uploaded synthetic CV is essential. Predefined personas are also required; they do not replace extraction. |
| D-005 | Prefer a smaller, robust core with credible evaluation over broad, fragile functionality. Aim for a high course result. |
| D-006 | The two coding leads named in `TEAM_MEMBER_STARTER_GUIDES.md` jointly approve shared schema, interface and core-rule changes. |
| D-007 | Prefer zero additional spend. No runtime API access has been established. A paid option requires an explicit new decision. |
| D-008 | Report and demo/presentation are due 29 September 2026. Member availability and scheduling assumptions are maintained in `TEAM_MEMBER_STARTER_GUIDES.md`. |
| D-009 | Use a few selected skills rather than a large plugin/tool installation. |
| D-010 | The technical documentation should include an AFU-lite functional specification based on the agreed structure; this is not the entire technical report. |
| D-011 | Chat-only participation must be fully supported; non-coding contributors are not required to use GitHub/VS Code or install skills. |

### Kick-off decisions recorded 17 September 2026

These decisions were provided in the kick-off discussion and are integrated into this draft. Where they alter shared contracts or core rules, the approvals required by project governance must be recorded before the relevant contract version is treated as accepted.

| ID | Decision | Status |
|---|---|---|
| D-012 | Product direction is a broader career/application assistant MVP, not only an application-ranking tool; scope remains constrained by the 29 Sep deadline. | Recorded; shared-scope sign-off still required where governance applies |
| D-013 | Candidate target = students/recent graduates; internship and entry-level positions for the MVP. | Recorded |
| D-014 | Role scope = Business, Finance, Economics, Management and related commercial/managerial/financial roles; exclude STEM-specialist/legal/unrelated roles. | Recorded |
| D-015 | Target geographies = Italy, Spain, UK, France, Germany, Switzerland, Netherlands, Luxembourg, Denmark, Ireland, Shanghai, Shenzhen, Singapore and Hong Kong. Dataset coverage need not be exhaustive/balanced across all. | Recorded |
| D-016 | Product structure is eligibility-first, with urgency/freshness part of prioritisation; evidence remains required for material eligibility/explanation claims. | Recorded |
| D-017 | Hard constraints come from a closed predefined taxonomy that can be revised through testing before freeze; model may not invent hard gates. | Recorded; core-rule sign-off still required where governance applies |
| D-018 | Non-hard job requirements are classified by GenAI into fit/ranking or informational categories. | Recorded; rule semantics to validate |
| D-019 | GenAI handles semantic extraction, requirement classification, gap detection, clarification-question wording, explanations and optional career suggestions; deterministic code applies rules and ranking. | Recorded |
| D-020 | Initial profiling includes explicit additional-citizenship questioning; structured clarification questions fill supported missing candidate fields and trigger deterministic recomputation. | Recorded; exact contract fields to freeze |
| D-021 | Greenhouse is primary; Ashby/Lever are conditional on coverage evidence. Target ~40-60 development/demo jobs and 20-30 frozen evaluation jobs. | Recorded; source coverage TO VALIDATE |
| D-022 | Ranking factor families = profile fit, preference fit, deadline urgency and defensible freshness. Exact weights remain TO VALIDATE. | Recorded |
| D-023 | Main demo wow moment = a missing decision-relevant candidate fact triggers a targeted question; the structured answer changes eligibility and/or ranking visibly. | Recorded |
| D-024 | Cloud API is runtime-model strategy first; exact model/provider remains TO VALIDATE. | Recorded |
| D-025 | Current implementation ownership is maintained in `TEAM_MEMBER_STARTER_GUIDES.md`; product boundaries remain UI/intelligence vs data/input as defined in the shared contracts. | Recorded |
| D-026 | The data/input boundary supplies normalized jobs, source text/metadata and PDF-extracted CV input to the intelligence/UI boundary, which returns candidate profile, clarifications, eligibility, ranking, gaps/explanations and warnings. | Recorded; contract sign-off still required where governance applies |
| D-027 | Automatic job-specific CV tailoring/generation is backlog, not MVP. Strategic profile improvement suggestions are Nice to Have. | Recorded |
| D-028 | Session logging is required for substantive work; the current logging procedure and template live only in `SESSION_LOGS.md` and the operating instructions. | Recorded |


### Documentation architecture approved 18 September 2026

| ID | Decision | Status |
|---|---|---|
| D-029 | `PROJECT_CONTEXT.md` contains current project truth only: confirmed facts, approved project decisions, constraints, contracts, open questions and evaluation design. It no longer owns member assignments, response workflows, session templates or task scheduling. | Approved by Marco, 2026-09-18 |
| D-030 | The project master prompt governs ChatGPT behavior for all members and automatically applies the grill workflow to material proposals. | Approved by Marco, 2026-09-18 |
| D-031 | `TEAM_MEMBER_STARTER_GUIDES.md` is the official operating plan for roles, assigned tasks, priorities, deliverables, formats, deadlines, quality criteria, dependencies and handoff recipients. | Approved by Marco, 2026-09-18 |
| D-032 | `SESSION_LOGS.md` is the chronological evidence record for work actually performed and does not override current project truth or the current operating plan. | Approved by Marco, 2026-09-18 |
| D-033 | Execution is role-appropriate: repository/Git workflow is used only where relevant and authorized; chat-only/non-coding contributors deliver verifiable artifacts and handoffs without being forced into software-development mechanics. | Approved by Marco, 2026-09-18 |
| D-034 | Contract `0.2.0-draft` uses one shared strict Pydantic contract with forbidden extra fields; approved document kinds (`cv`, `job`, `questionnaire`, `ats_metadata`); extraction modes (`live`, `cache`, `fixture`); `JobRecord` namespaced IDs (`<source>:<source_job_id>`), primary `description` plus additional `source_documents`, quarantine for incomplete records; and the approved `RequirementFact`/`JobFacts` structure. `RequirementFact` is intelligence output only; deterministic rule outcomes remain separate. Final contract freeze is still pending CandidateProfile compatibility, final ClarificationRequest fields, and shared sample payloads. | Approved by Marco + Pierpaolo, 2026-09-18 |
| D-035 | The remaining `0.2.0-draft` candidate/clarification schema is jointly approved: `CandidateProfile` uses evidence-backed semantic fields, explicit preferences/declarations, `dict[constraint_id, list[EligibilityAnswer]]`, and resolvable candidate provenance; country/work-authorization semantics are explicit; `ClarificationRequest` uses closed answer/priority enums and validated `CandidateFieldPath` families. `answer_key` membership for a specific constraint remains a `RuleCatalogue` responsibility, not a shared-contract rule. Shared fixtures are fixed at `tests/fixtures/contracts/v0.2.0-draft/{candidate_profile,clarification_request,job_record}.json`. The Q-08 candidate/clarification schema decision is closed; its fixture verification condition was satisfied on 2026-09-20 by commit `03a208a`, with `121 passed` and 3/3 fixture round-trips. This decision freezes the models explicitly covered by D-034/D-035; it does not freeze `JobSnapshot` or downstream result/config envelopes. | Approved by Marco + Pierpaolo, 2026-09-20; verification condition satisfied 2026-09-20 |
| D-036 | The repository-root `PROJECT_CONTEXT.md` is the single editable canonical copy of current project truth. The ChatGPT Project Source copy is a convenience mirror and must be refreshed after approved changes; when versions differ, the repository-root copy governs until synchronization. This changes storage authority only and does not change the source-role separation established by D-029 to D-033. | Approved by Marco, 2026-09-20 |
| D-037 | `JobSnapshot 0.2.1-draft` is the jointly approved backward-compatible A/B snapshot envelope. It adds exact `SourceManifestEntry`, `QuarantineSummary` and `JobSnapshot` serialization around unchanged frozen `0.2.0-draft` `JobRecord` payloads; uses one UTF-8 JSON object; makes `documents` the canonical registry for every embedded job description/source document and top-level job evidence document reference; stores quarantine summary metadata only; and leaves RuleCatalogue/ranking semantics unchanged. A owns `load_snapshot(Path) -> JobSnapshot` and the text-only `PdfExtractionError`/`extract_pdf_text(pdf_bytes, document_id)` boundary; malformed, unusable encrypted and no-text PDFs raise `PdfExtractionError`, with no OCR. | Approved by Marco + Pierpaolo, 2026-09-20 |
| D-038 | Group A Greenhouse batch ingestion is partial-success. A configured posting that fails with an expected Greenhouse fetch or normalization failure is omitted from `jobs` and summarized through stable `JobSnapshot.quarantine` reasons, while other valid postings remain in the snapshot. Unexpected programming/contract failures propagate. | Approved by Marco, 2026-09-22 |
| D-039 | Group A Greenhouse batch snapshots use one `SourceManifestEntry` per successfully fetched-and-normalized posting, preserving the exact Greenhouse public API posting endpoint as `source_ref`, the batch observation time as `retrieved_at`, and `record_count=1`. Failed targets do not create successful manifest entries. | Approved by Marco, 2026-09-22 |

### Proposed implementation defaults - review/freeze before independent implementation

| ID | Proposal | Status |
|---|---|---|
| R-001 | Local Streamlit execution; public hosting not on the first-week critical path | Proposed |
| R-002 | Python 3.12 compatibility baseline, small verified dependency set and JSON-based local artifacts | Proposed environment baseline; `JobSnapshot` persistence is frozen separately as one UTF-8 JSON object by D-037 |
| R-003 | Core shared contract structures in section 6 implemented once in the shared contracts module | Core sections A-D are implemented and verified for `0.2.0-draft`; `JobSnapshot 0.2.1-draft` is jointly approved for A-01 implementation; result/config envelopes remain separately unfrozen |
| R-004 | Local sentence embeddings/direct cosine similarity; no vector DB | Proposed; exact model/version TO VALIDATE |
| R-005 | Closed taxonomy initial candidates listed in section 7 | Proposed set; test and freeze before evaluation |
| R-006 | Missing ranking factors remain null and are normalized/disclosed rather than silently scored zero | Proposed; exact normalization TO VALIDATE |
| R-007 | Three personas, 20-30 frozen jobs, independent team raters, comparable baselines | Proposed operationalization of original evaluation plan |

Accepting a baseline does not mean the corresponding behavior is implemented or tested. Keep status dimensions separate.

### Open decisions / TO VALIDATE

| ID | Question | Recommendation / next action |
|---|---|---|
| Q-01 | Which exact cloud runtime provider/model and access route? | Run a real structured extraction test; record model ID, access, latency, limitations, current quota/terms |
| Q-02 | Does Greenhouse provide enough relevant coverage? | Coverage test against agreed domain/geographies; add Ashby/Lever only if a material gap is demonstrated |
| Q-03 | What is the final hard-constraint list and exact semantics? | Test the section 7 candidates on representative postings; create truth-table cases; version/freeze |
| Q-04 | How should citizenship interact with work authorization/sponsorship? | Treat them separately by default; approve any country-specific inference only with explicit semantics/evidence |
| Q-05 | What are the ranking weights and missing-factor normalization? | Tune only on development examples; freeze before held-out evaluation |
| Q-06 | Which exact embedding model/version and dependency versions? | Select a small English model, verify license/download/performance, pin tested versions |
| Q-07 | Can the assigned independent team raters complete the frozen-set ratings? | Confirm availability in `TEAM_MEMBER_STARTER_GUIDES.md`; each rates before discussing disagreements |
| Q-08 | What exact serializable fields define candidate eligibility answers and `ClarificationRequest`, and do shared sample payloads prove A/B compatibility? | **Closed 2026-09-20 for the candidate/clarification core boundary.** Joint schema sign-off was followed by successful fixture and negative/reference verification (`121 passed`, commit `03a208a`). This closure does not approve `JobSnapshot` or downstream result/config envelope serialization. |
| Q-09 | What is the exact submission time and timezone? | Verify the official course platform; do not infer from this planning document |
| Q-10 | How will repository/video be accessible to the grader? | Ensure grader access, working links and redistribution permission for stored source text |
| Q-11 | What exact serializable fields define `JobSnapshot`, its source manifest and quarantine summary? | **Closed 2026-09-20.** Marco + Pierpaolo jointly approved `JobSnapshot 0.2.1-draft` under D-006/D-037, including the exact manifest/quarantine fields, canonical document-registry invariants, single-JSON persistence, A-owned loader, and text-only PDF error boundary. |

### Record a new decision

```text
ID and date:
Question / change:
Decision:
Why:
Affected contract/files/tests:
Approved by:
Status: proposed | approved | superseded
```

Record the actual human approver(s) required by the affected governance rule. Contract/core-rule changes still require the approvals specified by the current project governance. An unresolved choice can remain configurable while unrelated work proceeds on explicitly labeled fixtures. Never invent approval or silently resolve an open item in code.

## 12. Source register and verification limits

This register records sources that support project requirements, product/technical decisions and verification limits. It does not define assistant workflow or member assignments.

### User-provided project sources

**[P1] Project guidelines.pdf** - supplied by the team.
- Pages 2, 5-7: presentation timing, live demo, backup and Q&A roles.
- Pages 3-5: report/walkthrough deliverables, report structure/format, five 20-point grading areas and AI-writing disclosure.
- No deployment mandate, final submission clock/timezone or video-duration requirement was inferred where the file did not specify one.

**[P2] Job_applicable_ai_Project_Proposal_Revised.docx** - supplied by the team.
- Page 1: problem, students/recent graduates, hybrid architecture, three-ATS source plan, proposed stack and credentials.
- Page 2: pipeline, hard constraints, evaluation profiles/baselines, source freshness and demo concept.
- The runtime model named in that document is not assumed available, affordable or selected. The team has since requested a free-first runtime decision and a smaller scope.

**[P3] Team decisions in the project conversation, 17 September 2026.**
Confirmed earlier team decisions plus the 17 September kick-off discussion on product direction, market, broader eligibility taxonomy, cloud-first runtime strategy, clarification loop, ranking factors, source strategy and UI ownership. See the decision register above for current status and remaining validation items.

**[P4] Joint A-01 shared-contract sign-off in the project conversation, 20 September 2026.**
Marco approved A-01 Q1-Q5, including the `0.2.1-draft` version boundary. Pierpaolo then explicitly approved the same `JobSnapshot 0.2.1-draft` envelope and its normative registry, manifest/quarantine, loader and text-only PDF constraints under D-006.

The public sources below support technical assumptions, not claims about the project's implementation or measured results.

### Technical reference catalogue - recheck when used

| ID | Reference | Supports | URL |
|---|---|---|---|
| S7 | Google, Gemini API pricing | Conditional free tiers and data-use distinction | `https://ai.google.dev/gemini-api/docs/pricing` |
| S8 | Google, Rate limits; available regions | Account/model quota and regional access checks | `https://ai.google.dev/gemini-api/docs/rate-limits` ; `https://ai.google.dev/gemini-api/docs/available-regions` |
| S9 | Ollama, Structured Outputs | Local structured-output option | `https://docs.ollama.com/capabilities/structured-outputs` |
| S10 | Google, Structured outputs | Schema constraints and semantic validation limits | `https://ai.google.dev/gemini-api/docs/structured-output` |
| S11 | Greenhouse, Job Board API | Public GET access and source fields such as updated_at | `https://docs.greenhouse.io/job-board.html` |
| S12 | pypdf, Extract Text from a PDF | Text-bearing PDF extraction and OCR limitations | `https://pypdf.readthedocs.io/en/stable/user/extract-text.html` |
| S13 | Sentence Transformers, Quickstart | Local embeddings workflow | `https://sbert.net/docs/quickstart.html` |

### Verification limits

No runtime provider login, billing, endpoint dataset collection, application execution, browser demo or academic evaluation is established merely by this document. Current implementation/progress claims require evidence in the repository and/or `SESSION_LOGS.md`.

**END OF PROJECT CONTEXT - v0.4.5-draft.**
