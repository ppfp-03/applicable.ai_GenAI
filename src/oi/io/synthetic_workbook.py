"""Convert the OI-50 synthetic job workbook into a canonical JobSnapshot.

Generation only: this runs once, by hand, and writes two committed files.
Nothing in the app imports it, and the workbook is never read at runtime.

    python -m oi.io.synthetic_workbook --workbook OI_50_synthetic_job_profiles.xlsx
    python -m oi.io.synthetic_workbook --workbook ... --audit ~/oi50_audit.json

It writes ``data/snapshots/synthetic_oi50.json``: the catalogue as a
``JobSnapshot`` (0.2.1-draft), loaded by ``oi.io.synthetic_catalogue``. The
catalogue holds no audit URL anywhere.

The workbook's "Source URL (audit only)" column stays local: only when asked
with ``--audit`` does this write a job -> URL mapping, and only to a path
outside the repository. Neither the workbook nor that mapping is committed,
and nothing in the app loads either.

The conversion is deterministic and invents nothing:

- every job is ``source="synthetic"`` with the ID ``synthetic:SYN-JOB-NNN``,
  a non-routable placeholder ``url``, and a ``SourceDocument`` holding the
  row's own text (``source_ref`` names the workbook row, never a URL);
- country codes come only from the approved names in ``config/markets.json``;
  a location marked for subsequent openings is not a current location;
- ``deadline_at`` is set only when the cell is exactly one calendar date,
  at 23:59 local time of the primary current location (UTC when the current
  locations span time zones or have no country);
- publication and update times stay null; ``first_seen_at`` and
  ``last_seen_at`` are the one fixed ``CATALOGUE_TIMESTAMP``;
- each hard column becomes a mandatory hard requirement for its catalogue
  constraint, with no rule parameters: those are left to the eligibility
  owner. A hard cell whose own wording says it is not a gate ("not stated",
  "preferred") becomes a non-hard requirement instead;
- non-hard requirements become ``fit`` requirements, ``preferred`` only when
  their text says so;
- cell text is kept exactly as written, including text the workbook itself
  truncates with "..."; nothing is reconstructed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Sequence
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

from oi.contracts import (
    ActiveState,
    DiscoveryKind,
    DocumentKind,
    EvidenceRef,
    JobFacts,
    JobLocation,
    JobRecord,
    JobSnapshot,
    RequirementClassification,
    RequirementFact,
    RequirementModality,
    SourceDocument,
    SourceManifestEntry,
)

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_PATH = ROOT / "data" / "snapshots" / "synthetic_oi50.json"
MARKETS_PATH = ROOT / "config" / "markets.json"

#: The one fixed timestamp of this catalogue: snapshot creation, manifest
#: retrieval and every job's first/last seen time. Never the system clock.
CATALOGUE_TIMESTAMP = datetime(2026, 9, 27, 0, 0, tzinfo=timezone.utc)

SOURCE = "synthetic"
SNAPSHOT_ID = "synthetic-oi50"
WORKBOOK_NAME = "OI_50_synthetic_job_profiles.xlsx"
SHEET_NAME = "Synthetic Profiles"
PLACEHOLDER_URL = "https://example.invalid/synthetic/{profile_id}"

AUDIT_COLUMN = "Source URL (audit only)"
COLUMNS = (
    "Profile ID",
    "Company",
    "Job title",
    "Locations",
    "Application open",
    "Deadline / start period",
    "Hard - Location",
    "Hard - Work authorization",
    "Hard - Student/graduate status",
    "Hard - Graduation window",
    "Hard - Degree level",
    "Hard - Field of study",
    "Hard - Language",
    "Hard - Experience range",
    "Non-hard requirements",
    AUDIT_COLUMN,
)

#: Hard columns and the catalogue constraint each one states. "Hard -
#: Location" has none: HC_LOCATION is decided from `locations`, so its text
#: (office days, on-site) is kept as information.
HARD_COLUMNS = {
    "Hard - Location": None,
    "Hard - Work authorization": "HC_WORK_AUTH",
    "Hard - Student/graduate status": "HC_STUDENT_STATUS",
    "Hard - Graduation window": "HC_GRAD_WINDOW",
    "Hard - Degree level": "HC_DEGREE_LEVEL",
    "Hard - Field of study": "HC_FIELD_OF_STUDY",
    "Hard - Language": "HC_LANGUAGE",
    "Hard - Experience range": "HC_MIN_EXPERIENCE",
}
#: A hard cell saying this about itself is not a gate.
NOT_STATED = "not stated"
PREFERRED = "prefer"

#: IANA time zone of each platform country, for the 23:59 deadline rule.
COUNTRY_TIMEZONES = {
    "IT": "Europe/Rome",
    "ES": "Europe/Madrid",
    "FR": "Europe/Paris",
    "DE": "Europe/Berlin",
    "NL": "Europe/Amsterdam",
    "LU": "Europe/Luxembourg",
    "DK": "Europe/Copenhagen",
    "IE": "Europe/Dublin",
    "GB": "Europe/London",
    "CH": "Europe/Zurich",
    "CN": "Asia/Shanghai",
    "HK": "Asia/Hong_Kong",
    "SG": "Asia/Singapore",
}
DEADLINE_TIME = time(23, 59)
_DATE = re.compile(r"(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4})")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
#: Parenthetical location wording that marks a place as not current.
_FUTURE_LOCATION = "subsequent"


# --- Workbook reading (standard library only) --------------------------------

_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _column_index(ref: str) -> int:
    index = 0
    for letter in re.match(r"[A-Z]+", ref).group(0):
        index = index * 26 + ord(letter) - 64
    return index - 1


def read_rows(workbook: Path, sheet: str = SHEET_NAME) -> list[dict[str, str | None]]:
    """The sheet's data rows as {column: text}, empty cells as None.

    Raises:
        ValueError: If the sheet is missing or its header is not `COLUMNS`.
    """
    with zipfile.ZipFile(workbook) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("m:si", _NS):
                shared.append("".join(t.text or "" for t in item.iter(f"{{{_NS['m']}}}t")))
        book = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {rel.get("Id"): rel.get("Target") for rel in rels}
        sheets = {s.get("name"): s.get(f"{{{_NS['r']}}}id") for s in book.find("m:sheets", _NS)}
        if sheet not in sheets:
            raise ValueError(f"Workbook has no sheet {sheet!r}; found {sorted(sheets)}.")
        target = targets[sheets[sheet]].lstrip("/")
        target = target if target.startswith("xl/") else f"xl/{target}"
        grid: list[list[str | None]] = []
        for row in ElementTree.fromstring(archive.read(target)).iter(f"{{{_NS['m']}}}row"):
            cells: dict[int, str | None] = {}
            for cell in row.findall("m:c", _NS):
                value, kind = cell.find("m:v", _NS), cell.get("t")
                if kind == "inlineStr":
                    text = "".join(t.text or "" for t in cell.iter(f"{{{_NS['m']}}}t"))
                elif value is None:
                    text = None
                elif kind == "s":
                    text = shared[int(value.text)]
                else:
                    text = value.text
                cells[_column_index(cell.get("r"))] = text
            if cells:
                grid.append([cells.get(i) for i in range(max(cells) + 1)])
    header, *data = grid
    if tuple(header) != COLUMNS:
        raise ValueError(f"Unexpected header: {header}")
    return [
        {name: (row[i] if i < len(row) and (row[i] or "").strip() else None) for i, name in enumerate(COLUMNS)}
        for row in data
    ]


# --- Row conversion ------------------------------------------------------------


def load_market_names(path: Path = MARKETS_PATH) -> dict[str, str]:
    """Approved country name -> ISO code, from config/markets.json."""
    return {c["name"]: c["code"] for c in json.loads(path.read_text(encoding="utf-8"))["countries"]}


def parse_locations(text: str, markets: dict[str, str]) -> list[tuple[str, str | None]]:
    """Current locations as (city, country code or None), in source order.

    Places are ";"-separated, each "City[, Region], Country" or a single name.
    A place qualified as a subsequent opening is not current. A country name
    outside `markets` stays None: no mapping is invented.

    Raises:
        ValueError: On a parenthetical qualifier this rule does not cover.
    """
    current = []
    for place in (p.strip() for p in text.split(";")):
        qualified = re.fullmatch(r"(.*?)\s*\(([^)]*)\)", place)
        if qualified:
            place, qualifier = qualified.group(1).strip(), qualified.group(2)
            if _FUTURE_LOCATION in qualifier.lower():
                continue
            raise ValueError(f"Unhandled location qualifier {qualifier!r} in {text!r}.")
        parts = [p.strip() for p in place.split(",")]
        current.append((parts[0], markets.get(parts[-1])))
    return current


def parse_deadline(text: str | None, locations: list[tuple[str, str | None]]) -> datetime | None:
    """The application deadline, only when the cell is exactly one date.

    It falls at 23:59 local time of the primary current location, or 23:59
    UTC when the current locations span time zones or have no country.
    """
    if text is None:
        return None
    match = _DATE.fullmatch(text.strip())
    if match is None:
        return None
    day, month, year = int(match.group(1)), _MONTHS.index(match.group(2)) + 1, int(match.group(3))
    zones = {COUNTRY_TIMEZONES.get(code) for _, code in locations}
    zone = ZoneInfo(zones.pop()) if len(zones) == 1 and None not in zones else timezone.utc
    local = datetime.combine(datetime(year, month, day).date(), DEADLINE_TIME, tzinfo=zone)
    return local.astimezone(timezone.utc)


def bullets(text: str) -> list[str]:
    """A cell's "•" bullet lines, or the whole cell if it has none."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines if lines and all(line.startswith("•") for line in lines) else [text.strip()]


