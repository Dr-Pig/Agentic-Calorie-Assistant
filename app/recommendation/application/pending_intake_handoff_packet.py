from __future__ import annotations

from typing import Any, Mapping


FORBIDDEN_SIDE_EFFECTS = [
    "meal_thread_mutation",
    "ledger_entry_creation",
    "day_budget_mutation",
    "durable_memory_write",
]


def build_recommendation_pending_intake_handoff(
    *,
    primary_candidate: Mapping[str, Any],
    ux_packet: Mapping[str, Any],
    artifact_type: str = "recommendation_pending_intake_handoff_packet",
) -> dict[str, Any]:
    candidate_id = str(primary_candidate.get("candidate_id") or "")
    omitted = not candidate_id
    source_action = _source_log_action(ux_packet)
    return {
        "artifact_type": artifact_type,
        "status": "omitted" if omitted else "pass",
        "contract_scope": "pending_intake_handoff_only",
        "handoff_contract": _handoff_contract(),
        "handoff_state": "no_pending_intake_handoff"
        if omitted
        else "pending_user_intake_confirmation",
        "candidate_id": candidate_id,
        "candidate_snapshot": dict(primary_candidate),
        "offer_action": "log_this",
        "source_ux_action": source_action,
        "lab_intake_intent_created": not omitted,
        "requires_explicit_user_intake_action": True,
        "requires_user_confirmation_before_commit": True,
        "allowed_next_actions": ["confirm_log_this", "edit_before_log", "dismiss"],
        "forbidden_side_effects": list(FORBIDDEN_SIDE_EFFECTS),
        "canonical_commit_requested": False,
        "canonical_product_mutation_allowed": False,
        "served_to_mainline_user": False,
        "meal_thread_mutated": False,
        "intake_committed": False,
        "ledger_entry_created": False,
        "day_budget_mutated": False,
        "durable_product_memory_written": False,
        "source_ux_packet_primary_candidate_id": str(
            ux_packet.get("primary_candidate_id") or ""
        ),
        "omission_reason": "no_qualified_candidate" if omitted else "",
        "blockers": _blockers(candidate_id=candidate_id, source_action=source_action),
    }


def _handoff_contract() -> dict[str, Any]:
    return {
        "contract_scope": "pending_intake_handoff_only",
        "truth_owner": "intake_runtime_after_user_confirmation",
        "recommendation_role": "proposal_only",
        "requires_user_confirmation_before_commit": True,
        "forbidden_side_effects": list(FORBIDDEN_SIDE_EFFECTS),
    }


def _source_log_action(ux_packet: Mapping[str, Any]) -> dict[str, Any]:
    for action in ux_packet.get("actions") or []:
        if isinstance(action, Mapping) and action.get("action") == "log_this":
            return dict(action)
    return {}


def _blockers(*, candidate_id: str, source_action: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if candidate_id and not source_action:
        blockers.append("source_log_action_missing")
    if source_action.get("canonical_commit_requested") is True:
        blockers.append("source_log_action.canonical_commit_requested")
    return blockers


__all__ = ["build_recommendation_pending_intake_handoff"]
