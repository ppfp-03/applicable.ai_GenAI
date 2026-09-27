"""The OI-50 synthetic job catalogue and its generator (oi.io.synthetic_workbook).

The workbook itself is not in the repository, so the committed artifacts are
checked as they are, and the conversion rules are checked on inline rows.
"""

from __future__ import annotations

import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from pathlib import Path

import pytest

from oi.contracts import CandidateProfile, JobSnapshot, quote_occurs_in
from oi.intelligence.eligibility import assess_eligibility, load_rule_catalogue
from oi.intelligence.ranking_adapter import rank_with_eligibility
from oi.io import synthetic_workbook as sw
from oi.io.snapshot import load_snapshot
from oi.io.synthetic_catalogue import get_synthetic_catalogue

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "snapshots" / "synthetic_oi50.json"
IDS = [f"SYN-JOB-{i:03d}" for i in range(1, 51)]
DEADLINES = {
    "SYN-JOB-003": datetime(2026, 11, 8, 23, 59, tzinfo=timezone.utc),   # London, GMT
    "SYN-JOB-004": datetime(2027, 4, 30, 15, 59, tzinfo=timezone.utc),  # Hong Kong, UTC+8
    "SYN-JOB-016": datetime(2026, 12, 11, 23, 59, tzinfo=timezone.utc),  # London, GMT
    "SYN-JOB-024": datetime(2026, 10, 18, 22, 59, tzinfo=timezone.utc),  # London, BST
}
#: Synthetic rows whose audit source is a posting also in greenhouse_batch01.
RELABELLED_REAL = ["SYN-JOB-001", "SYN-JOB-002", "SYN-JOB-003", "SYN-JOB-004",
                   "SYN-JOB-005", "SYN-JOB-006", "SYN-JOB-010", "SYN-JOB-012"]


@pytest.fixture(scope="module")
def snapshot() -> JobSnapshot:
    return get_synthetic_catalogue()


@pytest.fixture(scope="module")
def jobs(snapshot):
    return {job.source_job_id: job for job in snapshot.jobs}


def cells(job) -> dict[str, str]:
    """The workbook cells recorded in a job's synthetic document."""
    out, current = {}, None
    for line in job.description.text.splitlines():
        head = next((c for c in sw.COLUMNS if line.startswith(f"{c}: ")), None)
        if head:
            current, out[head] = head, line[len(head) + 2:]
        elif current:
            out[current] += "\n" + line
    return out


# --- The artifact --------------------------------------------------------------


def test_the_catalogue_loads_as_a_job_snapshot(snapshot):
    assert isinstance(snapshot, JobSnapshot)
    assert snapshot.schema_version == "0.2.1-draft"
    assert snapshot.snapshot_id == "synthetic-oi50"
    assert snapshot == load_snapshot(SNAPSHOT)


def test_exactly_fifty_unique_synthetic_ids_in_order(snapshot):
    assert len(snapshot.jobs) == 50
    assert [j.job_id for j in snapshot.jobs] == [f"synthetic:{i}" for i in IDS]
    assert len({j.job_id for j in snapshot.jobs}) == 50


def test_every_job_is_labelled_synthetic_with_a_placeholder_url(snapshot):
    for job in snapshot.jobs:
        assert job.source == "synthetic"
        assert job.url == f"https://example.invalid/synthetic/{job.source_job_id}"
        assert job.description.source_ref == f"OI_50_synthetic_job_profiles.xlsx#Synthetic Profiles!{job.source_job_id}"
    [entry] = snapshot.source_manifest
    assert (entry.source, entry.record_count) == ("synthetic", 50)


def test_every_job_is_active_undated_and_seen_once(snapshot):
    for job in snapshot.jobs:
        assert job.active_state.value == "active"
        assert job.source_published_at is None and job.source_updated_at is None
        assert job.discovery_kind.value == "initial_snapshot"
        assert job.first_seen_at == job.last_seen_at == sw.CATALOGUE_TIMESTAMP
        assert job.extraction is None
    assert snapshot.created_at == sw.CATALOGUE_TIMESTAMP


def test_nothing_is_invented_for_ranking(snapshot):
    for job in snapshot.jobs:
        assert job.facts.role_family is None
        assert job.facts.skills == job.facts.experience == job.facts.education == []