def document_text(row: dict[str, str | None]) -> str:
    """The row as one synthetic document: every stated cell but the audit URL."""
    return "\n".join(f"{name}: {row[name]}" for name in COLUMNS if name != AUDIT_COLUMN and row[name])


def convert_row(row: dict[str, str | None], markets: dict[str, str]) -> JobRecord:
    """One workbook row as a canonical JobRecord, inventing nothing."""
    profile_id = row["Profile ID"]
    job_id = f"{SOURCE}:{profile_id}"
    text = document_text(row)
    description = SourceDocument(
        document_id=f"{job_id}:description",
        kind=DocumentKind.JOB,
        text=text,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        source_ref=f"{WORKBOOK_NAME}#{SHEET_NAME}!{profile_id}",
    )

    evidence: list[EvidenceRef] = []

    def cite(short: str, field_path: str, quote: str) -> str:
        count = sum(1 for ref in evidence if ref.field_path == field_path)
        evidence_id = f"{job_id}:{short}-{count + 1:03d}"
        evidence.append(EvidenceRef(evidence_id=evidence_id, document_id=description.document_id,
                                    quote=quote, field_path=field_path))
        return evidence_id

    places = parse_locations(row["Locations"], markets)
    location_evidence = cite("location", "locations", row["Locations"])
    locations = [JobLocation(country_code=code, city=city, evidence_ids=[location_evidence]) for city, code in places]

    deadline = parse_deadline(row["Deadline / start period"], places)
    if deadline is not None:
        cite("deadline", "deadline_at", row["Deadline / start period"])

    requirements: list[RequirementFact] = []

    def require(text: str, classification, modality, constraint_id=None) -> None:
        requirements.append(RequirementFact(
            requirement_id=f"{job_id}:req-{len(requirements) + 1:03d}",
            text=text,
            classification=classification,
            modality=modality,
            constraint_id=constraint_id,
            evidence_ids=[cite("requirement", "facts.requirements", text)],
        ))

    for column, constraint_id in HARD_COLUMNS.items():
        cell = row[column]
        if cell is None:  # not stated: no requirement
            continue
        lowered = cell.lower()
        if constraint_id is None or NOT_STATED in lowered:
            require(cell.strip(), RequirementClassification.INFORMATIONAL, RequirementModality.UNSPECIFIED)
        elif PREFERRED in lowered:
            require(cell.strip(), RequirementClassification.FIT, RequirementModality.PREFERRED)
        else:
            # One requirement per language; the other constraints keep the
            # whole cell, so alternative routes ("OR") stay one requirement.
            parts = bullets(cell) if constraint_id == "HC_LANGUAGE" else [cell.strip()]
            for part in parts:
                require(part, RequirementClassification.HARD_CONSTRAINT, RequirementModality.MANDATORY, constraint_id)

    for item in bullets(row["Non-hard requirements"] or ""):
        if item:
            modality = RequirementModality.PREFERRED if PREFERRED in item.lower() else RequirementModality.UNSPECIFIED
            require(item, RequirementClassification.FIT, modality)

    if row["Application open"] != "Yes":
        raise ValueError(f"{profile_id}: 'Application open' is {row['Application open']!r}, not 'Yes'.")

    return JobRecord(
        schema_version="0.2.0-draft",
        job_id=job_id,
        source=SOURCE,
        source_job_id=profile_id,
        company=row["Company"],
        title=row["Job title"],
        url=PLACEHOLDER_URL.format(profile_id=profile_id),
        description=description,
        source_documents=[],
        locations=locations,
        source_published_at=None,
        source_updated_at=None,
        deadline_at=deadline,
        first_seen_at=CATALOGUE_TIMESTAMP,
        last_seen_at=CATALOGUE_TIMESTAMP,
        active_state=ActiveState.ACTIVE,
        discovery_kind=DiscoveryKind.INITIAL_SNAPSHOT,
        facts=JobFacts(skills=[], experience=[], education=[], role_family=None, requirements=requirements),
        evidence=evidence,
        extraction=None,
    )


