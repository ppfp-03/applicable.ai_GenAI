"""Derive the normalized synthetic demo catalogue from the faithful OI-50 one.

Generation only: this runs by hand and writes three committed files. Nothing
in the app imports it.

    python -m oi.io.synthetic_normalized            # write the files
    python -m oi.io.synthetic_normalized --check    # fail if they are stale

It reads the faithful catalogue (``data/snapshots/synthetic_oi50.json``), its
curated parameters (``config/eligibility/job_parameters.json``), the rules in
``config/synthetic/oi50_normalization.json`` and the shared skills vocabulary
(``config/skills_vocabulary.json``). It writes:

- ``data/snapshots/synthetic_oi50_normalized.json``: a ``JobSnapshot`` of 50
  jobs ``synthetic-normalized:SYN-JOB-NNN``;
- ``config/eligibility/job_parameters_normalized.json``: the parameter layer
  for every hard requirement of those jobs;
- ``data/snapshots/synthetic_oi50_normalized_provenance.json``: every value
  that ranking or eligibility reads, classed SOURCE, NORMALIZED or
  SYNTHETIC_FILL, with the rule used and the faithful requirement it came from.

The faithful files are only read, never written.

This is controlled synthetic demo data, never held-out evaluation data. Values
the faithful catalogue states win (SOURCE); approved wording maps turn source
text into vocabulary values (NORMALIZED); everything else is dealt from
approved quotas in an order fixed by ``sha256("<field>:<source job id>")``
(SYNTHETIC_FILL). No candidate is read, so nothing is tuned to one. Every
normalized or filled value is stated in a per-job normalization document
(``source_ref`` ``normalization:oi50-v1#SYN-JOB-NNN``), and fills cite that
document only, never the posting text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

from oi.contracts import JobSnapshot
from oi.intelligence.eligibility.parameters import JobParameterSet
from oi.intelligence.eligibility.rules.language import FLUENT_LEVELS

ROOT = Path(__file__).resolve().parents[3]
FAITHFUL_SNAPSHOT = ROOT / "data" / "snapshots" / "synthetic_oi50.json"
FAITHFUL_PARAMETERS = ROOT / "config" / "eligibility" / "job_parameters.json"
RULES_PATH = ROOT / "config" / "synthetic" / "oi50_normalization.json"
SKILLS_PATH = ROOT / "config" / "skills_vocabulary.json"
SNAPSHOT_PATH = ROOT / "data" / "snapshots" / "synthetic_oi50_normalized.json"
PARAMETERS_PATH = ROOT / "config" / "eligibility" / "job_parameters_normalized.json"
PROVENANCE_PATH = ROOT / "data" / "snapshots" / "synthetic_oi50_normalized_provenance.json"

SOURCE = "synthetic-normalized"
FAITHFUL_SOURCE = "synthetic"
SNAPSHOT_ID = "synthetic-oi50-normalized"

SOURCE_CLASS = "SOURCE"
NORMALIZED = "NORMALIZED"
FILL = "SYNTHETIC_FILL"

STATUS_WORDS = {
    "enrolled_student": "enrolled student",
    "recent_graduate": "recent graduate",
}
SPONSORSHIP_WORDS = {
    "offered": "visa sponsorship is offered",
    "not_offered": "visa sponsorship is not offered",
    "not_stated": "the posting does not state whether visa sponsorship is offered",
}


# --- Helpers ----------------------------------------------------------------


def order_key(name: str, source_job_id: str) -> str:
    """The fixed, candidate-independent order in which fills are dealt."""
    return hashlib.sha256(f"{name}:{source_job_id}".encode()).hexdigest()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _renamed(value: str) -> str:
    """A faithful ID in the normalized namespace."""
    prefix = f"{FAITHFUL_SOURCE}:"
    if not value.startswith(prefix):
        raise ValueError(f"not a faithful ID: {value!r}")
    return f"{SOURCE}:{value[len(prefix):]}"


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _value(value: Any, cls: str, rule: str, refs: Sequence[str] = ()) -> dict:
    return {"value": value, "class": cls, "rule": rule, "source_refs": list(refs)}


def deal(name: str, ids: Sequence[str], quota: dict[str, int], taken: dict[str, int]) -> dict[str, str]:
    """Deal what `quota` leaves after `taken` to `ids`, in `order_key` order.

    Raises:
        ValueError: If source values already exceed a bucket, or the remainder
            does not match the number of jobs to fill.
    """
    rest = {value: count - taken.get(value, 0) for value, count in quota.items()}
    if any(count < 0 for count in rest.values()):
        raise ValueError(f"{name}: source values exceed the quota {quota} (taken {taken})")
    values = [value for value, count in rest.items() for _ in range(count)]
    if len(values) != len(ids):
        raise ValueError(f"{name}: quota leaves {len(values)} values for {len(ids)} jobs")
    ordered = sorted(ids, key=lambda i: order_key(name, i))
    return dict(zip(ordered, values))


def spread(name: str, ids: Sequence[str], buckets: Sequence[dict]) -> dict[str, int]:
    """Deal day offsets from day buckets, evenly spaced inside each bucket."""
    total = sum(bucket["count"] for bucket in buckets)
    if total != len(ids):
        raise ValueError(f"{name}: buckets hold {total} values for {len(ids)} jobs")
    ordered = sorted(ids, key=lambda i: order_key(name, i))
    out, start = {}, 0
    for bucket in buckets:
        low, high, count = bucket["min"], bucket["max"], bucket["count"]
        for index in range(count):
            step = 0 if count == 1 else round(index * (high - low) / (count - 1))
            out[ordered[start + index]] = low + step
        start += count
    return out


def _first_match(text: str, phrases: Sequence[str]) -> str | None:
    lowered = text.lower()
    return next((phrase for phrase in phrases if phrase in lowered), None)


# --- Per-requirement normalization --------------------------------------------


def student_status(text: str, rules: dict) -> tuple[list[str], str] | None:
    """Accepted statuses and the phrase that decided them, from source wording."""
    phrases = rules["student_status_phrases"]
    both = _first_match(text, phrases["both"])
    if both:
        return ["enrolled_student", "recent_graduate"], both
    recent = _first_match(text, phrases["recent_graduate"])
    student = _first_match(text, phrases["enrolled_student"])
    if recent and student:
        return ["enrolled_student", "recent_graduate"], f"{recent} + {student}"
    if recent:
        return ["recent_graduate"], recent
    if student:
        return ["enrolled_student"], student
    return None


SUMMER = re.compile(r"summer (\d{4})", re.IGNORECASE)


def grad_window(text: str) -> tuple[date, date] | None:
    """`summer YYYY` is 1 June - 30 September; several summers span them all."""
    years = [int(y) for y in SUMMER.findall(text)]
    if not years:
        return None
    return date(min(years), 6, 1), date(max(years), 9, 30)


RANGE = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*(?:relevant\s+)?years?", re.IGNORECASE)


def experience_lower_bound(text: str, rules: dict) -> int | None:
    """Months at the lower bound of an explicit, unconditional year range."""
    if _first_match(text, rules["experience_conditional_markers"]):
        return None
    match = RANGE.search(text)
    return int(match.group(1)) * 12 if match else None


def fields_of_study(text: str, rules: dict) -> tuple[list[str], list[str], bool, list[str]]:
    """(accepted fields, unmapped terms, whether related fields are accepted,
    the source terms that were mapped)."""
    terms = sorted(rules["field_terms"].items(), key=lambda item: -len(item[0]))
    exact = rules["field_terms_case_sensitive"]
    accepted: list[str] = []
    unmapped: list[str] = []
    used: list[str] = []
    for chunk in re.split(r"\bOR\b|,|;|/|\(|\)|•", text):
        chunk = chunk.strip(" .")
        if not chunk:
            continue
        term = next((word for word in exact if re.search(rf"\b{re.escape(word)}\b", chunk)), None)
        hit = exact.get(term)
        if hit is None:
            lowered = chunk.lower()
            found = [(lowered.find(word), -len(word), word, f) for word, f in terms
                     if re.search(rf"\b{re.escape(word)}\b", lowered)]
            term, hit = min(found)[2:] if found else (None, None)
        if hit is None:
            if not any(re.search(m, chunk.lower()) for m in rules["related_markers"]):
                unmapped.append(chunk)
            continue
        used.append(term)
        if hit not in accepted:
            accepted.append(hit)
    related = any(re.search(marker, text.lower()) for marker in rules["related_markers"])
    return accepted, unmapped, related, used


def broadened(accepted: list[str], rules: dict) -> list[str]:
    """`accepted` plus each field's approved related fields, one hop."""
    out = list(accepted)
    for name in accepted:
        for other in rules["related_fields"].get(name, []):
            if other not in out:
                out.append(other)
    return out