def test_every_quote_is_contained_in_its_own_document(snapshot):
    for job in snapshot.jobs:
        for ref in job.evidence:
            assert ref.document_id == job.description.document_id
            assert quote_occurs_in(ref.quote, job.description.text)
        quotes = {ref.evidence_id: ref.quote for ref in job.evidence}
        for req in job.facts.requirements:
            assert [quotes[e] for e in req.evidence_ids] == [req.text]


# --- Audit URLs ---------------------------------------------------------------


def test_the_snapshot_holds_no_url_but_its_placeholders():
    text = SNAPSHOT.read_text(encoding="utf-8")
    urls = re.findall(r"https?://[^\s\"]+", text)
    assert len(urls) == 50
    assert all(u.startswith("https://example.invalid/synthetic/SYN-JOB-") for u in urls)
    for host in ("greenhouse.io", "lever.co", "ashbyhq.com", "Source URL"):
        assert host not in text


def test_no_audit_mapping_is_committed_or_loaded():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert not [f for f in tracked.splitlines() if "audit" in f.lower() and f.endswith(".json")]
    assert not [f for f in tracked.splitlines() if f.endswith(".xlsx")]
    app_code = [p for folder in ("src", "core", "views", "ui") for p in (ROOT / folder).rglob("*.py")] + [ROOT / "app.py"]
    mentions = [p for p in app_code if re.search(r"audit_mapping|audit_urls|Source URL \(audit only\)", p.read_text(encoding="utf-8"))]
    assert mentions == [ROOT / "src" / "oi" / "io" / "synthetic_workbook.py"]
    assert "audit" not in (ROOT / "src" / "oi" / "io" / "synthetic_catalogue.py").read_text(encoding="utf-8").lower()


def write_workbook(path: Path, rows: list[dict]) -> Path:
    """A minimal .xlsx with the workbook's header and `rows`, inline strings only."""
    def cell(ref: str, value: str) -> str:
        return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>'

    def col(i: int) -> str:
        return chr(65 + i)

    grid = [list(sw.COLUMNS)] + [[row.get(c) or "" for c in sw.COLUMNS] for row in rows]
    sheet_rows = "".join(
        f'<row r="{r + 1}">' + "".join(cell(f"{col(i)}{r + 1}", v) for i, v in enumerate(values) if v) + "</row>"
        for r, values in enumerate(grid)
    )
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", f'<workbook xmlns="{main}" xmlns:r="{rel}"><sheets>'
                         f'<sheet name="{sw.SHEET_NAME}" sheetId="1" r:id="rId1"/></sheets></workbook>')
        archive.writestr("xl/_rels/workbook.xml.rels",
                         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                         '<Relationship Id="rId1" Target="/xl/worksheets/sheet1.xml"/></Relationships>')
        archive.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{main}"><sheetData>{sheet_rows}</sheetData></worksheet>')
    return path


ROW = {c: None for c in sw.COLUMNS} | {
    "Profile ID": "SYN-JOB-001", "Company": "Example Co", "Job title": "Analyst Intern",
    "Locations": "Paris, France", "Application open": "Yes", "Deadline / start period": "8 Nov 2026",
    "Hard - Language": "• French: fluent.", "Non-hard requirements": "• Excel preferred.",
    sw.AUDIT_COLUMN: "https://job-boards.greenhouse.io/example/jobs/123",
}


def test_generation_needs_no_audit_output(tmp_path):
    workbook = write_workbook(tmp_path / "book.xlsx", [ROW])
    out = tmp_path / "catalogue.json"
    assert sw.main(["--workbook", str(workbook), "--output", str(out)]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["book.xlsx", "catalogue.json"]
    snapshot = load_snapshot(out)
    assert [j.job_id for j in snapshot.jobs] == ["synthetic:SYN-JOB-001"]
    assert "greenhouse.io" not in out.read_text(encoding="utf-8")


def test_the_optional_audit_mapping_is_a_local_output_only(tmp_path):
    workbook = write_workbook(tmp_path / "book.xlsx", [ROW])
    out, audit = tmp_path / "catalogue.json", tmp_path / "local" / "audit.json"
    audit.parent.mkdir()
    assert sw.main(["--workbook", str(workbook), "--output", str(out), "--audit", str(audit)]) == 0
    assert json.loads(audit.read_text())["audit_urls"] == {"synthetic:SYN-JOB-001": ROW[sw.AUDIT_COLUMN]}
    assert "greenhouse.io" not in out.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="outside the repository"):
        sw.main(["--workbook", str(workbook), "--output", str(out),
                 "--audit", str(ROOT / "data" / "snapshots" / "audit.json")])
    assert not (ROOT / "data" / "snapshots" / "audit.json").exists()


