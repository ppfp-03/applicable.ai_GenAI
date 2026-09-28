"""One pure function per hard constraint, registered by constraint ID."""

from __future__ import annotations

from oi.intelligence.eligibility.rules import (
    degree_level,
    field_of_study,
    grad_window,
    language,
    location,
    min_experience,
    student_status,
    work_auth,
)
from oi.intelligence.eligibility.rules.base import RuleFn

#: The registry the engine dispatches through. Must match the catalogue.
RULES: dict[str, RuleFn] = {
    "HC_LOCATION": location.evaluate,
    "HC_WORK_AUTH": work_auth.evaluate,
    "HC_STUDENT_STATUS": student_status.evaluate,
    "HC_GRAD_WINDOW": grad_window.evaluate,
    "HC_DEGREE_LEVEL": degree_level.evaluate,
    "HC_FIELD_OF_STUDY": field_of_study.evaluate,
    "HC_LANGUAGE": language.evaluate,
    "HC_MIN_EXPERIENCE": min_experience.evaluate,
}
