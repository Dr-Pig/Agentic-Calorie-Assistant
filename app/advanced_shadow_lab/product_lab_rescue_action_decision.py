from __future__ import annotations

from typing import Any, Mapping


COMMIT_ACTIONS = {"accept_rescue_plan"}
NON_COMMIT_DECISIONS = {
    "dismiss_rescue_plan": "dismiss_current_proposal_instance",
    "request_gentler_plan": "request_gentler_variant",
    "request_shorter_plan": "request_shorter_variant",
    "ask_why_this_plan": "request_explanation",
}


def build_rescue_action_decision_packet(
    *,
    message: Mapping[str, Any],
    action: str,
) -> dict[str, Any]:
    proposal = _mapping(message.get("rescue_proposal"))
    blockers = _blockers(message=message, proposal=proposal, action=action)
    return {
        "artifact_type": "advanced_product_lab_rescue_action_decision_packet",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "decision_kind": _decision_kind(action),
        "action": action,
        "source_message_id": str(message.get("message_id") or ""),
        "source_candidate_id": str(message.get("candidate_id") or ""),
        "handoff_state": str(proposal.get("handoff_state") or ""),
        "proposal_card_snapshot": dict(_mapping(proposal.get("proposal_card"))),
        "guardrail_math_snapshot": dict(_mapping(proposal.get("guardrail_math"))),
        "requires_explicit_rescue_commit": action in COMMIT_ACTIONS,
        "lab_rescue_commit_pending": action in COMMIT_ACTIONS and not blockers,
        "proposal_instance_dismissed": action == "dismiss_rescue_plan" and not blockers,
        "requested_next_signal": _requested_next_signal(action),
        "canonical_commit_requested": proposal.get("canonical_commit_requested") is True,
        "proposal_committed": False,
        "rescue_committed": False,
        "ledger_entry_created": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "served_to_mainline_user": False,
        "durable_product_memory_written": False,
        "source_refs": _source_refs(message, proposal),
        "blockers": blockers,
    }


def _blockers(
    *,
    message: Mapping[str, Any],
    proposal: Mapping[str, Any],
    action: str,
) -> list[str]:
    blockers: list[str] = []
    if action not in COMMIT_ACTIONS and action not in NON_COMMIT_DECISIONS:
        blockers.append(f"rescue_action.unsupported:{action}")
    if proposal.get("handoff_state") != "pending_user_rescue_commit_confirmation":
        blockers.append("rescue_proposal.handoff_state_not_pending_confirmation")
    if not _mapping(proposal.get("proposal_card")):
        blockers.append("rescue_proposal.proposal_card_missing")
    if action in COMMIT_ACTIONS and proposal.get("canonical_commit_requested") is True:
        blockers.append("rescue_proposal.canonical_commit_requested")
    if message.get("canonical_mutation_requested") is True:
        blockers.append("chat_message.canonical_mutation_requested")
    return blockers


def _decision_kind(action: str) -> str:
    if action in COMMIT_ACTIONS:
        return "pending_rescue_commit_confirmation"
    return NON_COMMIT_DECISIONS.get(action, "unsupported_rescue_action")


def _requested_next_signal(action: str) -> str:
    if action == "dismiss_rescue_plan":
        return "material_context_change_or_user_reopens_rescue"
    if action == "request_gentler_plan":
        return "chat_negotiation_requested_gentler_plan"
    if action == "request_shorter_plan":
        return "chat_negotiation_requested_shorter_plan"
    if action == "ask_why_this_plan":
        return "chat_explanation_requested"
    return "explicit_rescue_commit_confirmation"


def _source_refs(message: Mapping[str, Any], proposal: Mapping[str, Any]) -> list[str]:
    refs = [
        f"chat_message:{message.get('message_id') or ''}",
        f"chat_candidate:{message.get('candidate_id') or ''}",
        f"rescue_handoff:{proposal.get('source_pending_rescue_commit_artifact_type') or ''}",
    ]
    card = _mapping(proposal.get("proposal_card"))
    if card:
        refs.append(f"rescue_proposal_card:{card.get('card_kind') or ''}")
    return [ref for ref in refs if not ref.endswith(":")]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_rescue_action_decision_packet"]