# --- Deadlines ------------------------------------------------------------------


def test_exactly_the_four_explicit_deadlines(jobs):
    assert {k: j.deadline_at for k, j in jobs.items() if j.deadline_at} == DEADLINES


def test_rolling_start_and_programme_text_never_becomes_a_deadline(jobs):
    for key, job in jobs.items():
        if key in DEADLINES:
            continue
        stated = cells(job)["Deadline / start period"]
        assert job.deadline_at is None, (key, stated)
    for text in ["Rolling basis", "- | Start: 29 Jun 2027 (10 weeks)", "- | Programme: Jan-May 2027",
                 "Rolling basis | Start: Jan 2027 onward (6 months)", "- | Start: not stated",
                 "Summer to mid-fall (second application window; exact date not stated)", None]:
        assert sw.parse_deadline(text, [("London", "GB")]) is None


def test_a_deadline_is_23_59_local_or_utc_across_time_zones():
    assert sw.parse_deadline("18 Oct 2026", [("London", "GB")]) == datetime(2026, 10, 18, 22, 59, tzinfo=timezone.utc)
    assert sw.parse_deadline("30 Apr 2027", [("Hong Kong", "HK")]) == datetime(2027, 4, 30, 15, 59, tzinfo=timezone.utc)
    utc = datetime(2026, 11, 8, 23, 59, tzinfo=timezone.utc)
    assert sw.parse_deadline("8 Nov 2026", [("London", "GB"), ("Singapore", "SG")]) == utc
    assert sw.parse_deadline("8 Nov 2026", [("Somewhere", None)]) == utc


# --- Locations ----------------------------------------------------------------


def test_country_codes_come_only_from_the_approved_markets(snapshot):
    markets = sw.load_market_names()
    for job in snapshot.jobs:
        assert job.locations
        for loc in job.locations:
            assert loc.country_code in markets.values()


def test_location_parsing_rules():
    markets = sw.load_market_names()
    assert sw.parse_locations("London, England, United Kingdom", markets) == [("London", "GB")]
    assert sw.parse_locations("Hong Kong, Hong Kong", markets) == [("Hong Kong", "HK")]
    assert sw.parse_locations("Singapore", markets) == [("Singapore", "SG")]
    assert sw.parse_locations("Zurich, Switzerland; Berlin, Germany; Munich, Germany", markets) == [
        ("Zurich", "CH"), ("Berlin", "DE"), ("Munich", "DE")]
    assert sw.parse_locations("London, United Kingdom; Dublin, Ireland (subsequent openings)", markets) == [
        ("London", "GB")]
    assert sw.parse_locations("Lisbon, Portugal", markets) == [("Lisbon", None)]  # no invented mapping
    with pytest.raises(ValueError):
        sw.parse_locations("Paris, France (remote possible)", markets)


def test_multi_location_rows(jobs):
    assert [(l.city, l.country_code) for l in jobs["SYN-JOB-008"].locations] == [
        ("Zurich", "CH"), ("Berlin", "DE"), ("Munich", "DE")]
    assert [(l.city, l.country_code) for l in jobs["SYN-JOB-016"].locations] == [("London", "GB")]
    assert "Dublin, Ireland (subsequent openings)" in jobs["SYN-JOB-016"].description.text


# --- Requirements -------------------------------------------------------------


def test_missing_hard_cells_create_no_requirement(jobs):
    for key, job in jobs.items():
        stated = cells(job)
        for column, constraint in sw.HARD_COLUMNS.items():
            texts = [r.text for r in job.facts.requirements]
            if column not in stated:
                assert not [r for r in job.facts.requirements if constraint and r.constraint_id == constraint], (key, column)
            else:
                assert any(t in stated[column] for t in texts), (key, column)


def test_every_stated_hard_cell_is_a_mandatory_gate_unless_it_says_otherwise(jobs):
    for key, job in jobs.items():
        for column, constraint in sw.HARD_COLUMNS.items():
            cell = cells(job).get(column)
            if not cell or constraint is None:
                continue
            reqs = [r for r in job.facts.requirements if r.text in cell]
            if "not stated" in cell.lower() or "prefer" in cell.lower():
                assert all(r.constraint_id is None for r in reqs), (key, column)
            else:
                assert reqs and all(
                    (r.classification.value, r.modality.value, r.constraint_id) == ("hard_constraint", "mandatory", constraint)
                    for r in reqs
                ), (key, column)


