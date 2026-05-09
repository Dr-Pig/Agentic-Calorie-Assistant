from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.memory.application.long_term_context_shadow.lab_product_shadow_inputs import (
    reviewed_consumer_shadow_input,
    reviewed_lab_memory_triggers,
    reviewed_lab_rescue_packets,
)
from app.memory.application.long_term_context_shadow.lab_store import (
    _memory_lab_review_loop_state_artifact,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.long_term_context_shadow.reviewed_product_replay"
)

_INACTIVE_REVIEW_GROUPS = ("suppressed", "deleted", "expired", "rejected")


def reviewed_memory_product_loop_replay(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    review_state = _memory_lab_review_loop_state_artifact(fixture, candidates)
    blockers = list(review_state.get("blockers") or [])
    if blockers:
        return {
            **_base_replay(),
            "status": "blocked",
            "review_surface_status": "blocked",
            "blockers": blockers,
            "review_state_counts": _empty_review_state_counts(),
            "excluded_candidate_ids_by_reason": {},
            "recommendation_reviewed_record_ids": [],
            "proactive_reviewed_trigger_candidate_ids": [],
            "rescue_reviewed_packet_candidate_ids": [],
        }

    recommendation = reviewed_consumer_shadow_input(
        fixture,
        candidates,
        "recommendation",
    )
    proactive = reviewed_consumer_shadow_input(fixture, candidates, "proactive_context")
    rescue = reviewed_consumer_shadow_input(fixture, candidates, "rescue_context")
    proactive_triggers = reviewed_lab_memory_triggers(proactive)
    rescue_packets = reviewed_lab_rescue_packets(rescue)

    return {
        **_base_replay(),
        "status": "generated",
        "review_surface_status": str(
            review_state["lab_review_correction_surface"]["status"]
        ),
        "blockers": [],
        "review_state_counts": _review_state_counts(review_state),
        "excluded_candidate_ids_by_reason": _excluded_candidate_ids_by_reason(
            review_state
        ),
        "recommendation_reviewed_record_ids": recommendation[
            "reviewed_lab_record_ids"
        ],
        "proactive_reviewed_trigger_candidate_ids": [
            trigger["source_candidate_id"] for trigger in proactive_triggers
        ],
        "rescue_reviewed_packet_candidate_ids": [
            packet["source_candidate_id"] for packet in rescue_packets
        ],
    }


def _base_replay() -> dict[str, Any]:
    return {
        "replay_id": "reviewed_memory_product_loop_replay",
        "source_review_artifact": "memory_lab_review_loop_state",
        "expected_user_value": "reviewed_memory_feedback_loop_before_activation",
        "recommendation_served": False,
        "scheduler_activated": False,
        "rescue_committed": False,
        "durable_memory_written": False,
        "manager_context_packet_written": False,
        "runtime_effect_allowed": False,
    }


def _empty_review_state_counts() -> dict[str, int]:
    return {
        "active": 0,
        "suppressed": 0,
        "deleted": 0,
        "expired": 0,
        "rejected": 0,
    }


def _review_state_counts(review_state: dict[str, Any]) -> dict[str, int]:
    surface = review_state["lab_review_correction_surface"]
    groups = surface.get("review_state_groups") or {}
    return {
        "active": len(groups.get("active") or []),
        **{key: len(groups.get(key) or []) for key in _INACTIVE_REVIEW_GROUPS},
    }


def _excluded_candidate_ids_by_reason(
    review_state: dict[str, Any],
) -> dict[str, list[str]]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for record in review_state.get("lab_memory_records") or []:
        reason = record.get("excluded_from_lab_context_reason")
        if reason:
            grouped[str(reason)].append(str(record["source_candidate_id"]))
    return {reason: sorted(candidate_ids) for reason, candidate_ids in sorted(grouped.items())}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "reviewed_memory_product_loop_replay"]