def languages(text: str, rules: dict) -> tuple[list[tuple[str, str]], str]:
    """[(ISO 639-1 code, level)], and the rule used, from one source line."""
    lowered = text.lower()
    level = next((entry["level"] for entry in rules["language_levels"] if entry["wording"] in lowered), None)
    names = sorted(
        (lowered.find(name), code) for name, code in rules["language_names"].items() if name in lowered
    )
    codes = list(dict.fromkeys(code for _, code in names))
    if level is None or not codes:
        return [], "unmapped"
    if " or " in lowered and len(codes) > 1:
        convention = rules["alternative_language_levels"].get(codes[0])
        if convention is not None:
            return [(codes[0], convention)], f"alternatives_convention:{codes[0]}={convention}"
        return [(codes[0], level)], "first_listed_alternative"
    if len(codes) > 1:
        return [(code, level) for code in codes], "split_languages"
    return [(codes[0], level)], "wording_map"


def comparable_level(code: str, level: str, rules: dict) -> tuple[str, str | None]:
    """`level` on the scale candidates normally answer on, and the rule used.

    The engine counts "fluent" as a fixed level only for some languages
    (FLUENT_LEVELS); for the others SELF:fluent cannot be compared with a
    CEFR answer. The demo layer states those on CEFR instead, at the level
    D-046 gives English "fluent". The engine and D-046 are unchanged.
    """
    if level == "SELF:fluent" and code not in FLUENT_LEVELS:
        target = rules["fluent_without_engine_level"]
        return target, f"fluent_as_{target.replace(':', '_').lower()}"
    return level, None


