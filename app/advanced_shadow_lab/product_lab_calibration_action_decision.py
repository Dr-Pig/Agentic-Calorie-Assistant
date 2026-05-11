from __future__ import annotations

from typing import Any, Mapping


COMMIT_ACTIONS = {"accept_calibration_proposal"}
NON_COMMIT_DECISIONS = {
    "dismiss_calibration_proposal": "dismiss_calibration_proposal_lab",
    "view_calibration_alternatives": "show_calibration_alternatives_lab",
}


def build_calibration_action_decision_packet(
    *,
    message: Mapping[str, Any],
    action: str,
) -> dict[str, Any]:
    proposal = _mapping(message.get("calibration_proposal"))
    card = _mapping(proposal.get("proposal_card"))
    blockers = _blockers(message=message, proposal=proposal, card=card, action=action)
    applied = action in COMMIT_ACTIONS and not blockers
    dismissed = action == "dismiss_calibration_proposal" and not blockers
    return {
        "artifact_type": "advanced_product_lab_calibration_action_decision_packet",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "decision_kind": _decision_kind(action),
        "action": action,
        "source_message_id": str(message.get("message_id") or ""),
        "source_candidate_id": str(message.get("candidate_id") or ""),
        "proposal_card_snapshot": dict(card),
        "lab_body_plan_before": _before_body_plan(card),
        "lab_body_plan_after": _after_body_plan(proposal, card, applied=applied),
        "lab_calibration_effect_applied": applied,
        "proposal_instance_dismissed": dismissed,
        "requested_next_signal": _requested_next_signal(action),
        "canonical_commit_requested": proposal.get("canonical_commit_requested") is True,
        "proposal_committed": False,
        "body_plan_mutated": False,
        "day_budget_mutated": False,
        "served_to_mainline_user": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "source_refs": _source_refs(message, proposal, card),
        "blockers": blockers,
    }


def _blockers(
    *,
    message: Mapping[str, Any],
    proposal: Mapping[str, Any],
    card: Mapping[str, Any],
    action: str,
) -> list[str]:
    blockers: list[str] = []
    if action not in COMMIT_ACTIONS and action not in NON_COMMIT_DECISIONS:
        blockers.append(f"calibration_action.unsupported:{action}")
    if not card:
        blockers.append("calibration_proposal.proposal_card_missing")
    if action in COMMIT_ACTIONS and proposal.get("canonical_commit_requested") is True:
        blockers.append("calibration_proposal.canonical_commit_requested")
    if message.get("canonical_mutation_requested") is True:
        blockers.append("chat_message.canonical_mutation_requested")
    return blockers


def _decision_kind(action: str) -> str:
    if action in COMMIT_ACTIONS:
        return "apply_calibration_effect_lab"
    return NON_COMMIT_DECISIONS.get(action, "unsupported_calibration_action")


def _before_body_plan(card: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "daily_budget_kcal": _int(card.get("previous_daily_budget_kcal")),
        "recommended_target_kcal": _int(card.get("previous_daily_budget_kcal")),
    }


def _after_body_plan(
    proposal: Mapping[str, Any],
    card: Mapping[str, Any],
    *,
    applied: bool,
) -> dict[str, Any]:
    if applied:
        return dict(_mapping(proposal.get("lab_body_plan_preview")))
    return _before_body_plan(card)


def _requested_next_signal(action: str) -> str:
    if action == "dismiss_calibration_proposal":
        return "new_qualified_body_trend_or_user_reopens_calibration"
    if action == "view_calibration_alternatives":
        return "user_reviews_hidden_calibration_alternatives"
    return "explicit_calibration_acceptance"


def _source_refs(
    message: Mapping[str, Any],
    proposal: Mapping[str, Any],
    card: Mapping[str, Any],
) -> list[str]:
    refs = [
        f"chat_message:{message.get('message_id') or ''}",
        f"chat_candidate:{message.get('candidate_id') or ''}",
        f"calibration_artifact:{proposal.get('source_calibration_artifact_type') or ''}",
        f"calibration_proposal_card:{card.get('proposal_family') or ''}",
    ]
    return [ref for ref in refs if not ref.endswith(":")]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = ["build_calibration_action_decision_packet"]
