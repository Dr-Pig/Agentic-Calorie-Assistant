from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ...shared.domain import ProposalOption
from .calibration_proposal_gate import CalibrationProposalOptionFamily

CalibrationSurfaceAction = Literal[
    "accept_calibration_proposal",
    "defer_calibration_proposal",
    "reject_calibration_proposal",
]

PRIMARY_FAMILY_ORDER: tuple[CalibrationProposalOptionFamily, ...] = (
    "logging_quality_first",
    "monitor_only",
    "budget_adjustment",
    "pace_adjustment",
    "plan_reset",
)
PLAN_CHANGING_FAMILIES = frozenset({"budget_adjustment", "pace_adjustment", "plan_reset"})


@dataclass(frozen=True)
class CalibrationProposalResponseResult:
    surfaced: bool
    proposal_family: str | None
    reply_text: str
    top_option: ProposalOption | None
    backup_options: list[ProposalOption]
    proposal_cards: list[dict[str, Any]]
    quick_actions: list[dict[str, Any]]
    ui_hints: dict[str, Any]