def language_name(code: str, rules: dict) -> str:
    return next(n for n, c in rules["language_names"].items() if c == code).capitalize()


# --- Build ----------------------------------------------------------------------


@dataclass
class Draft:
    """One normalized job while it is being built."""

    faithful: dict
    sid: str
    lines: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    requirements: list[dict] = field(default_factory=list)
    parameters: list[dict] = field(default_factory=list)
    values: dict = field(default_factory=dict)
    req_provenance: dict = field(default_factory=dict)

    @property
    def job_id(self) -> str:
        return f"{SOURCE}:{self.sid}"

    @property
    def doc_id(self) -> str:
        return f"{self.job_id}:normalization"

    def state(self, key: str, line: str, field_path: str) -> str:
        """Add one statement to the normalization document; return its evidence ID."""
        self.lines.append(line)
        evidence_id = f"{self.job_id}:norm-{key}"
        self.evidence.append({"evidence_id": evidence_id, "document_id": self.doc_id,
                              "quote": line, "field_path": field_path})
        return evidence_id

    def statement(self, key: str) -> str:
        """The statement behind evidence `norm-<key>`, without its final period."""
        evidence_id = f"{self.job_id}:norm-{key}"
        return next(e["quote"] for e in self.evidence if e["evidence_id"] == evidence_id).rstrip(".")

    def ordered(self) -> None:
        """Requirements and parameters in source order, added requirements last."""
        def key(item: dict) -> tuple[int, str]:
            return (0 if ":req-" in item["requirement_id"] else 1, item["requirement_id"])
        self.requirements.sort(key=key)
        self.parameters.sort(key=key)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build(faithful: dict, faithful_params: dict, rules: dict, skills: dict) -> tuple[dict, dict, dict]:
    """(snapshot, parameter layer, provenance) as JSON-ready dicts."""
    anchor = datetime.fromisoformat(rules["anchor"].replace("Z", "+00:00"))
    vocabulary = [entry["name"] for entry in skills["skills"]]
    known = {name.lower(): name for name in vocabulary}
    params_by_req = {entry["requirement_id"]: entry for entry in faithful_params["entries"]}
    markets = {m["code"]: m["name"] for m in _load(ROOT / "config" / "markets.json")["countries"]}
    drafts = [Draft(job, job["source_job_id"]) for job in faithful["jobs"]]
    ids = [d.sid for d in drafts]
    header = ("Demo normalization {version} for {sid}. Synthetic demo data: these statements were "
              "authored to make the job comparable and are not from the posting.")

    for d in drafts:
        d.lines.append(header.format(version=rules["normalization_version"], sid=d.sid))

    # Hard requirements: carry, normalize or fill each one.
    pending_experience: list[Draft] = []
    for d in drafts:
        for req in d.faithful["facts"]["requirements"]:
            _requirement(d, req, params_by_req.get(req["requirement_id"]), rules, pending_experience)

    # Primary location: the first current location, as written.
    for d in drafts:
        first = d.faithful["locations"][0]
        d.values["primary_country"] = _value(first["country_code"], SOURCE_CLASS, "first_current_location",
                                             first["evidence_ids"])

    _work_authorization(drafts, rules, markets)
    _student_status(drafts, rules)
    _role_family(drafts, rules)
    _skills(drafts, rules, known)
    _education(drafts, rules)
    _experience(drafts, rules, pending_experience)
    _dates(drafts, rules, anchor)

    for d in drafts:
        d.ordered()
    snapshot = _snapshot(drafts, faithful, rules, anchor)
    parameters = {"layer_version": faithful_params["layer_version"],
                  "entries": [entry for d in drafts for entry in d.parameters]}
    provenance = {
        "normalization_version": rules["normalization_version"],
        "snapshot_id": SNAPSHOT_ID,
        "faithful_snapshot_id": faithful["snapshot_id"],
        "faithful_snapshot_sha256": _sha(FAITHFUL_SNAPSHOT.read_text(encoding="utf-8")),
        "evaluation_use": rules["evaluation_use"],
        "anchor": rules["anchor"],
        "classes": [SOURCE_CLASS, NORMALIZED, FILL],
        "jobs": {d.job_id: {"faithful_job_id": d.faithful["job_id"], "values": d.values,
                            "requirements": d.req_provenance} for d in drafts},
    }
    # Validate before anything is written.
    JobSnapshot.model_validate(snapshot)
    JobParameterSet.model_validate(parameters)
    return snapshot, parameters, provenance


def _add_requirement(d: Draft, req_id: str, text: str, constraint: str | None, evidence: list[str],
                     params: dict | None, cls: str, rule: str, faithful_req: str | None,
                     classification: str = "hard_constraint", modality: str = "mandatory") -> None:
    d.requirements.append({
        "requirement_id": req_id, "text": text, "classification": classification,
        "modality": modality, "constraint_id": constraint if classification == "hard_constraint" else None,
        "evidence_ids": evidence,
    })
    d.req_provenance[req_id] = {"constraint_id": constraint, "class": cls, "rule": rule,
                                "faithful_requirement_id": faithful_req,
                                "parameters": params if classification == "hard_constraint" else None}
    if classification == "hard_constraint":
        d.parameters.append({
            "job_id": d.job_id, "requirement_id": req_id, "constraint_id": constraint,
            "parameters": params, "evidence_ids": evidence, "origin": "curated",
            "note": f"Normalized demo layer, {cls}: {rule}.",
        })


