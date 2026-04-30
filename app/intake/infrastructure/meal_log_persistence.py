from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.intake.application.canonical_commit_bridge import (
    build_commit_request_candidate,
    commit_request_candidate_to_canonical,
    resolve_commit_candidate_target,
)
from app.intake.application.state_transition import determine_meal_status
from app.composition.canonical_persistence import get_legacy_mapping_for_meal_log
from app.database import append_message, save_meal_log, supersede_log, update_message_linkage
from app.models import MealLog, User
from app.schemas import EstimatePayload


def _json_safe(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def persist_text_meal_result(
    db: Session,
    *,
    user: User,
    latest_log: MealLog | None,
    manager_intent: str,
    payload: EstimatePayload,
    raw_input: str,
    request_id: str | None = None,
    incoming_user_message_id: int | None = None,
) -> dict[str, object]:
    components_list = [{"name": c.name, "portion_hint": c.quantity_hint} for c in payload.component_estimates]
    if not components_list and payload.meal_title:
        components_list = [{"name": payload.meal_title, "portion_hint": "1 serving"}]

    parent_id = None
    superseded_log_id = None
    action = "noop"
    persisted_status = None
    persisted_log: MealLog | None = None
    canonical_write_decision = dict(payload.trace_contract.get("canonical_write_decision") or {})
    canonical_write_allowed = canonical_write_decision.get("can_write_canonical", True) is not False
    boundary_followup = bool((payload.boundary_trace or {}).get("boundary_followup_triggered"))
    resolved_meal_status = determine_meal_status(
        payload_action_taken=payload.action_taken,
        payload_route_target=payload.route_target,
        estimated_kcal=payload.estimated_kcal,
        trace_contract=payload.trace_contract,
        quality_signals=payload.quality_signals,
    )

    boundary_continuation = (
        latest_log is not None
        and str((payload.boundary_trace or {}).get("meal_boundary") or "") == "continue_active_meal"
    )
    should_attach_to_latest = latest_log is not None and (
        manager_intent in ["clarification", "modification"] or boundary_continuation
    )

    if should_attach_to_latest:
        supersede_log(db, latest_log.id)
        parent_id = latest_log.id
        superseded_log_id = latest_log.id

    if boundary_followup:
        action = "skip_log_boundary_clarification"
        persisted_status = latest_log.status if latest_log else None
    elif (
        canonical_write_allowed
        and payload.estimated_kcal > 0
        and resolved_meal_status == "completed_meal"
    ):
        persisted_log = save_meal_log(
            db,
            user,
            meal_title=payload.meal_title,
            raw_input=raw_input,
            kcal=payload.estimated_kcal,
            protein_g=payload.protein_g,
            carb_g=payload.carb_g,
            fat_g=payload.fat_g,
            components=components_list,
            debug_steps=payload.debug_steps,
            status="completed_meal",
            pending_question=payload.followup_question,
            parent_log_id=parent_id,
        )
        action = "save_completed_log"
        persisted_status = "completed_meal"
    elif resolved_meal_status in {"candidate_meal", "draft_unresolved"}:
        persisted_log = save_meal_log(
            db,
            user,
            meal_title=payload.meal_title or raw_input,
            raw_input=raw_input,
            kcal=payload.estimated_kcal,
            protein_g=payload.protein_g,
            carb_g=payload.carb_g,
            fat_g=payload.fat_g,
            components=components_list,
            debug_steps=payload.debug_steps,
            status=resolved_meal_status or "draft_unresolved",
            pending_question=payload.followup_question,
            parent_log_id=parent_id,
        )
        action = "save_draft_log"
        persisted_status = resolved_meal_status or "draft_unresolved"

    assistant_message_appended = False
    assistant_message_id: int | None = None
    if payload.reply_text:
        # Collect traces for persistence
        trace_blob = {
            "llm_traces": payload.llm_traces,
            "boundary_trace": payload.boundary_trace,
            "judge_trace": payload.judge_trace,
            "evidence_resolution_trace": payload.evidence_resolution_trace,
            "token_usage": payload.token_usage,
            "trace_contract": payload.trace_contract,
        }
        assistant_msg = append_message(
            db,
            user,
            "assistant",
            payload.reply_text,
            linked_meal_log_id=persisted_log.id if persisted_log else (latest_log.id if boundary_followup and latest_log else None),
            trace_id=request_id,
            trace_json=_json_safe(trace_blob),
        )
        assistant_message_appended = True
        assistant_message_id = assistant_msg.id

    linked_meal_log_id: int | None = None
    if persisted_log is not None:
        linked_meal_log_id = persisted_log.id
    elif boundary_followup:
        linked_meal_log_id = latest_log.id if latest_log else None
    elif payload.boundary_trace.get("meal_boundary") == "continue_active_meal":
        linked_meal_log_id = latest_log.id if latest_log else None
    if incoming_user_message_id is not None:
        update_message_linkage(
            db,
            message_id=incoming_user_message_id,
            linked_meal_log_id=linked_meal_log_id,
            trace_id=request_id,
        )

    canonical_commit = None
    if (
        persisted_log is not None
        and persisted_status == "completed_meal"
        and canonical_write_allowed
    ):
        parent_version_id = None
        meal_thread_id = None
        if latest_log is not None:
            latest_map = get_legacy_mapping_for_meal_log(db, latest_log.id)
            if latest_map is not None:
                meal_thread_id = latest_map.meal_thread_id
                parent_version_id = latest_map.meal_version_id
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
        payload.trace_contract["correction_target_resolution"] = {
            "meal_thread_id": resolved_target.meal_thread_id,
            "parent_version_id": resolved_target.parent_version_id,
            "superseded_version_id": resolved_target.superseded_version_id,
            "version_reason": resolved_target.version_reason,
            "historical_correction_source_version_id": resolved_target.correction_target_version_id,
            "source_log_id": resolved_target.source_log_id,
        }
        canonical_commit = commit_request_candidate_to_canonical(
            db,
            user=user,
            candidate=commit_candidate,
            latest_log_id=latest_log.id if latest_log is not None else None,
            persisted_log_id=persisted_log.id,
        )

    return {
        "action": action,
        "status": persisted_status,
        "parent_log_id": parent_id,
        "superseded_log_id": superseded_log_id,
        "manager_intent": manager_intent,
        "assistant_message_appended": assistant_message_appended,
        "persisted_log_id": persisted_log.id if persisted_log else None,
        "incoming_user_message_id": incoming_user_message_id,
        "assistant_message_id": assistant_message_id,
        "linked_meal_log_id": linked_meal_log_id,
        "canonical_commit": {
            "meal_thread_id": canonical_commit.meal_thread_id,
            "meal_version_id": canonical_commit.meal_version_id,
            "active_version_id": canonical_commit.active_version_id,
            "local_date": canonical_commit.local_date,
            "consumed_kcal": canonical_commit.consumed_kcal,
            "created_new_thread": canonical_commit.created_new_thread,
            "superseded_version_id": canonical_commit.superseded_version_id,
            "ledger_entry_id": canonical_commit.ledger_entry_id,
        }
        if canonical_commit is not None
        else None,
    }
