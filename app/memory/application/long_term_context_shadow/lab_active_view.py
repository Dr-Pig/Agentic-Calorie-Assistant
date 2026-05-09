from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.lab_store import (
    _memory_lab_review_loop_state_artifact,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.long_term_context_shadow.lab_active_view"
)

CONSUMER_SPECS: dict[str, tuple[set[str], set[str]]] = {
    "recommendation": (
        {"recommendation", "recommendation_presentation"},
        {
            "food_preference",
            "golden_order",
            "negative_preference",
            "temporary_preference",
            "user_language_pattern",
        },
    ),
    "intake_chat_context": (
        {
            "chat_context",
            "intake_clarification",
            "response_context",
            "response_generation",
            "nutrition_clarify_priority",
        },
        {
            "app_usage_style",
            "food_preference",
            "golden_order",
            "intake_estimation_bias",
            "interaction_preference",
            "negative_preference",
            "temporary_preference",
            "user_language_pattern",
        },
    ),
    "calibration": (
        {"calibration", "intake_risk_tagging", "nutrition_clarify_priority"},
        {"intake_estimation_bias", "logging_adherence_pattern", "pattern"},
    ),
    "calibration_context": (
        {"calibration", "intake_risk_tagging", "nutrition_clarify_priority"},
        {"intake_estimation_bias", "logging_adherence_pattern", "pattern"},
    ),
    "proactive": (
        {"proactive", "proactive_message_style", "recommendation", "rescue_later"},
        {
            "app_usage_style",
            "food_preference",
            "golden_order",
            "interaction_preference",
            "logging_adherence_pattern",
            "negative_preference",
            "pattern",
            "temporary_preference",
        },
    ),
    "proactive_context": (
        {"proactive", "proactive_message_style", "recommendation", "rescue_later"},
        {
            "app_usage_style",
            "food_preference",
            "golden_order",
            "interaction_preference",
            "logging_adherence_pattern",
            "negative_preference",
            "pattern",
            "temporary_preference",
        },
    ),
    "rescue_later": (
        {"rescue_later", "calibration", "proactive"},
        {"intake_estimation_bias", "interaction_preference", "pattern"},
    ),
    "rescue_context": (
        {"rescue_later", "calibration", "proactive"},
        {"intake_estimation_bias", "interaction_preference", "pattern"},
    ),
    "cross_surface_context": (
        {"chat_context", "intake_clarification", "proactive", "response_generation"},
        {"app_usage_style", "interaction_preference", "user_language_pattern"},
    ),
}


def reviewed_lab_context_view(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    state = _memory_lab_review_loop_state_artifact(fixture, candidates)
    records = list(state.get("lab_memory_records") or [])
    active_records = [record for record in records if record["active_in_lab_context"]]
    return {
        "source_artifact_type": "memory_lab_review_loop_state",
        "status": state["status"],
        "lab_isolated": True,
        "runtime_effect_allowed": False,
        "manager_context_injection_allowed": False,
        "blockers": list(state.get("blockers") or []),
        "active_source_candidate_ids": [
            record["source_candidate_id"] for record in active_records
        ],
        "excluded_source_candidate_ids": [
            record["source_candidate_id"]
            for record in records
            if not record["active_in_lab_context"]
        ],
        "consumer_views": {
            consumer_id: _consumer_view(consumer_id, active_records)
            for consumer_id in CONSUMER_SPECS
        },
    }


def empty_consumer_view(consumer_id: str) -> dict[str, Any]:
    return _consumer_view(consumer_id, [])


def reviewed_context_pack_fields(
    pack_id: str,
    reviewed_view: dict[str, Any] | None,
) -> dict[str, Any]:
    if not reviewed_view:
        lab_view = {"active_memory_record_ids": [], "active_records": []}
        return {
            "reviewed_lab_view_status": "not_built",
            "reviewed_lab_context_source_artifact": "not_built",
            "reviewed_lab_record_ids": lab_view["active_memory_record_ids"],
            "reviewed_lab_record_summaries": lab_view["active_records"],
        }
    lab_view = reviewed_view["consumer_views"].get(
        pack_id,
        {"active_memory_record_ids": [], "active_records": []},
    )
    return {
        "reviewed_lab_view_status": str(reviewed_view.get("status")),
        "reviewed_lab_context_source_artifact": str(
            reviewed_view.get("source_artifact_type")
        ),
        "reviewed_lab_record_ids": lab_view["active_memory_record_ids"],
        "reviewed_lab_record_summaries": lab_view["active_records"],
    }


def _consumer_view(
    consumer_id: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    selected = [
        _record_summary(record)
        for record in records
        if _record_allowed(record, *CONSUMER_SPECS[consumer_id])
    ]
    return {
        "consumer_id": consumer_id,
        "active_memory_record_ids": [
            record["memory_record_id"] for record in selected
        ],
        "source_candidate_ids": [
            record["source_candidate_id"] for record in selected
        ],
        "active_records": selected,
        "runtime_effect_allowed": False,
        "manager_context_injection_allowed": False,
    }


def _record_allowed(
    record: dict[str, Any],
    allowed_consumers: set[str],
    allowed_candidate_types: set[str],
) -> bool:
    return (
        record["candidate_type"] in allowed_candidate_types
        and bool(set(record.get("intended_consumers") or []).intersection(allowed_consumers))
    )


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "memory_record_id": record["memory_record_id"],
        "source_candidate_id": record["source_candidate_id"],
        "record_state": record["record_state"],
        "revision": record["revision"],
        "memory_text": record["memory_text"],
        "candidate_type": record["candidate_type"],
        "can_be_runtime_loaded": False,
        "durable_memory_written": False,
        "runtime_effect_allowed": False,
        "manager_context_injection_allowed": False,
        "audit_provenance_retained": record["audit_provenance_retained"],
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "empty_consumer_view",
    "reviewed_context_pack_fields",
    "reviewed_lab_context_view",
]