def _requirement(d: Draft, req: dict, faithful_entry: dict | None, rules: dict,
                 pending_experience: list[Draft]) -> None:
    rid = _renamed(req["requirement_id"])
    source_ev = [_renamed(e) for e in req["evidence_ids"]]
    constraint = req["constraint_id"]
    if req["classification"] != "hard_constraint":
        _add_requirement(d, rid, req["text"], None, source_ev, None, SOURCE_CLASS, "carried",
                         req["requirement_id"], req["classification"], req["modality"])
        return

    if faithful_entry is not None:
        params = dict(faithful_entry["parameters"])
        if params["kind"] == "degree_level" and params.get("in_progress_policy") is None:
            # The faithful layer leaves the policy to the catalogue default
            # ("undecided"); the demo layer states one.
            params["in_progress_policy"] = "counts"
            ev = d.state("degree-policy", "Degree policy: a degree in progress counts.", "facts.requirements")
            _add_requirement(d, rid, req["text"], constraint, source_ev + [ev], params, FILL,
                             "in_progress_policy_fill", req["requirement_id"])
            return
        if params["kind"] == "language":
            level, level_rule = comparable_level(params["language"], f"{params['scale']}:{params['min_level']}", rules)
            if level_rule:
                params["scale"], params["min_level"] = level.split(":")
                line = f"Language: {language_name(params['language'], rules)}, {level}."
                ev = d.state(f"language-{params['language']}", line, "facts.requirements")
                _add_requirement(d, rid, req["text"], constraint,
                                 [_renamed(e) for e in faithful_entry["evidence_ids"]] + [ev], params, FILL,
                                 f"faithful_parameter+{level_rule}", req["requirement_id"])
                return
        _add_requirement(d, rid, req["text"], constraint,
                         [_renamed(e) for e in faithful_entry["evidence_ids"]], params, SOURCE_CLASS,
                         "faithful_parameter", req["requirement_id"])
        return

    text = req["text"]
    if constraint == "HC_STUDENT_STATUS":
        found = student_status(text, rules)
        if found is None:
            raise ValueError(f"{d.sid}: no student-status rule for {text!r}")
        accepted, phrase = found
        line = "Student status: " + " or ".join(STATUS_WORDS[s] for s in accepted) + "."
        ev = d.state("student-status", line, "facts.requirements")
        _add_requirement(d, rid, text, constraint, source_ev + [ev],
                         {"kind": "student_status", "accepted": accepted}, NORMALIZED,
                         f"student_status_phrase:{phrase}", req["requirement_id"])
    elif constraint == "HC_GRAD_WINDOW":
        window = grad_window(text)
        if window is None:
            raise ValueError(f"{d.sid}: no graduation-window rule for {text!r}")
        line = f"Graduation window: {window[0].isoformat()} to {window[1].isoformat()}."
        ev = d.state("grad-window", line, "facts.requirements")
        _add_requirement(d, rid, text, constraint, source_ev + [ev],
                         {"kind": "grad_window", "start": window[0].isoformat(), "end": window[1].isoformat()},
                         NORMALIZED, "summer_is_june_to_september", req["requirement_id"])
    elif constraint == "HC_MIN_EXPERIENCE":
        months = experience_lower_bound(text, rules)
        if months == 0:
            # Lower bound zero: the posting imposes no minimum, so nothing gates.
            _add_requirement(d, rid, text, None, source_ev, None, NORMALIZED, "range_lower_bound_zero",
                             req["requirement_id"], "informational", req["modality"])
            d.values["experience_months"] = _value(0, NORMALIZED, "range_lower_bound", [req["requirement_id"]])
        elif months is not None:
            line = f"Experience requirement: at least {months} months."
            ev = d.state("experience", line, "facts.requirements")
            _add_requirement(d, rid, text, constraint, source_ev + [ev],
                             {"kind": "min_experience", "min_months": months}, NORMALIZED,
                             "range_lower_bound", req["requirement_id"])
            d.values["experience_months"] = _value(months, NORMALIZED, "range_lower_bound", [req["requirement_id"]])
        else:
            d.values["_experience_requirement"] = {"requirement": req, "id": rid, "evidence": source_ev}
            pending_experience.append(d)
    elif constraint == "HC_FIELD_OF_STUDY":
        accepted, unmapped, related, used = fields_of_study(text, rules)
        if not accepted:
            raise ValueError(f"{d.sid}: no field of study mapped from {text!r}")
        broad = [t for t in used if t in rules["broad_field_terms"]]
        rule = "field_terms" + (f"+broad_terms:{','.join(broad)}" if broad else "")
        if related:
            accepted, rule = broadened(accepted, rules), rule + "+related_broadened"
        # A field the posting names word for word is NORMALIZED; a broad term
        # or a related-field broadening is a semantic default, so a fill.
        cls = FILL if broad or related else NORMALIZED
        line = "Field of study: " + ", ".join(accepted) + "."
        ev = d.state("field", line, "facts.requirements")
        _add_requirement(d, rid, text, constraint, source_ev + [ev],
                         {"kind": "field_of_study", "accepted": accepted, "related_accepted": False},
                         cls, rule, req["requirement_id"])
        d.values["fields_of_study"] = _value({"fields": accepted, "any": False}, cls, rule,
                                             [req["requirement_id"]])
        if unmapped:
            d.values["fields_of_study"]["unmapped_terms"] = unmapped
    elif constraint == "HC_WORK_AUTH":
        phrases = rules["sponsorship_normalized"]
        phrase = _first_match(text, phrases["not_offered"])
        broad = _first_match(text, phrases["not_offered_broad"])
        if phrase is None and broad is None:
            raise ValueError(f"{d.sid}: no work-authorization rule for {text!r}")
        # Stated "without sponsorship" is NORMALIZED; inferring it from a
        # requirement to hold authorization already is a semantic default.
        cls, phrase = (NORMALIZED, phrase) if phrase else (FILL, broad)
        country = d.faithful["locations"][0]["country_code"]
        line = f"Work authorization: required for {country}; {SPONSORSHIP_WORDS['not_offered']}."
        ev = d.state("work-auth", line, "facts.requirements")
        params = {"kind": "work_auth", "country_code": country, "employer_sponsorship": "not_offered"}
        _add_requirement(d, rid, text, constraint, source_ev + [ev], params, cls,
                         f"sponsorship_phrase:{phrase}", req["requirement_id"])
    elif constraint == "HC_DEGREE_LEVEL":
        lowered = text.lower()
        if "bac+4" in lowered or "bac+5" in lowered:
            level, rule = "master", "bac_plus_4_or_5_is_master"
        elif "bachelor" in lowered and ("msc" in lowered or "master" in lowered):
            level, rule = "bachelor", "bachelor_or_master_is_bachelor"
        else:
            d.values["_degree_requirement"] = {"requirement": req, "id": rid, "evidence": source_ev}
            return
        policy = "does_not_count" if re.search(r"\bcompleted\b", lowered) and "study" not in lowered else "counts"
        line = f"Degree level: at least {level}; a degree in progress {'counts' if policy == 'counts' else 'does not count'}."
        ev = d.state("degree", line, "facts.requirements")
        _add_requirement(d, rid, text, constraint, source_ev + [ev],
                         {"kind": "degree_level", "min_level": level, "in_progress_policy": policy},
                         NORMALIZED, rule, req["requirement_id"])
    elif constraint == "HC_LANGUAGE":
        found, rule = languages(text, rules)
        if not found:
            raise ValueError(f"{d.sid}: no language rule for {text!r}")
        # A level the posting does not state (the alternatives convention) is a fill.
        cls = FILL if rule.startswith("alternatives_convention") else NORMALIZED
        for index, (code, level) in enumerate(found, start=1):
            level, level_rule = comparable_level(code, level, rules)
            line = f"Language: {language_name(code, rules)}, {level}."
            ev = d.state(f"language-{code}", line, "facts.requirements")
            req_id = rid if len(found) == 1 else f"{rid}-{index}"
            scale, _, minimum = level.partition(":")
            _add_requirement(d, req_id, text if len(found) == 1 else line, constraint,
                             (source_ev + [ev]) if len(found) == 1 else [ev] + source_ev,
                             {"kind": "language", "language": code, "scale": scale, "min_level": minimum},
                             FILL if level_rule else cls, "+".join(filter(None, [rule, level_rule])),
                             req["requirement_id"])
    else:
        raise ValueError(f"{d.sid}: no normalization for {constraint}")


