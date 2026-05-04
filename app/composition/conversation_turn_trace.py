from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.composition.dogfood_trace_policy import (
    build_manager_mode_policy,
    build_unsupported_intent_policy,
)
from app.database import append_message, get_or_create_user
from app.shared.infra.models import MessageBuffer

_EVIDENCE_REQUIRED_FINAL_ACTIONS = {
    "commit",
    "commit_logged_estimate",
    "commit_correction",
    "correction_applied",
    "overshoot_note",
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _model_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return _json_safe(value)


def _object_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {}


def _manager_context_policy_version(packet: dict[str, Any] | None) -> str | None:
    if not isinstance(packet, dict):
        return None
    metadata = dict(packet.get("metadata") or {})
    version = metadata.get("context_policy_version")
    return str(version) if version is not None else None


def _manager_context_loaded_summary(packet: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(packet, dict):
        return {}
    artifact = dict(packet.get("context_loading_artifact") or {})
    return _json_safe(dict(artifact.get("loaded_context_summary") or {}))


def _manager_context_omitted_summary(packet: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(packet, dict):
        return {}
    artifact = dict(packet.get("context_loading_artifact") or {})
    omitted = dict(artifact.get("omitted_context_summary") or {})
    if "deferred_context_ids" not in omitted:
        deferred_context_ids = [
            item.get("context_id")
            for item in list(packet.get("omitted_context") or [])
            if isinstance(item, dict) and item.get("context_id") is not None
        ]
        if deferred_context_ids:
            omitted["deferred_context_ids"] = deferred_context_ids
    return _json_safe(omitted)


def _pending_followup_snapshot(state: Any) -> dict[str, Any] | None:
    conversation_state = getattr(state, "conversation_state", None)
    pending_state = getattr(conversation_state, "pending_followup_state", None)
    if pending_state is not None:
        return _model_dump(pending_state)
    injected_context = _object_dict(getattr(state, "injected_context", None))
    pending_payload = _object_dict(injected_context.get("PENDING_FOLLOWUP"))
    if pending_payload and bool(pending_payload.get("is_open")):
        return _json_safe(pending_payload)
    return None


def _state_snapshot(state: Any) -> dict[str, Any]:
    current_budget = getattr(state, "current_budget_view", None)
    active_plan = getattr(state, "active_body_plan_view", None)
    return {
        "user_external_id": getattr(state, "user_external_id", None),
        "user_id": getattr(state, "user_id", None),
        "local_date": getattr(state, "local_date", None),
        "onboarding_ready": bool(getattr(state, "onboarding_ready", False)),
        "active_meal": _json_safe(getattr(state, "active_meal", None)),
        "pending_followup": _pending_followup_snapshot(state),
        "current_budget": _model_dump(current_budget) if current_budget is not None else None,
        "active_body_plan": _model_dump(active_plan) if active_plan is not None else None,
    }


def _structured_followup_question(result: dict[str, Any] | None) -> str | None:
    payload = dict(result or {})
    manager = dict(payload.get("intake_execution_manager") or {})
    manager_rounds = list(manager.get("manager_rounds") or [])
    final_round = dict(manager_rounds[-1].get("decision") or {}) if manager_rounds else {}
    answer_contract = dict(final_round.get("answer_contract") or {})
    semantic_decision = dict(final_round.get("semantic_decision") or {})
    question = str(
        answer_contract.get("followup_question")
        or semantic_decision.get("followup_question")
        or ""
    ).strip()
    return question or None


def _linked_meal_log_id(result: dict[str, Any] | None) -> int | None:
    payload = dict(result or {})
    persistence = _object_dict((payload.get("intake_execution_manager") or {}).get("persistence_result"))
    for key in ("linked_meal_log_id", "persisted_log_id"):
        value = persistence.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _evidence_summary_content_present(value: Any) -> bool:
    evidence = _object_dict(value)
    if not evidence:
        return False
    if evidence.get("target_evidence_present") is True:
        return True
    if str(evidence.get("eligibility") or "") == "target_evidence":
        return True
    count_keys = ("candidate_count", "exact_count", "near_exact_count", "generic_count")
    for key in count_keys:
        try:
            if int(evidence.get(key) or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _persistence_evidence_present(value: Any) -> bool:
    persistence = _object_dict(value)
    if not persistence:
        return False
    if persistence.get("canonical_commit") is not None:
        return True
    if persistence.get("target_evidence_contract") or persistence.get("target_evidence_payload"):
        return True
    return _evidence_summary_content_present(persistence.get("evidence_summary"))


def _dogfood_trace_policy(manager_decision: Any) -> dict[str, Any]:
    decision = _object_dict(manager_decision)
    unsupported_family = str(decision.get("unsupported_intent_family") or "").strip()
    manager_mode = str(decision.get("manager_mode") or "fixture").strip() or "fixture"
    provider_profile = decision.get("provider_profile")
    model_id = decision.get("model_id")
    return {
        "lifecycle_status": "raw_trace",
        "raw_trace_is_truth": False,
        "review_candidate_can_be_auto_proposed": True,
        "canonical_eval_requires_human_approval": True,
        "unsupported_intent_policy": (
            build_unsupported_intent_policy(unsupported_family) if unsupported_family else None
        ),
        "manager_mode_policy": build_manager_mode_policy(
            manager_mode=manager_mode,
            provider_profile=str(provider_profile) if provider_profile is not None else None,
            live_call_used=bool(decision.get("live_call_used") is True),
            model_id=str(model_id) if model_id is not None else None,
        ),
    }


def build_runtime_turn_trace(
    *,
    request_id: str,
    local_date: str,
    raw_user_input: str | None,
    assistant_message: str | None,
    state_before: Any,
    current_turn_context: Any | None,
    manager_context_packet_v1: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    state_after: Any | None = None,
    phase_a_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(result or {})
    manager_decision = payload.get("manager_decision")
    intake_execution_manager = dict(payload.get("intake_execution_manager") or {})
    phase_c_trace = dict(payload.get("phase_c_trace") or {})
    state_delta = dict(payload.get("state_delta") or {})
    sidecar = dict(payload.get("sidecar") or {})
    final_mapping = dict(intake_execution_manager.get("final") or {})
    final_action = str(final_mapping.get("final_action") or "")
    tool_outputs = {
        "manager_rounds": intake_execution_manager.get("manager_rounds") or [],
        "persistence_result": intake_execution_manager.get("persistence_result"),
        "evidence_summary": sidecar.get("evidence_summary"),
    }
    evidence_content_present = _evidence_summary_content_present(
        tool_outputs.get("evidence_summary")
    ) or _persistence_evidence_present(tool_outputs.get("persistence_result"))
    evidence_required = final_action in _EVIDENCE_REQUIRED_FINAL_ACTIONS
    evidence_requirement_satisfied = (not evidence_required) or evidence_content_present
    context_policy_version = _manager_context_policy_version(manager_context_packet_v1)
    loaded_context_summary = _manager_context_loaded_summary(manager_context_packet_v1)
    omitted_context_summary = _manager_context_omitted_summary(manager_context_packet_v1)
    return {
        "trace_schema_version": "accurate_intake_conversation_turn_v1",
        "request_id": request_id,
        "local_date": local_date,
        "scope": "current_session_current_day",
        "long_term_memory": False,
        "proactive": False,
        "rescue_recommendation": False,
        "context_policy_version": context_policy_version,
        "loaded_context_summary": loaded_context_summary,
        "omitted_context_summary": omitted_context_summary,
        "manager_context_packet_v1": _json_safe(manager_context_packet_v1),
        "context_snapshot": {
            "current_turn_context": _model_dump(current_turn_context) if current_turn_context is not None else None,
            "manager_context_packet_v1": _json_safe(manager_context_packet_v1),
            "state_before": _state_snapshot(state_before),
            "state_after": _state_snapshot(state_after) if state_after is not None else None,
            "phase_a_trace": _json_safe(phase_a_trace or payload.get("phase_a_trace") or {}),
        },
        "user_message": {
            "raw_text": raw_user_input,
            "source": "chat",
        },
        "assistant_response": {
            "text": assistant_message,
            "structured_followup_question": _structured_followup_question(payload),
        },
        "trace_chain": {
            "chat_message": "message_buffer",
            "manager_decision_present": manager_decision is not None,
            "evidence_packet_present": True,
            "evidence_content_present": evidence_content_present,
            "evidence_required": evidence_required,
            "evidence_requirement_satisfied": evidence_requirement_satisfied,
            "final_mapping_present": bool(final_mapping),
            "state_before_present": state_before is not None,
            "state_after_present": state_after is not None,
        },
        "manager_decision": _json_safe(manager_decision),
        "dogfood_trace_policy": _json_safe(_dogfood_trace_policy(manager_decision)),
        "evidence_packet": _json_safe(tool_outputs),
        "final_mapping": _json_safe(final_mapping),
        "state_delta": _json_safe(state_delta),
        "phase_c_trace": _json_safe(phase_c_trace),
    }


def _messages_for_trace(db: Session, *, user_id: int, request_id: str) -> list[MessageBuffer]:
    return (
        db.query(MessageBuffer)
        .filter(MessageBuffer.user_id == user_id, MessageBuffer.trace_id == request_id)
        .order_by(MessageBuffer.id.asc())
        .all()
    )


def _upsert_trace_on_message(
    db: Session,
    *,
    message: MessageBuffer,
    content: str,
    trace: dict[str, Any],
    linked_meal_log_id: int | None,
) -> None:
    message.content = content
    message.trace_json = {
        **dict(message.trace_json or {}),
        "runtime_turn_trace": _json_safe(trace),
    }
    if linked_meal_log_id is not None:
        message.linked_meal_log_id = linked_meal_log_id
    db.add(message)


def _pending_followup_linkage(
    trace: dict[str, Any],
    *,
    user_message_id: int | None,
    assistant_message_id: int | None,
    linked_meal_log_id: int | None,
) -> dict[str, Any] | None:
    context_snapshot = dict(trace.get("context_snapshot") or {})
    state_after = dict(context_snapshot.get("state_after") or {})
    pending_followup = dict(state_after.get("pending_followup") or {})
    if not pending_followup or not bool(pending_followup.get("is_open")):
        return None
    return {
        "runtime_turn_id": trace.get("request_id"),
        "user_message_id": user_message_id,
        "assistant_message_id": assistant_message_id,
        "linked_meal_log_id": linked_meal_log_id,
        "pending_followup": _json_safe(pending_followup),
    }


def record_runtime_turn_messages(
    db: Session,
    *,
    user_external_id: str,
    request_id: str,
    local_date: str,
    raw_user_input: str | None,
    assistant_message: str | None,
    state_before: Any,
    current_turn_context: Any | None,
    manager_context_packet_v1: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    state_after: Any | None = None,
    phase_a_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user = get_or_create_user(db, user_external_id)
    trace = build_runtime_turn_trace(
        request_id=request_id,
        local_date=local_date,
        raw_user_input=raw_user_input,
        assistant_message=assistant_message,
        state_before=state_before,
        current_turn_context=current_turn_context,
        manager_context_packet_v1=manager_context_packet_v1,
        result=result,
        state_after=state_after,
        phase_a_trace=phase_a_trace,
    )
    linked_meal_log_id = _linked_meal_log_id(result)
    existing = _messages_for_trace(db, user_id=user.id, request_id=request_id)
    user_message = next((message for message in existing if message.role == "user"), None)
    assistant_message_row = next((message for message in existing if message.role == "assistant"), None)
    if user_message is None and raw_user_input:
        user_message = append_message(
            db,
            user,
            "user",
            raw_user_input,
            linked_meal_log_id=linked_meal_log_id,
            trace_id=request_id,
            trace_json={"runtime_turn_trace": _json_safe(trace)},
        )
    elif user_message is not None:
        _upsert_trace_on_message(
            db,
            message=user_message,
            content=raw_user_input or user_message.content,
            trace=trace,
            linked_meal_log_id=linked_meal_log_id,
        )
    if assistant_message_row is None and assistant_message:
        assistant_message_row = append_message(
            db,
            user,
            "assistant",
            assistant_message,
            linked_meal_log_id=linked_meal_log_id,
            trace_id=request_id,
            trace_json={"runtime_turn_trace": _json_safe(trace)},
        )
    elif assistant_message_row is not None:
        _upsert_trace_on_message(
            db,
            message=assistant_message_row,
            content=assistant_message or assistant_message_row.content,
            trace=trace,
            linked_meal_log_id=linked_meal_log_id,
        )
    trace["chat_linkage"] = {
        "runtime_turn_id": request_id,
        "user_message_id": user_message.id if user_message is not None else None,
        "assistant_message_id": assistant_message_row.id if assistant_message_row is not None else None,
        "linked_meal_log_id": linked_meal_log_id,
    }
    trace["pending_followup_linkage"] = _pending_followup_linkage(
        trace,
        user_message_id=user_message.id if user_message is not None else None,
        assistant_message_id=assistant_message_row.id if assistant_message_row is not None else None,
        linked_meal_log_id=linked_meal_log_id,
    )
    if user_message is not None:
        _upsert_trace_on_message(
            db,
            message=user_message,
            content=raw_user_input or user_message.content,
            trace=trace,
            linked_meal_log_id=linked_meal_log_id,
        )
    if assistant_message_row is not None:
        _upsert_trace_on_message(
            db,
            message=assistant_message_row,
            content=assistant_message or assistant_message_row.content,
            trace=trace,
            linked_meal_log_id=linked_meal_log_id,
        )
    db.commit()
    return {
        "request_id": request_id,
        "user_message_id": user_message.id if user_message is not None else None,
        "assistant_message_id": assistant_message_row.id if assistant_message_row is not None else None,
        "linked_meal_log_id": linked_meal_log_id,
        "runtime_turn_trace_present": True,
    }


__all__ = [
    "build_runtime_turn_trace",
    "record_runtime_turn_messages",
]
