from __future__ import annotations

from typing import Any

from .canonical_commit_bridge import build_commit_request_candidate, resolve_commit_candidate_target
from ...schemas import EstimatePayload
from app.shared.infra.canonical_persistence import get_legacy_mapping_for_meal_log
from ..infrastructure.meal_log_persistence import persist_text_meal_result


def persist_text_meal_payload(
    *,
    db: Any,
    user: Any,
    latest_log: Any,
    manager_intent: str,
    payload: EstimatePayload,
    raw_input: str,
    request_id: str,
    incoming_user_message_id: int | None,
    conversation_state: Any,
    manager_semantic_decision: dict[str, Any] | None,
) -> dict[str, Any]:
    parent_version_id = None
    meal_thread_id = None
    historical_correction_source_version_id = None
    if latest_log is not None:
        canonical_mapping = get_legacy_mapping_for_meal_log(db, latest_log.id)
        if canonical_mapping is not None:
            meal_thread_id = canonical_mapping.meal_thread_id
            parent_version_id = canonical_mapping.meal_version_id
    commit_candidate = build_commit_request_candidate(
        payload=payload,
        raw_input=raw_input,
        manager_intent=manager_intent,
        request_id=request_id,
        meal_thread_id=meal_thread_id,
        parent_version_id=parent_version_id,
    )
    resolved_target = resolve_commit_candidate_target(
        db,
        candidate=commit_candidate,
        latest_log_id=latest_log.id if latest_log is not None else None,
    )
    commit_candidate.meal_thread_id = resolved_target.meal_thread_id
    commit_candidate.parent_version_id = resolved_target.parent_version_id
    commit_candidate.version_reason = resolved_target.version_reason
    historical_correction_source_version_id = resolved_target.correction_target_version_id
    payload.trace_contract["commit_request_candidate"] = commit_candidate.model_dump(mode="json")
    payload.trace_contract["correction_target_resolution"] = {
        "meal_thread_id": resolved_target.meal_thread_id,
        "parent_version_id": resolved_target.parent_version_id,
        "superseded_version_id": resolved_target.superseded_version_id,
        "version_reason": resolved_target.version_reason,
        "historical_correction_source_version_id": historical_correction_source_version_id,
        "source_log_id": resolved_target.source_log_id,
    }
    persistence_decision = persist_text_meal_result(
        db,
        user=user,
        latest_log=latest_log,
        manager_intent=manager_intent,
        payload=payload,
        raw_input=raw_input,
        request_id=request_id,
        incoming_user_message_id=incoming_user_message_id,
    )
    payload.trace_contract["persistence_decision"] = persistence_decision
    target_attachment = dict((manager_semantic_decision or {}).get("target_attachment") or {})
    target_attachment_mode = str(target_attachment.get("mode") or "")
    if conversation_state.boundary_clarification_open and target_attachment_mode != "boundary_clarification":
        payload.boundary_trace["boundary_resolution_state"] = "resolved"
        payload.boundary_trace["resolution_meal_id"] = persistence_decision.get("linked_meal_log_id")
    elif target_attachment_mode == "boundary_clarification":
        payload.boundary_trace["boundary_resolution_state"] = "open"
    payload.span_timeline.append(
        {
            "span_id": "span:persistence_decision:1",
            "parent_span_id": None,
            "stage": "persistence_decision",
            "status": "ok",
            "attempt_index": 1,
            "trigger_reason": persistence_decision.get("action"),
            "duration_ms": None,
            "input_ref": "trace_contract.persistence_decision",
            "output_ref": "multi_turn_context",
            "stage_input_summary": {"manager_intent": persistence_decision.get("manager_intent")},
            "stage_output_summary": {
                "action": persistence_decision.get("action"),
                "status": persistence_decision.get("status"),
                "parent_log_id": persistence_decision.get("parent_log_id"),
                "canonical_commit": bool(persistence_decision.get("canonical_commit")),
            },
            "handoff_contract": {
                "assistant_message_appended": persistence_decision.get("assistant_message_appended", False)
            },
        }
    )
    return persistence_decision