def _hard(d: Draft, constraint: str) -> list[dict]:
    return [r for r in d.requirements if r["constraint_id"] == constraint]


def _params(d: Draft, req_id: str) -> dict:
    return next(e["parameters"] for e in d.parameters if e["requirement_id"] == req_id)


def _work_authorization(drafts: list[Draft], rules: dict, markets: dict) -> None:
    """Every job requires work authorization for its primary country."""
    taken: dict[str, int] = {}
    missing = []
    for d in drafts:
        existing = _hard(d, "HC_WORK_AUTH")
        if existing:
            params = _params(d, existing[0]["requirement_id"])
            taken[params["employer_sponsorship"]] = taken.get(params["employer_sponsorship"], 0) + 1
            prov = d.req_provenance[existing[0]["requirement_id"]]
            d.values["sponsorship"] = _value(params["employer_sponsorship"], prov["class"], prov["rule"],
                                             [prov["faithful_requirement_id"]])
        else:
            missing.append(d.sid)
    dealt = deal("sponsorship", missing, rules["quotas"]["sponsorship"], taken)
    for d in drafts:
        if d.sid not in dealt:
            continue
        country = d.values["primary_country"]["value"]
        policy = dealt[d.sid]
        line = f"Work authorization: required for {markets[country]} ({country}); {SPONSORSHIP_WORDS[policy]}."
        ev = d.state("work-auth", line, "facts.requirements")
        _add_requirement(d, f"{d.job_id}:norm-work-auth", line, "HC_WORK_AUTH", [ev],
                         {"kind": "work_auth", "country_code": country, "employer_sponsorship": policy},
                         FILL, "sponsorship_quota", None)
        d.values["sponsorship"] = _value(policy, FILL, "sponsorship_quota")


