from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.intake.application.manager_context_scope_flags import current_turn_context_evidence_scope_flags
from app.intake.application.manager_context_policy_constants import (
    DEFERRED_CONTEXT_REASONS,
    DISPLAY_LABEL_FIELDS,
    INTERACTION_EVENT_FIELDS,
    MANAGER_CONTEXT_POLICY_VERSION,
    POLICY_EXCLUDED_CONTEXT_IDS,
)
from app.intake.application.manager_context_packet_read_model_sections import (
    evidence_state as build_evidence_state,
    read_model_summary as build_read_model_summary,
)
from app.intake.application.manager_context_packet_sections import (
    active_workflow_state,
    candidate_context as build_candidate_context,
    queue_state as build_queue_state,
)
from app.intake.application.manager_context_target_candidates import target_candidates as build_target_candidates
from app.intake.application.manager_context_lineage import attach_context_lineage
from app.runtime.contracts.phase_a import CurrentTurnContextV1

def build_manager_context_packet_v1(
    *,
    current_turn_context: CurrentTurnContextV1,
    user_id: str,
    local_date: str,
    local_time: str | None = None,
    timezone: str = "Asia/Taipei",
    session_id: str,
    turn_id: str | None = None,
    trace_id_runtime_only: str | None = None,
    channel: str = "web_shell",
    manager_mode: str = "fixture",
    max_recent_messages: int = 20,
    max_recent_chars: int = 6000,
    queue_state: dict[str, Any] | None = None,
    pending_draft: dict[str, Any] | None = None,
    active_day_state: dict[str, Any] | None = None,
    evidence_state: dict[str, Any] | None = None,
    target_candidates: list[dict[str, Any]] | None = None,
    max_target_candidates: int = 10,
    debug_artifacts: Any | None = None,
    dogfood_review_artifacts: Any | None = None,
    raw_trace_dump: Any | None = None,
    food_gap_candidates: Any | None = None,
    long_term_memory: Any | None = None,
    proactive_context: Any | None = None,
    rescue_context: Any | None = None,
    recommendation_context: Any | None = None,
) -> dict[str, Any]:
    """Build a bounded support-evidence packet for Manager input.

    The packet is intentionally read-only. It exposes current-session/current-day
    context without adding a new truth surface or granting mutation authority.
    """

    deferred_inputs = {
        "debug_artifacts": debug_artifacts,
        "dogfood_review_artifacts": dogfood_review_artifacts,
        "raw_trace_dump": raw_trace_dump,
        "food_gap_candidates": food_gap_candidates,
        "long_term_memory": long_term_memory,
        "proactive_context": proactive_context,
        "rescue_context": rescue_context,
        "recommendation_context": recommendation_context,
    }
    candidate_context = build_candidate_context(current_turn_context, target_candidates)
    recent_chat_messages, loading_artifact = _bounded_recent_chat_turns_with_artifact(
        current_turn_context.recent_chat_turns,
        max_recent_messages=max_recent_messages,
        max_recent_chars=max_recent_chars,
        pending_followup=current_turn_context.pending_followup,
        pending_draft=pending_draft,
        target_candidates=candidate_context,
        interaction_event=current_turn_context.current_interaction_event,
    )
    omitted_context = _omitted_context(deferred_inputs)
    loading_artifact["omitted_context_summary"]["deferred_context_ids"] = [
        item["context_id"] for item in omitted_context
    ]
    packet = {
        "metadata": {
            "user_id": user_id,
            "local_date": local_date,
            "local_time": local_time,
            "timezone": timezone,
            "session_id": session_id,
            "turn_id": turn_id,
            "trace_id_runtime_only": trace_id_runtime_only,
            "context_policy_version": MANAGER_CONTEXT_POLICY_VERSION,
            "claim_scope": "current_session_current_day_manager_input_evidence",
        },
        "current_turn": {
            "user_utterance": current_turn_context.user_utterance,
            "raw_user_input": current_turn_context.user_utterance,
            "channel": channel,
            "manager_mode": manager_mode,
            "current_turn_first": True,
            **current_turn_context_evidence_scope_flags(),
            "interaction_event": _interaction_event_snapshot(current_turn_context.current_interaction_event),
        },
        "queue_state": build_queue_state(queue_state),
        "recent_chat_window": {
            "policy": {
                "mode": "token_budgeted",
                "max_messages_safety_cap": max_recent_messages,
                "last_messages": max_recent_messages,
                "max_chars": max_recent_chars,
                "hard_pins_preserved": True,
                "summary_role": "reference_only",
            },
            "messages": recent_chat_messages,
            "omitted_summary": loading_artifact["omitted_context_summary"],
        },
        "context_loading_artifact": loading_artifact,
        "hard_pins": {
            "pending_followup": _readonly_copy(current_turn_context.pending_followup),
            "pending_draft": _readonly_copy(pending_draft),
            "last_assistant_question": current_turn_context.last_system_question,
        },
        "active_workflow": active_workflow_state(
            current_turn_context=current_turn_context,
            pending_draft=pending_draft,
        ),
        "active_day_state": _active_day_state(current_turn_context, active_day_state),
        "read_model_summary": build_read_model_summary(current_turn_context),
        "evidence_state": build_evidence_state(evidence_state),
        "target_candidates": {
            "selection_owner": "manager",
            "for_correction_or_removal": build_target_candidates(
                candidate_context,
                max_target_candidates=max_target_candidates,
            ),
            "mutation_authority": False,
            "read_only": True,
        },
        "constraints": [
            "frontend_cannot_infer_semantics",
            "food_gap_candidates_are_not_food_truth",
            "runtime_guards_own_mutation_legality",
            "no_long_term_memory_in_mvp",
            "no_proactive_rescue_or_recommendation_context_in_mvp",
        ],
        "omitted_context": omitted_context,
        "not_claiming": [
            "long_term_memory",
            "proactive_behavior",
            "rescue_or_recommendation",
            "food_kb_truth_promotion",
            "mutation_authority",
        ],
    }
    return attach_context_lineage(packet)


