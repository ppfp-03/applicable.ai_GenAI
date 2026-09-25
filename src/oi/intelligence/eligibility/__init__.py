"""Deterministic eligibility engine over the closed hard-constraint catalogue.

Given a CandidateProfile, a JobRecord, the internal RuleCatalogue and the
temporary job-side parameter layer, the engine returns one EligibilityResult.
Every outcome is MET, CONFLICT, UNKNOWN or NOT_APPLICABLE and names the rule
that produced it.

The package reads structured facts only. It calls no model, reads no free
text, keeps no clock and does no ranking or UI work. It is independent of
core/rules.py, which still drives the demo screens.
"""

from oi.intelligence.eligibility.catalogue import RuleCatalogue, load_rule_catalogue
from oi.intelligence.eligibility.engine import assess_eligibility
from oi.intelligence.eligibility.models import (
    EligibilityResult,
    EligibilityStatus,
    EligibilityWarning,
    RuleOutcome,
    RuleStatus,
    UnknownCause,
    WarningCode,
)
from oi.intelligence.eligibility.parameters import JobParameterSet, load_job_parameters

__all__ = [
    "EligibilityResult",
    "EligibilityStatus",
    "EligibilityWarning",
    "JobParameterSet",
    "RuleCatalogue",
    "RuleOutcome",
    "RuleStatus",
    "UnknownCause",
    "WarningCode",
    "assess_eligibility",
    "load_job_parameters",
    "load_rule_catalogue",
]