def _student_status(drafts: list[Draft], rules: dict) -> None:
    """Every job states which student statuses it accepts."""
    taken: dict[str, int] = {}
    missing = []
    for d in drafts:
        existing = _hard(d, "HC_STUDENT_STATUS")
        if existing:
            accepted = "+".join(_params(d, existing[0]["requirement_id"])["accepted"])
            taken[accepted] = taken.get(accepted, 0) + 1
        else:
            missing.append(d.sid)
    dealt = deal("student_status", missing, rules["quotas"]["student_status"], taken)
    for d in drafts:
        if d.sid not in dealt:
            continue
        accepted = dealt[d.sid].split("+")
        line = "Student status: " + " or ".join(STATUS_WORDS[s] for s in accepted) + "."
        ev = d.state("student-status", line, "facts.requirements")
        _add_requirement(d, f"{d.job_id}:norm-student-status", line, "HC_STUDENT_STATUS", [ev],
                         {"kind": "student_status", "accepted": accepted}, FILL, "student_status_quota", None)


def _role_family(drafts: list[Draft], rules: dict) -> None:
    """One family per job, from the title; titles no rule matches are filled."""
    counts = {family: 0 for family in rules["role_families"]}
    unmatched = []
    for d in drafts:
        title = d.faithful["title"].lower()
        rule = next((r for r in rules["role_family_title_rules"]
                     if any(k in title for k in r["keywords"])), None)
        if rule is None:
            unmatched.append(d)
            continue
        keyword = next(k for k in rule["keywords"] if k in title)
        # A title that names the family is NORMALIZED; a broad association
        # (for example "middle office" -> Markets & Trading) is a fill.
        cls = FILL if keyword in rule.get("broad", []) else NORMALIZED
        d.values["role_family"] = _value(rule["family"], cls, f"title_keyword:{keyword}")
        counts[rule["family"]] += 1
    order = rules["role_families"]
    for d in sorted(unmatched, key=lambda x: order_key("role_family", x.sid)):
        family = min(order, key=lambda f: (counts[f], order.index(f)))
        counts[family] += 1
        d.values["role_family"] = _value(family, FILL, "least_represented_family")
    for d in drafts:
        family = d.values["role_family"]["value"]
        d.values["role_family"]["evidence_id"] = d.state("role-family", f"Role family: {family}.",
                                                         "facts.role_family")


def _skills(drafts: list[Draft], rules: dict, known: dict[str, str]) -> None:
    """4-6 vocabulary skills: those the posting names first, then the family's."""
    low, high = rules["skill_count"]["min"], rules["skill_count"]["max"]
    for family, pool in rules["role_family_skills"].items():
        unknown = [s for s in pool if s.lower() not in known]
        if unknown:
            raise ValueError(f"{family}: skills {unknown} are not in the shared vocabulary")
    for entry in rules["skill_keywords"]:
        if entry["skill"].lower() not in known:
            raise ValueError(f"skill {entry['skill']!r} is not in the shared vocabulary")
    for d in drafts:
        found: list[dict] = []
        for req in d.faithful["facts"]["requirements"]:
            if req["classification"] != "fit":
                continue
            lowered = req["text"].lower()
            for entry in rules["skill_keywords"]:
                keyword = next((k for k in entry["keywords"] if k in lowered), None)
                if keyword and all(f["value"] != entry["skill"] for f in found):
                    cls = FILL if keyword in entry.get("broad", []) else NORMALIZED
                    found.append(_value(entry["skill"], cls, f"skill_keyword:{keyword}",
                                        [req["requirement_id"]]))
        found = found[:high]
        target = max(low + int(order_key("skill_count", d.sid), 16) % (high - low + 1), len(found))
        pool = rules["role_family_skills"][d.values["role_family"]["value"]]
        start = int(order_key("skill_pool", d.sid), 16) % len(pool)
        for skill in pool[start:] + pool[:start]:
            if len(found) >= target:
                break
            if all(f["value"] != skill for f in found):
                found.append(_value(skill, FILL, "role_family_skill_pool"))
        line = "Skills: " + "; ".join(f["value"] for f in found) + "."
        ev = d.state("skills", line, "facts.skills")
        for f in found:
            f["evidence_id"] = ev
        d.values["skills"] = found


