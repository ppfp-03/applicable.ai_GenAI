"""Load the demo dataset.

`data/demo.json` stands in for the pipeline's output while the product is
built: the same shapes the rules and ranking layers produce, written by hand
to match design-system/screenshots/. Loading it through the contracts means a
malformed file fails here, loudly, rather than halfway through a render.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from oi.contracts import Opportunity, Question

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "demo.json"


class DemoData:
    """The demo dataset, parsed into contract objects."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.today: str = raw["today"]
        self.profile: dict[str, Any] = raw["profile"]
        self.hours_budget: float = raw["week"]["hours_budget"]
        self.hours_planned: float = raw["week"]["hours_planned"]
        self.changes: str = raw.get("changes", {}).get("text", "")
        self.not_for_now_count: int = raw.get("not_for_now_count", 0)
        self.opportunities: list[Opportunity] = [
            Opportunity.model_validate(o) for o in raw["opportunities"]
        ]
        self.questions: list[Question] = [
            Question.model_validate(q) for q in raw["questions"]
        ]

    def opportunity(self, opportunity_id: str) -> Opportunity:
        """Return one opportunity by id.

        Raises:
            KeyError: If no opportunity carries that id.
        """
        for opp in self.opportunities:
            if opp.id == opportunity_id:
                return opp
        raise KeyError(f"No opportunity with id {opportunity_id!r}.")

    def question(self, question_id: str) -> Question:
        """Return one question by id.

        Raises:
            KeyError: If no question carries that id.
        """
        for q in self.questions:
            if q.id == question_id:
                return q
        raise KeyError(f"No question with id {question_id!r}.")


@lru_cache(maxsize=1)
def load() -> DemoData:
    """Read and parse the demo dataset, once per process."""
    raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    return DemoData(raw)
