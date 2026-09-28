"""Profile fit for the normalized synthetic demo: skills, education, experience.

A deterministic scorer, approved for the normalized demo only (not a
production or empirically validated profile-fit model):

    profile fit = 0.50 x skills + 0.25 x education/field + 0.25 x experience

each part on 0-100:

- skills: the share of the job's skills the candidate has, both read through
  the one shared skills vocabulary (``config/skills_vocabulary.json``);
- education/field: 100 when the degree and the field are both compatible, 50
  when exactly one is, 0 when neither is;
- experience: ``min(candidate months / required months, 1) x 100``, and 100
  when the job requires none.

Candidate facts are read, never assumed: skills from the candidate's own
skill records, degree level, field and months of experience from the
candidate's known eligibility answers. When a part needs a candidate fact
that is missing, the part is unavailable and so is the profile fit, which
the ranking pipeline then treats as a missing factor. Nothing becomes zero
for lack of data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from oi.contracts import CandidateProfile
from oi.intelligence.eligibility.catalogue import DEGREE_LEVELS
from oi.intelligence.eligibility.inputs import known_answer

#: The approved normalized-demo profile-fit parts and their weights.
WEIGHTS = {"skills": 0.50, "education_field": 0.25, "experience": 0.25}

SKILLS_VOCABULARY_PATH = Path(__file__).resolve().parents[3] / "config" / "skills_vocabulary.json"


def load_skills_vocabulary(path: Path = SKILLS_VOCABULARY_PATH) -> tuple[str, ...]:
    """The shared skills vocabulary, in file order."""
    return tuple(entry["name"] for entry in json.loads(path.read_text(encoding="utf-8"))["skills"])


def skill_named(skill: str, texts: Iterable[str]) -> bool:
    """Whether any of `texts` names `skill`, compared without case.

    The project's one rule for spotting a vocabulary skill in CV text: the
    same text, or one containing the other when the shorter has more than two
    characters ("Financial modelling in Excel" names Excel).
    """
    k = skill.lower()
    return any(k == s or (len(s) > 2 and s in k) or (len(k) > 2 and k in s)
               for s in (t.lower() for t in texts))


def vocabulary_skills(texts: Sequence[str], vocabulary: Sequence[str]) -> frozenset[str]:
    """The vocabulary skills that `texts` name."""
    return frozenset(skill for skill in vocabulary if skill_named(skill, texts))


@dataclass(frozen=True)
class CandidateFacts:
    """What profile fit reads about the candidate; None means not stated."""

    #: The vocabulary skills the candidate's skill records name; None when the
    #: candidate has no skill records at all.
    skills: frozenset[str] | None
    degree_level: str | None
    field_of_study: str | None
    experience_months: int | None


def candidate_facts(candidate: CandidateProfile, vocabulary: Sequence[str],
                    skill_texts: Sequence[str] | None = None) -> CandidateFacts:
    """The candidate's facts for profile fit.

    Args:
        candidate: The canonical candidate profile.
        vocabulary: The shared skills vocabulary.
        skill_texts: The candidate's skill records, when they are held outside
            `candidate` (for example the extracted CV's). Defaults to
            ``candidate.skills``.
    """
    texts = [s.value for s in candidate.skills] if skill_texts is None else list(skill_texts)
    degree = known_answer(candidate, "HC_DEGREE_LEVEL", "degree_level")
    field = known_answer(candidate, "HC_FIELD_OF_STUDY", "field_of_study")
    months = known_answer(candidate, "HC_MIN_EXPERIENCE", "prior_experience_months")
    return CandidateFacts(
        skills=vocabulary_skills(texts, vocabulary) if texts else None,
        degree_level=degree.value if degree else None,
        field_of_study=field.value if field else None,
        experience_months=months.value if months else None,
    )


@dataclass(frozen=True)
class JobProfile:
    """What profile fit reads about the job (the normalized profile inputs)."""

    skills: tuple[str, ...]
    degree_level: str
    fields_of_study: tuple[str, ...]
    any_field: bool
    experience_months: int


@dataclass(frozen=True)
class ProfileFit:
    """Profile fit and its parts, each 0-100, or None when unavailable."""

    skills: float | None
    education_field: float | None
    experience: float | None
    #: The weighted profile fit, 0-100; None unless every part is available.
    score: float | None
    matched_skills: tuple[str, ...]
    #: The parts that were unavailable, with the candidate fact they lacked.
    missing: tuple[str, ...]


def skills_score(candidate: CandidateFacts, job: JobProfile) -> float | None:
    if candidate.skills is None:
        return None
    matched = [s for s in job.skills if s in candidate.skills]
    return 100.0 * len(matched) / len(job.skills)


def education_score(candidate: CandidateFacts, job: JobProfile) -> float | None:
    if candidate.degree_level is None or candidate.field_of_study is None:
        return None
    degree_ok = DEGREE_LEVELS.index(candidate.degree_level) >= DEGREE_LEVELS.index(job.degree_level)
    field_ok = job.any_field or candidate.field_of_study in job.fields_of_study
    return {2: 100.0, 1: 50.0, 0: 0.0}[degree_ok + field_ok]


def experience_score(candidate: CandidateFacts, job: JobProfile) -> float | None:
    if job.experience_months == 0:
        return 100.0
    if candidate.experience_months is None:
        return None
    return 100.0 * min(candidate.experience_months / job.experience_months, 1.0)


def profile_fit(candidate: CandidateFacts, job: JobProfile) -> ProfileFit:
    """Profile fit of one job for one candidate."""
    parts = {
        "skills": skills_score(candidate, job),
        "education_field": education_score(candidate, job),
        "experience": experience_score(candidate, job),
    }
    missing = tuple(name for name, value in parts.items() if value is None)
    score = None if missing else sum(WEIGHTS[name] * value for name, value in parts.items())
    matched = tuple(s for s in job.skills if candidate.skills and s in candidate.skills)
    return ProfileFit(parts["skills"], parts["education_field"], parts["experience"], score, matched, missing)