def _education(drafts: list[Draft], rules: dict) -> None:
    """Minimum degree level and accepted fields for every job."""
    taken: dict[str, int] = {}
    missing = []
    for d in drafts:
        stated = _hard(d, "HC_DEGREE_LEVEL")
        if stated:
            level = _params(d, stated[0]["requirement_id"])["min_level"]
            prov = d.req_provenance[stated[0]["requirement_id"]]
            d.values["degree_level"] = _value(level, NORMALIZED if prov["class"] == NORMALIZED else SOURCE_CLASS,
                                              prov["rule"], [prov["faithful_requirement_id"]])
            taken[level] = taken.get(level, 0) + 1
        else:
            missing.append(d.sid)
    dealt = deal("degree_level", missing, rules["quotas"]["degree_level"], taken)
    for d in drafts:
        if d.sid in dealt:
            level = dealt[d.sid]
            d.values["degree_level"] = _value(level, FILL, "degree_level_quota")
            pending = d.values.pop("_degree_requirement", None)
            if pending is not None:
                # A stated but unreadable degree requirement takes the filled level.
                req = pending["requirement"]
                line = f"Degree level: at least {level}; a degree in progress counts."
                ev = d.state("degree", line, "facts.requirements")
                _add_requirement(d, pending["id"], req["text"], "HC_DEGREE_LEVEL", pending["evidence"] + [ev],
                                 {"kind": "degree_level", "min_level": level, "in_progress_policy": "counts"},
                                 FILL, "degree_level_quota", req["requirement_id"])
        level = d.values["degree_level"]["value"]
        d.values["degree_level"]["evidence_id"] = d.state("degree-level", f"Minimum degree level: {level}.",
                                                          "facts.education")

    markers = rules["all_disciplines_markers"]
    for d in drafts:
        if "fields_of_study" not in d.values:
            stated = _hard(d, "HC_FIELD_OF_STUDY")
            if stated:
                params = _params(d, stated[0]["requirement_id"])
                prov = d.req_provenance[stated[0]["requirement_id"]]
                d.values["fields_of_study"] = _value({"fields": params["accepted"], "any": False},
                                                     SOURCE_CLASS, prov["rule"], [prov["faithful_requirement_id"]])
            else:
                open_req = next((r for r in d.faithful["facts"]["requirements"]
                                 if _first_match(r["text"], markers)), None)
                if open_req is not None:
                    d.values["fields_of_study"] = _value({"fields": [], "any": True}, NORMALIZED,
                                                         "all_disciplines_accepted", [open_req["requirement_id"]])
                else:
                    fields = rules["role_family_default_fields"][d.values["role_family"]["value"]]
                    d.values["fields_of_study"] = _value({"fields": list(fields), "any": False}, FILL,
                                                         "role_family_default_fields")
        value = d.values["fields_of_study"]["value"]
        line = "Accepted fields of study: " + ("any field" if value["any"] else ", ".join(value["fields"])) + "."
        d.values["fields_of_study"]["evidence_id"] = d.state("fields", line, "facts.education")


def _experience(drafts: list[Draft], rules: dict, pending: list[Draft]) -> None:
    """Minimum months of experience for every job.

    A stated requirement that no approved rule reads (for example "1-2
    internships") takes a filled value, drawn first from the positive part of
    the quota so the stated requirement is never read as "none".
    """
    taken: dict[str, int] = {}
    for d in drafts:
        if "experience_months" in d.values:
            key = str(d.values["experience_months"]["value"])
            taken[key] = taken.get(key, 0) + 1
    quota = rules["quotas"]["experience_months"]
    rest = {value: count - taken.get(value, 0) for value, count in quota.items()}
    missing = [d.sid for d in drafts if "experience_months" not in d.values]
    if sum(rest.values()) != len(missing) or any(c < 0 for c in rest.values()):
        raise ValueError(f"experience quota {quota} does not fit {len(missing)} jobs (taken {taken})")
    pool = [value for value, count in rest.items() for _ in range(count)]
    pool = [v for _, v in sorted((order_key("experience_slot", f"{i}"), v) for i, v in enumerate(pool))]
    stated = sorted((d.sid for d in pending), key=lambda s: order_key("experience_months", s))
    others = sorted((s for s in missing if s not in stated), key=lambda s: order_key("experience_months", s))
    dealt: dict[str, str] = {}
    for sid in stated:
        value = next(v for v in pool if v != "0")
        pool.remove(value)
        dealt[sid] = value
    dealt.update(zip(others, pool))

    by_sid = {d.sid: d for d in drafts}
    for sid, value in dealt.items():
        d = by_sid[sid]
        months = int(value)
        d.values["experience_months"] = _value(months, FILL, "experience_months_quota")
        pending_req = d.values.pop("_experience_requirement", None)
        if pending_req is not None:
            req = pending_req["requirement"]
            line = f"Experience requirement: at least {months} months."
            ev = d.state("experience", line, "facts.requirements")
            _add_requirement(d, pending_req["id"], req["text"], "HC_MIN_EXPERIENCE", pending_req["evidence"] + [ev],
                             {"kind": "min_experience", "min_months": months}, FILL,
                             "experience_months_quota", req["requirement_id"])
    for d in drafts:
        months = d.values["experience_months"]["value"]
        text = "none" if months == 0 else f"{months} months"
        d.values["experience_months"]["evidence_id"] = d.state("experience-months", f"Minimum experience: {text}.",
                                                               "facts.experience")


