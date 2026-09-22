"""Deterministic eligibility rules.

Work authorisation is decided here, by table lookup, and nowhere else. No
model input reaches this module and none of its outputs depend on one: given
the same facts it always returns the same answer, and every answer names the
rule that produced it.

That separation is the point. A language model may explain what these rules
concluded; it may never conclude it. Getting someone's right to work wrong is
not a ranking error, and "the model said so" is not something a user can check.

The Swiss table for EU/EFTA citizens comes from
design-system/10-ux-architecture.md. This is not legal advice, and the rules
carry a version so an outcome can be traced to the text it was read from.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from oi.contracts import Evidence, ReqStatus, Source

#: Bump when a rule changes. Shown in "How we know" alongside the outcome.
RULES_VERSION = "2026-09-22"

#: Countries whose citizens move freely within the EU/EFTA area.
_EU_EFTA = frozenset(
    {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE",
        "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
        "RO", "SK", "SI", "ES", "SE",          # EU
        "IS", "LI", "NO", "CH",                # EFTA
    }
)


@dataclass(frozen=True)
class RuleOutcome:
    """What a rule concluded, and the evidence for it.

    `evidence` is None only when the rule could not fire for want of a fact.
    In that case `status` is "confirm": we ask rather than assume.
    """

    status: ReqStatus
    explanation: str
    evidence: Optional[Evidence] = None


def _rule_evidence(explanation: str, where: str) -> Evidence:
    """Wrap a rule's conclusion as evidence attributed to RULE."""
    return Evidence(
        text=explanation,
        highlight=None,
        source=Source(kind="RULE", where=f"{where} · rules {RULES_VERSION}"),
    )


def swiss_permit_for_eu_citizen(contract_months: Optional[int]) -> RuleOutcome:
    """Apply the Swiss permit table for an EU/EFTA citizen.

    | Contract length      | Outcome                                |
    |----------------------|----------------------------------------|
    | <= 3 months          | No permit needed                       |
    | > 3 and < 12 months  | L permit (EU/EFTA), for the contract   |
    | >= 12 months         | B permit (EU/EFTA), valid 5 years      |

    Args:
        contract_months: Contract length in months, or None if the posting
            does not say.

    Returns:
        A met outcome for any of the three bands. When the length is unknown,
        a "confirm" outcome with no evidence -- we do not pick a band, because
        that would be inventing a fact about someone's legal status.

    Raises:
        ValueError: If `contract_months` is zero or negative.
    """
    if contract_months is None:
        return RuleOutcome(
            status="confirm",
            explanation="Contract length is not stated in this posting.",
        )

    if contract_months <= 0:
        raise ValueError(
            f"Contract length must be a positive number of months, "
            f"got {contract_months}."
        )

    if contract_months <= 3:
        explanation = "No permit needed for ≤ 3 months"
        where = "CH · EU/EFTA · contract ≤ 3 months"
    elif contract_months < 12:
        explanation = "L permit (EU/EFTA) for the contract length"
        where = "CH · EU/EFTA · contract 3–12 months"
    else:
        explanation = "B permit (EU/EFTA), valid 5 years"
        where = "CH · EU/EFTA · contract ≥ 12 months"

    return RuleOutcome(
        status="met",
        explanation=explanation,
        evidence=_rule_evidence(explanation, where),
    )


def work_authorisation(
    citizenship: Optional[str],
    country: str,
    contract_months: Optional[int] = None,
) -> RuleOutcome:
    """Decide whether the candidate may work in `country`.

    Args:
        citizenship: ISO 3166-1 alpha-2 code of the declared citizenship, or
            None if we have not been told.
        country: ISO 3166-1 alpha-2 code of where the role is based.
        contract_months: Contract length, where the posting states it.

    Returns:
        A RuleOutcome. Absent a rule for the pair, the status is "confirm":
        having no rule means we do not know, which is different from knowing
        the answer is no.
    """
    citizenship = (citizenship or "").upper() or None
    country = country.upper()

    if citizenship is None:
        return RuleOutcome(
            status="confirm",
            explanation="Citizenship is not stated in your CV.",
        )

    # Free movement inside the EU/EFTA area, except Switzerland, which runs
    # its own permit regime even for EU citizens.
    if country in _EU_EFTA and country != "CH" and citizenship in _EU_EFTA:
        explanation = "EU/EFTA citizen — free movement applies"
        return RuleOutcome(
            status="met",
            explanation=explanation,
            evidence=_rule_evidence(
                explanation, f"{country} · EU/EFTA citizen"
            ),
        )

    if country == "CH" and citizenship in _EU_EFTA:
        return swiss_permit_for_eu_citizen(contract_months)

    # No rule covers this pair yet. Ask; never assume either way.
    return RuleOutcome(
        status="confirm",
        explanation=(
            f"We have no work-authorisation rule for {citizenship} "
            f"citizens in {country} yet."
        ),
    )
