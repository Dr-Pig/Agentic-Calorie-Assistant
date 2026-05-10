from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.ux_acceptance_coverage import REQUIRED_UX_JOURNEY_IDS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.journey_terminal_contract"
)
JOURNEY_OUTPUT_CONTRACTS = {
    "F": (
        "same_day_rescue_coaching_hook",
        "rescue",
        "open_rescue_discussion",
        False,
    ),
    "F2": (
        "planned_event_rescue_negotiation_packet",
        "rescue",
        "review_planned_event_adjustment",
        True,
    ),
    "I": (
        "calibration_proposal_review_packet",
        "calibration",
        "review_calibration_proposal",
        True,
    ),
    "L": (
        "recommendation_offer_pending_intent_packet",
        "recommendation",
        "review_recommendation_offer",
        False,
    ),
    "M": (
        "memory_review_adjusted_recommendation_packet",
        "recommendation",
        "review_memory_signal",
        False,
    ),
    "N": (
        "proactive_no_send_intervention_packet",
        "proactive",
        "review_no_send_candidate",
        False,
    ),
}


def expected_terminal_output(journey_id: str) -> dict[str, Any]:
    output_kind, workflow_family, primary_affordance, explicit_accept = (
        JOURNEY_OUTPUT_CONTRACTS[journey_id]
    )
    return {
        "status": "pass",
        "output_kind": output_kind,
        "workflow_family": workflow_family,
        "surface": "chat",
        "chat_first": True,
        "control_contract": {
            "primary_affordance": primary_affordance,
            "dismiss_available": True,
            "requires_explicit_acceptance": explicit_accept,
            "served_to_user": False,
            "delivery_attempted": False,
            "canonical_mutation_requested": False,
            "scheduler_enqueued": False,
        },
    }


def terminal_output_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    by_id = {str(row.get("journey_id") or ""): row for row in rows}
    missing = [
        journey_id
        for journey_id in REQUIRED_UX_JOURNEY_IDS
        if journey_id in by_id and not _output(by_id.get(journey_id))
    ]
    kind_mismatch = [journey_id for journey_id in REQUIRED_UX_JOURNEY_IDS if _kind_mismatch(journey_id, by_id)]
    family_mismatch = [journey_id for journey_id in REQUIRED_UX_JOURNEY_IDS if _family_mismatch(journey_id, by_id)]
    return {
        "output_kind_by_journey": {
            journey_id: str(_output(by_id.get(journey_id)).get("output_kind") or "")
            for journey_id in REQUIRED_UX_JOURNEY_IDS
            if _output(by_id.get(journey_id))
        },
        "workflow_family_by_journey": {
            journey_id: str(_output(by_id.get(journey_id)).get("workflow_family") or "")
            for journey_id in REQUIRED_UX_JOURNEY_IDS
            if _output(by_id.get(journey_id))
        },
        "missing_terminal_output_journey_ids": missing,
        "output_kind_mismatch_journey_ids": kind_mismatch,
        "workflow_family_mismatch_journey_ids": family_mismatch,
    }


def terminal_output_status(output_summary: Mapping[str, Any]) -> str:
    blockers = (
        output_summary.get("missing_terminal_output_journey_ids")
        or output_summary.get("output_kind_mismatch_journey_ids")
        or output_summary.get("workflow_family_mismatch_journey_ids")
    )
    return "blocked" if blockers else "pass"


def _kind_mismatch(journey_id: str, by_id: Mapping[str, Mapping[str, Any]]) -> bool:
    output = _output(by_id.get(journey_id))
    return bool(output) and output.get("output_kind") != JOURNEY_OUTPUT_CONTRACTS[journey_id][0]


def _family_mismatch(journey_id: str, by_id: Mapping[str, Mapping[str, Any]]) -> bool:
    output = _output(by_id.get(journey_id))
    return bool(output) and output.get("workflow_family") != JOURNEY_OUTPUT_CONTRACTS[journey_id][1]


def _output(row: Mapping[str, Any] | None) -> Mapping[str, Any]:
    value = row.get("ux_terminal_output") if isinstance(row, Mapping) else None
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "expected_terminal_output",
    "terminal_output_status",
    "terminal_output_summary",
]