def test_syn_048_work_authorization_is_not_a_gate(jobs):
    job = jobs["SYN-JOB-048"]
    assert not [r for r in job.facts.requirements if r.constraint_id == "HC_WORK_AUTH"]
    [info] = [r for r in job.facts.requirements if "work-authorisation requirement not stated" in r.text]
    assert (info.classification.value, info.modality.value) == ("informational", "unspecified")


def test_syn_050_experience_stays_non_hard(jobs):
    job = jobs["SYN-JOB-050"]
    assert not [r for r in job.facts.requirements if r.constraint_id == "HC_MIN_EXPERIENCE"]
    [pref] = [r for r in job.facts.requirements if "rather than a hard gate" in r.text]
    assert (pref.classification.value, pref.modality.value, pref.constraint_id) == ("fit", "preferred", None)


def test_non_hard_requirements_are_never_hard(jobs):
    for job in jobs.values():
        non_hard = cells(job)["Non-hard requirements"]
        for req in job.facts.requirements:
            if req.text in non_hard and not any(req.text in (cells(job).get(c) or "") for c in sw.HARD_COLUMNS):
                assert req.classification.value == "fit" and req.constraint_id is None


def test_one_language_requirement_per_language(jobs):
    texts = [r.text for r in jobs["SYN-JOB-007"].facts.requirements if r.constraint_id == "HC_LANGUAGE"]
    assert texts == ["• German: C1.", "• English: fluent."]


def test_truncated_text_is_kept_exactly(snapshot):
    truncated = [r for j in snapshot.jobs for r in j.facts.requirements if r.text.endswith("...")]
    assert truncated
    for job in snapshot.jobs:
        for req in job.facts.requirements:
            if req.text.endswith("..."):
                assert req.text in job.description.text


def test_the_relabelled_real_rows_stay_in_the_catalogue(jobs):
    for key in RELABELLED_REAL:
        assert key in jobs and jobs[key].source == "synthetic"


def test_a_row_converts_the_same_way_twice():
    row = {c: None for c in sw.COLUMNS} | {
        "Profile ID": "SYN-JOB-999", "Company": "Example Co", "Job title": "Analyst Intern",
        "Locations": "Paris, France", "Application open": "Yes", "Deadline / start period": "Rolling basis",
        "Hard - Language": "• French: fluent.\n• English: fluent.", "Non-hard requirements": "• Excel preferred.",
        sw.AUDIT_COLUMN: "https://example.org/audit",
    }
    markets = sw.load_market_names()
    first, second = sw.convert_row(row, markets), sw.convert_row(row, markets)
    assert first == second
    assert "https://example.org/audit" not in first.model_dump_json()
    assert [(r.constraint_id, r.modality.value) for r in first.facts.requirements] == [
        ("HC_LANGUAGE", "mandatory"), ("HC_LANGUAGE", "mandatory"), (None, "preferred")]


# --- Through eligibility and ranking -------------------------------------------


def test_the_catalogue_runs_through_eligibility_and_ranking(snapshot):
    candidate = CandidateProfile.model_validate(
        json.loads((ROOT / "tests" / "fixtures" / "contracts" / "v0.2.0-draft" / "candidate_profile.json").read_text()))
    catalogue = load_rule_catalogue()
    results = [assess_eligibility(candidate, job, catalogue) for job in snapshot.jobs]
    # Unparameterized requirements are never a conflict: only the candidate's
    # own country perimeter (HC_LOCATION) can exclude a job here.
    conflicts = {o.rule_id for r in results for o in r.outcomes if o.status.value == "conflict"}
    assert conflicts <= {"HC_LOCATION"}
    ranked = rank_with_eligibility(
        candidate, snapshot.jobs, results,
        weights={"profile_fit": 0.40, "preference_fit": 0.25, "deadline_urgency": 0.20, "freshness": 0.15},
        now=datetime(2026, 9, 27, 12, tzinfo=timezone.utc), deadline_horizon_days=30, freshness_horizon_days=30,
    )
    groups = ranked.pipeline.eligible, ranked.pipeline.uncertain
    entries = [e for g in groups for e in (*g.top, *g.rest, *g.unscored)]
    assert all(len(g.top) <= 5 for g in groups)
    assert len(entries) + len(ranked.pipeline.excluded) == 50
    for entry in entries:
        assert entry.breakdown.factors["profile_fit"] is None
        assert entry.breakdown.factors["freshness"] is None