def _dates(drafts: list[Draft], rules: dict, anchor: datetime) -> None:
    """Source deadlines stay; the rest and every first-seen time are filled."""
    missing = [d.sid for d in drafts if d.faithful["deadline_at"] is None]
    days = spread("deadline_at", missing, rules["quotas"]["deadline_days"])
    seen = spread("first_seen_at", [d.sid for d in drafts], rules["quotas"]["first_seen_days"])
    for d in drafts:
        if d.sid in days:
            moment = datetime.combine(anchor.date() + timedelta(days=days[d.sid]),
                                      datetime.min.time().replace(hour=23, minute=59), timezone.utc)
            ev = d.state("deadline", f"Application deadline: {_stamp(moment)}.", "deadline_at")
            d.values["deadline_at"] = _value(_stamp(moment), FILL, f"deadline_days_quota:{days[d.sid]}")
            d.values["deadline_at"]["evidence_id"] = ev
        else:
            refs = [e["evidence_id"] for e in d.faithful["evidence"] if e["field_path"] == "deadline_at"]
            d.values["deadline_at"] = _value(d.faithful["deadline_at"], SOURCE_CLASS, "faithful_deadline", refs)
        first = anchor - timedelta(days=seen[d.sid])
        ev = d.state("first-seen", f"Discovery (simulated): first seen {_stamp(first)}.", "first_seen_at")
        d.values["first_seen_at"] = _value(_stamp(first), FILL, f"first_seen_days_quota:{seen[d.sid]}")
        d.values["first_seen_at"]["evidence_id"] = ev
        d.values["discovery_kind"] = _value("synthetic_scenario", FILL, "simulated_discovery")


def _snapshot(drafts: list[Draft], faithful: dict, rules: dict, anchor: datetime) -> dict:
    documents: dict[str, dict] = {}
    jobs = []
    for d in drafts:
        job = d.faithful
        description = dict(job["description"], document_id=_renamed(job["description"]["document_id"]))
        text = "\n".join(d.lines)
        normalization = {"document_id": d.doc_id, "kind": "job", "text": text, "content_hash": _sha(text),
                         "source_ref": f"normalization:{rules['normalization_version']}#{d.sid}"}
        documents[description["document_id"]] = description
        documents[d.doc_id] = normalization
        filled_deadline = d.values["deadline_at"]["class"] == FILL
        evidence = [dict(e, evidence_id=_renamed(e["evidence_id"]), document_id=_renamed(e["document_id"]))
                    for e in job["evidence"] if not (filled_deadline and e["field_path"] == "deadline_at")]
        evidence += d.evidence
        v = d.values
        jobs.append({
            "schema_version": job["schema_version"],
            "job_id": d.job_id,
            "source": SOURCE,
            "source_job_id": d.sid,
            "company": job["company"],
            "title": job["title"],
            "url": f"https://example.invalid/{SOURCE}/{d.sid}",
            "description": description,
            "source_documents": [normalization],
            "locations": [dict(loc, evidence_ids=[_renamed(e) for e in loc["evidence_ids"]])
                          for loc in job["locations"]],
            "source_published_at": None,
            "source_updated_at": None,
            "deadline_at": v["deadline_at"]["value"],
            "first_seen_at": v["first_seen_at"]["value"],
            "last_seen_at": _stamp(anchor),
            "active_state": job["active_state"],
            "discovery_kind": "synthetic_scenario",
            "facts": {
                "skills": [{"value": s["value"], "evidence_ids": [s["evidence_id"]]} for s in v["skills"]],
                "experience": [{"value": d.statement("experience-months"),
                                "evidence_ids": [v["experience_months"]["evidence_id"]]}],
                "education": [
                    {"value": d.statement("degree-level"), "evidence_ids": [v["degree_level"]["evidence_id"]]},
                    {"value": d.statement("fields"), "evidence_ids": [v["fields_of_study"]["evidence_id"]]},
                ],
                "role_family": {"value": v["role_family"]["value"],
                                "evidence_ids": [v["role_family"]["evidence_id"]]},
                "requirements": d.requirements,
            },
            "evidence": evidence,
            "extraction": None,
        })
    return {
        "schema_version": faithful["schema_version"],
        "snapshot_id": SNAPSHOT_ID,
        "created_at": _stamp(anchor),
        "jobs": jobs,
        "documents": documents,
        "source_manifest": [{
            "source": SOURCE,
            "source_ref": f"normalization:{rules['normalization_version']}",
            "retrieved_at": _stamp(anchor),
            "record_count": len(jobs),
            "redistribution_allowed": None,
        }],
        "quarantine": [],
    }


def _dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def render() -> dict[Path, str]:
    """Every output file and its exact text."""
    snapshot, parameters, provenance = build(
        _load(FAITHFUL_SNAPSHOT), _load(FAITHFUL_PARAMETERS), _load(RULES_PATH), _load(SKILLS_PATH))
    # Round-trip through the contract so the file holds its canonical form.
    snapshot = JobSnapshot.model_validate(snapshot).model_dump(mode="json")
    parameters = JobParameterSet.model_validate(parameters).model_dump(mode="json")
    return {SNAPSHOT_PATH: _dump(snapshot), PARAMETERS_PATH: _dump(parameters),
            PROVENANCE_PATH: _dump(provenance)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="Fail if a committed file differs.")
    args = parser.parse_args(argv)
    outputs = render()
    if args.check:
        stale = [str(p.relative_to(ROOT)) for p, text in outputs.items()
                 if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            print("Stale: " + ", ".join(stale))
            return 1
        print("Up to date.")
        return 0
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
