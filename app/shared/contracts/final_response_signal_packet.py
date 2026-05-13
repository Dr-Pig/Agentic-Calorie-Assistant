from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.manager_tool_result_envelope import (
    normalize_manager_tool_result,
)
from app.shared.contracts.manager_turn_plan import FinalResponsePlan


CAPABILITY_SIGNAL_IDS = {
    "memory": "used_saved_preferences",
    "recommendation": "recommendation_ready",
    "rescue": "rescue_plan_ready",
    "proactive": "follow_up_ready",
    "query": "answer_backed_by_runtime_truth",
    "intake": "intake_truth_ready",
    "reusable_meal": "reusable_meal_reused",
}

DEFAULT_ACTION_AFFORDANCES = {
    "recommendation": ["view_recommendation_offer"],
    "rescue": ["accept_rescue_plan", "dismiss_rescue_plan"],
    "proactive": ["dismiss_nudge", "snooze_nudge", "undo_nudge"],
}

DEFAULT_MUST_NOT_CLAIM = [
    "logged_when_not_committed",
    "scheduled_when_not_sent",
    "mutated_when_guard_not_passed",
]


def build_final_response_signal_packet_contract() -> dict[str, Any]:
    return {
        "artifact_type": "shared_final_response_signal_packet_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "response_mode_default": "chat_first",
        "capability_signal_ids": dict(CAPABILITY_SIGNAL_IDS),
        "default_action_affordances": dict(DEFAULT_ACTION_AFFORDANCES),
        "default_must_not_claim": list(DEFAULT_MUST_NOT_CLAIM),
        "blockers": [],
    }


def build_final_response_signal_packet(
    *,
    final_response: Mapping[str, Any],
    prior_results: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    source_tool_call_ids = [str(item) for item in final_response.get("source_tool_call_ids") or []]
    capability_ids = _capability_ids_from_sources(source_tool_call_ids, prior_results)
    explicit_actions = [str(item) for item in final_response.get("action_affordances") or []]
    plan = FinalResponsePlan(
        response_mode=str(final_response.get("response_mode") or "chat_first"),
        user_visible_capabilities=capability_ids,
        source_tool_call_ids=source_tool_call_ids,
        action_affordances=explicit_actions or _default_actions(capability_ids),
        must_not_claim=list(DEFAULT_MUST_NOT_CLAIM),
    )
    return {
        "artifact_type": "shared_final_response_signal_packet",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "response_plan": plan.model_dump(mode="json"),
        "capability_signals": [
            {
                "capability_id": capability_id,
                "signal_id": CAPABILITY_SIGNAL_IDS[capability_id],
            }
            for capability_id in capability_ids
            if capability_id in CAPABILITY_SIGNAL_IDS
        ],
        "blockers": [],
    }


def _capability_ids_from_sources(
    source_tool_call_ids: list[str],
    prior_results: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    capability_ids: list[str] = []
    seen: set[str] = set()
    for call_id in source_tool_call_ids:
        result = prior_results.get(call_id)
        if not isinstance(result, Mapping):
            continue
        normalized = _mapping(result.get("normalized_result_envelope"))
        if not normalized:
            normalized = normalize_manager_tool_result(result)
        capability_id = str(normalized.get("capability_id") or "")
        if not capability_id or capability_id == "unknown" or capability_id in seen:
            continue
        seen.add(capability_id)
        capability_ids.append(capability_id)
    return capability_ids


def _default_actions(capability_ids: list[str]) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for capability_id in capability_ids:
        for action in DEFAULT_ACTION_AFFORDANCES.get(capability_id, []):
            if action in seen:
                continue
            seen.add(action)
            actions.append(action)
    return actions


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "build_final_response_signal_packet",
    "build_final_response_signal_packet_contract",
]
