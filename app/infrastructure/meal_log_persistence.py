from __future__ import annotations

from sqlalchemy.orm import Session

from ..application.state_transition import determine_meal_status
from ..database import append_message, save_meal_log, supersede_log, update_message_linkage
from ..models import MealLog, User
from ..schemas import EstimatePayload


def persist_text_meal_result(
    db: Session,
    *,
    user: User,
    latest_log: MealLog | None,
    planner_intent: str,
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
    boundary_followup = bool((payload.boundary_trace or {}).get("boundary_followup_triggered"))
    resolved_meal_status = determine_meal_status(
        payload_action_taken=payload.action_taken,
        payload_route_target=payload.route_target,
        estimated_kcal=payload.estimated_kcal,
        trace_contract=payload.trace_contract,
        quality_signals=payload.quality_signals,
    )

    if latest_log and planner_intent in ["clarification", "modification"]:
        supersede_log(db, latest_log.id)
        parent_id = latest_log.id
        superseded_log_id = latest_log.id

    if boundary_followup:
        action = "skip_log_boundary_clarification"
        persisted_status = latest_log.status if latest_log else None
    elif payload.estimated_kcal > 0 and payload.route_target != "clarify_user_private" and resolved_meal_status == "completed_meal":
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
    elif payload.route_target == "clarify_user_private" or resolved_meal_status in {"candidate_meal", "draft_unresolved"}:
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
        assistant_msg = append_message(
            db,
            user,
            "assistant",
            payload.reply_text,
            linked_meal_log_id=persisted_log.id if persisted_log else (latest_log.id if boundary_followup and latest_log else None),
            trace_id=request_id,
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

    return {
        "action": action,
        "status": persisted_status,
        "parent_log_id": parent_id,
        "superseded_log_id": superseded_log_id,
        "planner_intent": planner_intent,
        "assistant_message_appended": assistant_message_appended,
        "persisted_log_id": persisted_log.id if persisted_log else None,
        "incoming_user_message_id": incoming_user_message_id,
        "assistant_message_id": assistant_message_id,
        "linked_meal_log_id": linked_meal_log_id,
    }
