from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_calibration_action_summary import (
    session_calibration_action_summary,
    turn_calibration_action_summary,
)


def session_chat_action_summary(
    turn_summaries: list[Mapping[str, Any]],
) -> dict[str, Any]:
    action_types = [
        str(outcome_type)
        for item in turn_summaries
        for outcome_type in item.get("lab_chat_action_outcome_types") or []
    ]
    action_blockers = [
        str(blocker)
        for item in turn_summaries
        for blocker in item.get("lab_chat_action_blockers") or []
    ]
    return {
        "lab_chat_action_outcome_count": sum(
            int(item.get("lab_chat_action_outcome_count") or 0)
            for item in turn_summaries
        ),
        "lab_chat_action_outcome_types": action_types,
        "lab_chat_action_blockers": action_blockers,
        "lab_chat_action_canonical_mutation_allowed": any(
            item.get("lab_chat_action_canonical_mutation_allowed") is True
            for item in turn_summaries
        ),
        "lab_pending_intake_draft_count": sum(
            int(item.get("lab_pending_intake_draft_count") or 0)
            for item in turn_summaries
        ),
        "lab_pending_intake_draft_candidate_ids": [
            str(candidate_id)
            for item in turn_summaries
            for candidate_id in item.get("lab_pending_intake_draft_candidate_ids") or []
        ],
        "lab_pending_intake_draft_source_refs": [
            str(source_ref)
            for item in turn_summaries
            for source_ref in item.get("lab_pending_intake_draft_source_refs") or []
        ],
        "lab_pending_intake_draft_canonical_mutation_allowed": any(
            item.get("lab_pending_intake_draft_canonical_mutation_allowed") is True
            for item in turn_summaries
        ),
        "lab_pending_intake_terminal_count": sum(
            int(item.get("lab_pending_intake_terminal_count") or 0)
            for item in turn_summaries
        ),
        "lab_pending_intake_terminal_states": [
            str(state)
            for item in turn_summaries
            for state in item.get("lab_pending_intake_terminal_states") or []
        ],
        "lab_rescue_action_decision_count": sum(
            int(item.get("lab_rescue_action_decision_count") or 0)
            for item in turn_summaries
        ),
        "lab_rescue_action_decision_kinds": [
            str(kind)
            for item in turn_summaries
            for kind in item.get("lab_rescue_action_decision_kinds") or []
        ],
        "lab_rescue_action_decision_source_refs": [
            str(source_ref)
            for item in turn_summaries
            for source_ref in item.get("lab_rescue_action_decision_source_refs") or []
        ],
        "lab_rescue_commit_pending_count": sum(
            int(item.get("lab_rescue_commit_pending_count") or 0)
            for item in turn_summaries
        ),
        "lab_rescue_action_canonical_mutation_allowed": any(
            item.get("lab_rescue_action_canonical_mutation_allowed") is True
            for item in turn_summaries
        ),
        **session_calibration_action_summary(turn_summaries),
    }


def turn_chat_action_summary(
    action_outcomes: list[Mapping[str, Any]],
) -> dict[str, Any]:
    draft_packets = _pending_draft_packets(action_outcomes)
    terminal_packets = _pending_terminal_packets(action_outcomes)
    rescue_decisions = _rescue_decision_packets(action_outcomes)
    return {
        "lab_chat_action_outcome_count": len(action_outcomes),
        "lab_chat_action_event_ids": [
            str(item.get("event_id") or "") for item in action_outcomes
        ],
        "lab_chat_action_outcome_types": [
            str(item.get("outcome_type") or "") for item in action_outcomes
        ],
        "lab_chat_action_blockers": [
            str(blocker)
            for item in action_outcomes
            for blocker in item.get("blockers") or []
        ],
        "lab_chat_action_canonical_mutation_allowed": any(
            item.get("canonical_product_mutation_allowed") is True
            for item in action_outcomes
        ),
        "lab_pending_intake_draft_count": len(draft_packets),
        "lab_pending_intake_draft_candidate_ids": [
            str(item.get("primary_candidate_id") or "") for item in draft_packets
        ],
        "lab_pending_intake_draft_source_refs": [
            str(source_ref)
            for item in draft_packets
            for source_ref in item.get("source_refs") or []
        ],
        "lab_pending_intake_draft_canonical_mutation_allowed": any(
            item.get("canonical_product_mutation_allowed") is True
            for item in draft_packets
        ),
        "lab_pending_intake_terminal_count": len(terminal_packets),
        "lab_pending_intake_terminal_states": [
            str(item.get("terminal_state") or "") for item in terminal_packets
        ],
        "lab_rescue_action_decision_count": len(rescue_decisions),
        "lab_rescue_action_decision_kinds": [
            str(item.get("decision_kind") or "") for item in rescue_decisions
        ],
        "lab_rescue_action_decision_source_refs": [
            str(source_ref)
            for item in rescue_decisions
            for source_ref in item.get("source_refs") or []
        ],
        "lab_rescue_commit_pending_count": sum(
            1
            for item in rescue_decisions
            if item.get("lab_rescue_commit_pending") is True
        ),
        "lab_rescue_action_canonical_mutation_allowed": any(
            item.get("canonical_product_mutation_allowed") is True
            for item in rescue_decisions
        ),
        **turn_calibration_action_summary(action_outcomes),
    }


def _pending_draft_packets(
    action_outcomes: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    drafts: list[Mapping[str, Any]] = []
    for outcome in action_outcomes:
        draft = _mapping(outcome.get("pending_intake_draft_packet"))
        if draft.get("status") == "pass":
            drafts.append(draft)
    return drafts


def _pending_terminal_packets(
    action_outcomes: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    packets: list[Mapping[str, Any]] = []
    for outcome in action_outcomes:
        packet = _mapping(outcome.get("pending_intake_lifecycle_packet"))
        if packet.get("status") == "pass":
            packets.append(packet)
    return packets


def _rescue_decision_packets(
    action_outcomes: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    decisions: list[Mapping[str, Any]] = []
    for outcome in action_outcomes:
        decision = _mapping(outcome.get("rescue_action_decision_packet"))
        if decision.get("status") == "pass":
            decisions.append(decision)
    return decisions


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "session_chat_action_summary",
    "turn_chat_action_summary",
]
