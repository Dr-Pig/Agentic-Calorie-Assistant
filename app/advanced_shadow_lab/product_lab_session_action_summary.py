from __future__ import annotations

from typing import Any, Mapping


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
    }


def turn_chat_action_summary(
    action_outcomes: list[Mapping[str, Any]],
) -> dict[str, Any]:
    draft_packets = _pending_draft_packets(action_outcomes)
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


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "session_chat_action_summary",
    "turn_chat_action_summary",
]
