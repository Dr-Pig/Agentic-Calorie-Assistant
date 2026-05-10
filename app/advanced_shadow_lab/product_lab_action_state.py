from __future__ import annotations

from typing import Any, Mapping


EMPTY_STATE = {
    "artifact_type": "advanced_product_lab_action_state",
    "artifact_schema_version": "1.0",
    "status": "pass",
    "active_pending_intake_draft_ids": [],
    "active_pending_intake_source_refs": [],
    "rescue_commit_pending_count": 0,
    "rescue_commit_source_refs": [],
    "dismissed_rescue_instance_count": 0,
    "dismissed_rescue_source_refs": [],
    "requested_rescue_next_signals": [],
    "canonical_product_mutation_allowed": False,
    "durable_product_memory_written": False,
    "served_to_mainline_user": False,
    "blockers": [],
}


def empty_product_lab_action_state() -> dict[str, Any]:
    return {
        **dict(EMPTY_STATE),
        "active_pending_intake_draft_ids": [],
        "active_pending_intake_source_refs": [],
        "rescue_commit_source_refs": [],
        "dismissed_rescue_source_refs": [],
        "requested_rescue_next_signals": [],
        "blockers": [],
    }


def reduce_product_lab_action_state(
    *,
    prior_state: Mapping[str, Any],
    action_outcomes: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    delta = turn_action_state_delta(action_outcomes)
    next_state = _merge_state(prior_state, delta)
    return next_state, delta


def turn_action_state_delta(
    action_outcomes: list[Mapping[str, Any]],
) -> dict[str, Any]:
    intake = _pending_intake_packets(action_outcomes)
    rescue = _rescue_decision_packets(action_outcomes)
    return {
        "artifact_type": "advanced_product_lab_action_state_delta",
        "status": "pass",
        "pending_intake_draft_ids_added": [
            str(item.get("primary_candidate_id") or "") for item in intake
        ],
        "pending_intake_source_refs_added": _refs(intake),
        "rescue_commit_pending_added": sum(
            1 for item in rescue if item.get("lab_rescue_commit_pending") is True
        ),
        "rescue_commit_source_refs_added": _refs(
            [
                item
                for item in rescue
                if item.get("lab_rescue_commit_pending") is True
            ]
        ),
        "dismissed_rescue_instance_added": sum(
            1
            for item in rescue
            if item.get("proposal_instance_dismissed") is True
        ),
        "dismissed_rescue_source_refs_added": _refs(
            [
                item
                for item in rescue
                if item.get("proposal_instance_dismissed") is True
            ]
        ),
        "requested_rescue_next_signals_added": [
            str(item.get("requested_next_signal") or "")
            for item in rescue
            if item.get("lab_rescue_commit_pending") is not True
        ],
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "served_to_mainline_user": False,
        "blockers": [],
    }


def _merge_state(
    prior_state: Mapping[str, Any],
    delta: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **empty_product_lab_action_state(),
        "active_pending_intake_draft_ids": _append_unique(
            prior_state.get("active_pending_intake_draft_ids"),
            delta.get("pending_intake_draft_ids_added"),
        ),
        "active_pending_intake_source_refs": _append_unique(
            prior_state.get("active_pending_intake_source_refs"),
            delta.get("pending_intake_source_refs_added"),
        ),
        "rescue_commit_pending_count": int(
            prior_state.get("rescue_commit_pending_count") or 0
        )
        + int(delta.get("rescue_commit_pending_added") or 0),
        "rescue_commit_source_refs": _append_unique(
            prior_state.get("rescue_commit_source_refs"),
            delta.get("rescue_commit_source_refs_added"),
        ),
        "dismissed_rescue_instance_count": int(
            prior_state.get("dismissed_rescue_instance_count") or 0
        )
        + int(delta.get("dismissed_rescue_instance_added") or 0),
        "dismissed_rescue_source_refs": _append_unique(
            prior_state.get("dismissed_rescue_source_refs"),
            delta.get("dismissed_rescue_source_refs_added"),
        ),
        "requested_rescue_next_signals": _append_unique(
            prior_state.get("requested_rescue_next_signals"),
            delta.get("requested_rescue_next_signals_added"),
        ),
    }


def _pending_intake_packets(items: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return _packets(items, "pending_intake_draft_packet")


def _rescue_decision_packets(items: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return _packets(items, "rescue_action_decision_packet")


def _packets(items: list[Mapping[str, Any]], key: str) -> list[Mapping[str, Any]]:
    packets: list[Mapping[str, Any]] = []
    for item in items:
        packet = _mapping(item.get(key))
        if packet.get("status") == "pass":
            packets.append(packet)
    return packets


def _refs(items: list[Mapping[str, Any]]) -> list[str]:
    return [str(ref) for item in items for ref in item.get("source_refs") or []]


def _append_unique(existing: Any, added: Any) -> list[str]:
    result: list[str] = []
    for value in [*(existing or []), *(added or [])]:
        text = str(value)
        if text and text not in result:
            result.append(text)
    return result


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "empty_product_lab_action_state",
    "reduce_product_lab_action_state",
    "turn_action_state_delta",
]