def _bounded_recent_chat_turns_with_artifact(
    turns: list[dict[str, Any]],
    *,
    max_recent_messages: int,
    max_recent_chars: int,
    pending_followup: dict[str, Any] | None = None,
    pending_draft: dict[str, Any] | None = None,
    target_candidates: list[dict[str, Any]] | None = None,
    interaction_event: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    max_recent_messages = max(0, int(max_recent_messages or 0))
    max_recent_chars = max(0, int(max_recent_chars or 0))
    all_turns = [dict(turn) for turn in list(turns or []) if isinstance(turn, dict)]
    selected = all_turns[-max_recent_messages:] if max_recent_messages else []
    omitted_by_message_limit = max(len(all_turns) - len(selected), 0)
    bounded: list[dict[str, Any]] = []
    total_chars = 0
    omitted_by_char_cap = 0
    char_truncated = False
    for turn in reversed(selected):
        content = str(turn.get("content") or "")
        if max_recent_chars == 0:
            omitted_by_char_cap += 1
            char_truncated = True
            continue
        if bounded and total_chars + len(content) > max_recent_chars:
            omitted_by_char_cap += 1
            char_truncated = True
            continue
        if not bounded and len(content) > max_recent_chars:
            turn["content"] = content[-max_recent_chars:]
            content = str(turn["content"])
            char_truncated = True
        total_chars += len(content)
        bounded.append(_readonly_copy(turn) or {})
    messages = list(reversed(bounded))
    omitted_count = omitted_by_message_limit + omitted_by_char_cap
    history_trimmed = omitted_count > 0 or char_truncated
    canonical_state_reinjected = history_trimmed and any(
        (
            pending_followup is not None,
            pending_draft is not None,
            bool(list(target_candidates or [])),
            interaction_event is not None,
        )
    )
    artifact = {
        "loaded_message_count": len(messages),
        "omitted_count": omitted_count,
        "history_trimmed": history_trimmed,
        "canonical_state_reinjected_after_history_trim": canonical_state_reinjected,
        "loaded_char_count": total_chars,
        "hard_char_cap": max_recent_chars,
        "char_truncated": char_truncated,
        "token_budget_status": "at_hard_cap" if char_truncated or total_chars >= max_recent_chars > 0 else "within_budget",
        "loaded_context_summary": {
            "recent_chat_messages": len(messages),
            "pending_followup_present": pending_followup is not None,
            "pending_draft_present": pending_draft is not None,
            "target_candidate_count": len(list(target_candidates or [])),
            "interaction_event_present": interaction_event is not None,
        },
        "omitted_context_summary": {
            "recent_chat_messages_omitted": omitted_count,
            "omitted_by_message_limit": omitted_by_message_limit,
            "omitted_by_char_cap": omitted_by_char_cap,
            "policy_excluded_context_ids": list(POLICY_EXCLUDED_CONTEXT_IDS),
        },
    }
    return messages, artifact


def _interaction_event_snapshot(event: Any | None) -> dict[str, Any] | None:
    if event is None:
        return None
    payload = event.model_dump(mode="json") if hasattr(event, "model_dump") else dict(event)
    snapshot = {
        key: payload.get(key)
        for key in INTERACTION_EVENT_FIELDS
        if payload.get(key) is not None
    }
    event_payload = _display_label_snapshot(payload.get("payload"))
    if event_payload:
        snapshot["payload"] = event_payload
    metadata = _display_label_snapshot(payload.get("metadata"))
    if metadata:
        snapshot["metadata"] = metadata
    snapshot.update({
        "read_only": True,
        "mutation_authority": False,
    })
    return snapshot


def _display_label_snapshot(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        key: value[key]
        for key in DISPLAY_LABEL_FIELDS
        if key in value and _safe_scalar(value[key])
    }


def _safe_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float)) and not isinstance(value, bool)


def _active_day_state(
    current_turn_context: CurrentTurnContextV1,
    active_day_state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = dict(active_day_state or {})
    state.setdefault("budget_summary", _readonly_copy(current_turn_context.current_budget_snapshot))
    state.setdefault("active_meal_thread_ref", _readonly_copy(current_turn_context.active_meal_thread_ref))
    state.setdefault("recent_correction_removal_summary", [])
    state["read_only"] = True
    state["mutation_authority"] = False
    return state


def _readonly_copy(value: Any) -> Any:
    if value is None:
        return None
    copied = deepcopy(value)
    if isinstance(copied, dict):
        copied["read_only"] = True
        copied["mutation_authority"] = False
    return copied


def _omitted_context(values: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"context_id": key, "reason": DEFERRED_CONTEXT_REASONS[key]}
        for key, value in values.items()
        if value is not None
    ]
