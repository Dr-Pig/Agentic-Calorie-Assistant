from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.runtime.contracts.phase_a import CurrentTurnContextV1

MANAGER_CONTEXT_POLICY_VERSION = "accurate_intake_mvp_context_policy_v1"

_DEFERRED_CONTEXT_REASONS = {
    "debug_artifacts": "debug_surface_trace_only",
    "dogfood_review_artifacts": "operator_review_not_manager_input",
    "raw_trace_dump": "trace_dump_not_manager_input",
    "food_gap_candidates": "review_candidate_not_food_truth",
    "long_term_memory": "out_of_scope_for_mvp",
    "proactive_context": "out_of_scope_for_mvp",
    "rescue_context": "out_of_scope_for_mvp",
    "recommendation_context": "out_of_scope_for_mvp",
}


def build_manager_context_packet_v1(
    *,
    current_turn_context: CurrentTurnContextV1,
    user_id: str,
    local_date: str,
    session_id: str,
    channel: str = "web_shell",
    manager_mode: str = "fixture",
    max_recent_messages: int = 8,
    max_recent_chars: int = 2000,
    pending_draft: dict[str, Any] | None = None,
    active_day_state: dict[str, Any] | None = None,
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
    return {
        "metadata": {
            "user_id": user_id,
            "local_date": local_date,
            "session_id": session_id,
            "context_policy_version": MANAGER_CONTEXT_POLICY_VERSION,
            "claim_scope": "current_session_current_day_manager_input_evidence",
        },
        "current_turn": {
            "raw_user_input": current_turn_context.user_utterance,
            "channel": channel,
            "manager_mode": manager_mode,
            "read_only": True,
        },
        "recent_chat_window": {
            "policy": {"last_messages": max_recent_messages, "max_chars": max_recent_chars},
            "messages": _bounded_recent_chat_turns(
                current_turn_context.recent_chat_turns,
                max_recent_messages=max_recent_messages,
                max_recent_chars=max_recent_chars,
            ),
        },
        "hard_pins": {
            "pending_followup": _readonly_copy(current_turn_context.pending_followup),
            "pending_draft": _readonly_copy(pending_draft),
            "last_assistant_question": current_turn_context.last_system_question,
        },
        "active_day_state": _active_day_state(current_turn_context, active_day_state),
        "target_candidates": {
            "for_correction_or_removal": _target_candidates(
                target_candidates or current_turn_context.recent_item_targets,
                max_target_candidates=max_target_candidates,
            ),
            "mutation_authority": False,
        },
        "constraints": [
            "frontend_cannot_infer_semantics",
            "food_gap_candidates_are_not_food_truth",
            "runtime_guards_own_mutation_legality",
            "no_long_term_memory_in_mvp",
            "no_proactive_rescue_or_recommendation_context_in_mvp",
        ],
        "omitted_context": _omitted_context(deferred_inputs),
        "not_claiming": [
            "long_term_memory",
            "proactive_behavior",
            "rescue_or_recommendation",
            "food_kb_truth_promotion",
            "mutation_authority",
        ],
    }


def _bounded_recent_chat_turns(
    turns: list[dict[str, Any]],
    *,
    max_recent_messages: int,
    max_recent_chars: int,
) -> list[dict[str, Any]]:
    selected = [dict(turn) for turn in list(turns or [])[-max_recent_messages:]]
    bounded: list[dict[str, Any]] = []
    total_chars = 0
    for turn in reversed(selected):
        content = str(turn.get("content") or "")
        if bounded and total_chars + len(content) > max_recent_chars:
            continue
        if not bounded and len(content) > max_recent_chars:
            turn["content"] = content[-max_recent_chars:]
            content = str(turn["content"])
        total_chars += len(content)
        bounded.append(_readonly_copy(turn) or {})
    return list(reversed(bounded))


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


def _target_candidates(
    candidates: list[dict[str, Any]],
    *,
    max_target_candidates: int,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for candidate in list(candidates or [])[:max_target_candidates]:
        item = dict(candidate)
        item.setdefault("uniqueness_status", "candidate")
        item.setdefault("removable", True)
        item["read_only"] = True
        item["mutation_authority"] = False
        normalized.append(item)
    return normalized


def _readonly_copy(value: Any) -> Any:
    if value is None:
        return None
    copied = deepcopy(value)
    if isinstance(copied, dict):
        copied.setdefault("read_only", True)
        copied.setdefault("mutation_authority", False)
    return copied


def _omitted_context(values: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"context_id": key, "reason": _DEFERRED_CONTEXT_REASONS[key]}
        for key, value in values.items()
        if value is not None
    ]


__all__ = ["MANAGER_CONTEXT_POLICY_VERSION", "build_manager_context_packet_v1"]