def build(rows: list[dict[str, str | None]], markets: dict[str, str]) -> JobSnapshot:
    """The catalogue snapshot. It carries no audit URL."""
    jobs = [convert_row(row, markets) for row in rows]
    snapshot = JobSnapshot(
        schema_version="0.2.1-draft",
        snapshot_id=SNAPSHOT_ID,
        created_at=CATALOGUE_TIMESTAMP,
        jobs=jobs,
        documents={job.description.document_id: job.description for job in jobs},
        source_manifest=[SourceManifestEntry(
            source=SOURCE,
            source_ref=f"{WORKBOOK_NAME}#{SHEET_NAME}",
            retrieved_at=CATALOGUE_TIMESTAMP,
            record_count=len(jobs),
            redistribution_allowed=None,
        )],
        quarantine=[],
    )
    return snapshot


def audit_mapping(rows: list[dict[str, str | None]]) -> dict:
    """The local-only job -> audit URL mapping; never part of the catalogue."""
    return {
        "note": "Local audit provenance only. Not committed, never loaded by the app, never a posting link.",
        "snapshot_id": SNAPSHOT_ID,
        "source": f"{WORKBOOK_NAME}#{SHEET_NAME}",
        "audit_urls": {f"{SOURCE}:{row['Profile ID']}": row[AUDIT_COLUMN] for row in rows},
    }


def check_local_path(path: Path) -> Path:
    """`path`, if it lies outside the repository.

    Raises:
        ValueError: If `path` is inside the repository, where it could be
            committed or loaded.
    """
    resolved = path.expanduser().resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError(f"The audit mapping stays outside the repository; got {resolved}.")
    return resolved


def _dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--audit", type=Path, default=None,
                        help="Optional local path, outside the repository, for the audit URL mapping.")
    args = parser.parse_args(argv)
    audit_path = check_local_path(args.audit) if args.audit else None
    rows = read_rows(args.workbook)
    snapshot = build(rows, load_market_names())
    args.output.write_text(_dump(snapshot.model_dump(mode="json")), encoding="utf-8")
    print(f"Wrote {len(snapshot.jobs)} jobs to {args.output}.")
    if audit_path is not None:
        audit_path.write_text(_dump(audit_mapping(rows)), encoding="utf-8")
        print(f"Wrote the local audit mapping to {audit_path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
