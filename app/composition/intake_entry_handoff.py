from __future__ import annotations

from typing import Any

from app.composition.user_provided_kcal_evidence import manager_owned_user_provided_kcal_from_semantics
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE
from app.shared.contracts.correction_operation import structured_correction_operation

_NUTRITION_EVIDENCE_REQUIRED_FINAL_ACTIONS = {
    "commit",
    "correction_applied",
    "overshoot_note",
}
_NUTRITION_WRITE_MUTATION_CANDIDATES = {
    "canonical_write",
    "correction_write",
}
_COMPOSITION_UNKNOWN_ESTIMATION_POSTURES = {
    "composition_unknown",
    "composition_unknown_basket",
}
_B2_RETRIEVAL_GOALS = {
    "generic_anchor_lookup",
    "exact_brand_lookup",
    "listed_item_lookup",
    "composition_clarification",
    "query_only_answer",
}


def entry_handoff_tool_calls(manager_decision: Any, *, resolved_state: Any | None = None) -> list[dict[str, Any]]:
    if str(getattr(manager_decision, "workflow_effect", "") or "") != "route_to_intake":
        return []
    semantic_decision = dict(getattr(manager_decision, "semantic_decision", {}) or {})
    target = dict(getattr(manager_decision, "target_attachment", {}) or {})
    semantic_target = dict(semantic_decision.get("target_attachment") or {})
    merged_target = _hydrate_manager_selected_target({**target, **semantic_target}, resolved_state)
    final_candidate = str(semantic_decision.get("final_action_candidate") or "")
    operation = structured_correction_operation(merged_target)
    if final_candidate == "correction_applied" and operation in {"remove_item", "remove_meal"}:
        return [_target_resolution_handoff_call(merged_target)]
    calls: list[dict[str, Any]] = []
    if _requires_target_resolution_handoff(semantic_decision, merged_target, final_candidate):
        calls.append(_target_resolution_handoff_call(merged_target))
    calls.extend(_nutrition_evidence_handoff_tool_calls(semantic_decision, merged_target, final_candidate))
    return calls


def _remove_item_target_handoff_call(target: dict[str, Any]) -> dict[str, Any]:
    arguments = {
        key: value
        for key, value in {
            "canonical_name": target.get("canonical_name"),
            "meal_thread_id": target.get("meal_thread_id"),
            "meal_item_id": target.get("meal_item_id"),
            "operation": "remove_item",
            "target_resolution_source": target.get("target_resolution_source"),
            "target_proposal_source": "entry_manager_handoff",
        }.items()
        if value not in (None, "")
    }
    return {"name": "resolve_correction_target", "arguments": arguments}


def _target_resolution_handoff_call(target: dict[str, Any]) -> dict[str, Any]:
    operation = structured_correction_operation(target)
    arguments = {
        key: value
        for key, value in {
            "canonical_name": target.get("canonical_name"),
            "meal_thread_id": target.get("meal_thread_id"),
            "meal_item_id": target.get("meal_item_id"),
            "operation": operation,
            "target_resolution_source": target.get("target_resolution_source"),
            "target_proposal_source": "entry_manager_handoff",
        }.items()
        if value not in (None, "")
    }
    return {"name": "resolve_correction_target", "arguments": arguments}


def _requires_target_resolution_handoff(
    semantic_decision: dict[str, Any],
    target: dict[str, Any],
    final_candidate: str,
) -> bool:
    if final_candidate != "correction_applied":
        return False
    if str(semantic_decision.get("mutation_intent_candidate") or "") != "correction_write":
        return False
    return any(target.get(key) not in (None, "") for key in ("canonical_name", "meal_thread_id", "meal_item_id"))


def _nutrition_evidence_handoff_tool_calls(
    semantic_decision: dict[str, Any],
    target: dict[str, Any],
    final_candidate: str,
) -> list[dict[str, Any]]:
    if final_candidate not in _NUTRITION_EVIDENCE_REQUIRED_FINAL_ACTIONS:
        return []
    mutation_candidate = str(semantic_decision.get("mutation_intent_candidate") or "")
    if mutation_candidate not in _NUTRITION_WRITE_MUTATION_CANDIDATES:
        return []
    estimation_posture = str(semantic_decision.get("estimation_posture") or "")
    if estimation_posture in _COMPOSITION_UNKNOWN_ESTIMATION_POSTURES:
        return []
    if manager_owned_user_provided_kcal_from_semantics(semantic_decision) is not None:
        return []
    if structured_correction_operation(target) in {"remove_item", "remove_meal"}:
        return []
    arguments = {
        "manager_semantic_decision": {
            key: value
            for key, value in {
                "base_dish": semantic_decision.get("base_dish") or target.get("canonical_name"),
                "aliases": semantic_decision.get("aliases"),
                "brand_hint": semantic_decision.get("brand_hint"),
                "size_hint": semantic_decision.get("size_hint"),
                "modifier_hints": semantic_decision.get("modifier_hints"),
                "listed_items": semantic_decision.get("listed_items"),
                "retrieval_goal": _handoff_retrieval_goal(semantic_decision),
                "semantic_authority_source": _handoff_semantic_authority_source(semantic_decision),
            }.items()
            if value not in (None, "", [])
        },
        "handoff_source": "entry_manager_semantic_decision",
        "deterministic_role": "execute_manager_owned_evidence_requirement_only",
    }
    return [{"name": "estimate_nutrition", "arguments": arguments}]


def _handoff_retrieval_goal(semantic_decision: dict[str, Any]) -> str:
    explicit = str(semantic_decision.get("retrieval_goal") or "")
    if explicit in _B2_RETRIEVAL_GOALS:
        return explicit
    if isinstance(semantic_decision.get("listed_items"), list) and semantic_decision.get("listed_items"):
        return "listed_item_lookup"
    return "generic_anchor_lookup"


def _handoff_semantic_authority_source(semantic_decision: dict[str, Any]) -> str:
    authority = str(semantic_decision.get("semantic_authority") or "")
    if authority == "deterministic_fake_provider":
        return "synthetic_manager_structured_fixture"
    return "live_manager_structured_output"


def entry_handoff_manager_round(
    *,
    manager_decision: Any,
    tool_calls: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "round_index": 0,
        "stage": MANAGER_LOOP_STAGE,
        "manager_loop_scope": "intake_execution",
        "decision": {
            "manager_action": "call_tools",
            "tool_calls": tool_calls,
            "final_action": dict(getattr(manager_decision, "semantic_decision", {}) or {}).get(
                "final_action_candidate",
                "no_commit",
            ),
            "workflow_effect": "entry_handoff_tool_execution",
            "semantic_decision": dict(getattr(manager_decision, "semantic_decision", {}) or {}),
        },
        "trace": {
            "source": "entry_manager_route_to_intake_handoff",
            "entry_manager_scope": "turn_entry_or_read_only",
            "deterministic_role": "execute_manager_owned_handoff_tool_plan_only",
        },
        "tool_results": tool_results,
    }


async def execute_entry_handoff_seed(
    *,
    manager_decision: Any,
    tool_executor: Any,
    raw_user_input: str,
    resolved_state: Any,
    now_ms: Any,
    record_timing: Any,
) -> dict[str, Any]:
    tool_calls = entry_handoff_tool_calls(manager_decision, resolved_state=resolved_state)
    if not tool_calls:
        return {"tool_results": [], "manager_rounds": []}
    stage_start = now_ms()
    executed = await tool_executor(
        tool_calls=tool_calls,
        raw_user_input=raw_user_input,
        resolved_state=resolved_state,
        tool_results=[],
    )
    tool_results = [dict(item) for item in executed if isinstance(item, dict)]
    record_timing("entry_handoff_tool_plan", now_ms() - stage_start)
    return {
        "tool_results": tool_results,
        "manager_rounds": [
            entry_handoff_manager_round(
                manager_decision=manager_decision,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )
        ],
    }


def _hydrate_manager_selected_target(target: dict[str, Any], resolved_state: Any | None) -> dict[str, Any]:
    if resolved_state is None or not _manager_selected_existing_target(target):
        return target
    active_meal = _as_dict(getattr(resolved_state, "active_meal", None))
    if not active_meal or not _target_matches_active_meal(target, active_meal):
        return target
    hydrated = dict(target)
    if not str(hydrated.get("canonical_name") or "").strip():
        canonical_name = str(active_meal.get("canonical_name") or active_meal.get("meal_title") or "").strip()
        if canonical_name:
            hydrated["canonical_name"] = canonical_name
    for key in ("meal_thread_id", "meal_item_id"):
        if hydrated.get(key) in (None, "") and active_meal.get(key) not in (None, ""):
            hydrated[key] = active_meal.get(key)
    return hydrated


def _manager_selected_existing_target(target: dict[str, Any]) -> bool:
    operation = str(target.get("operation") or target.get("action_type") or "").strip()
    source = str(target.get("target_resolution_source") or "").strip()
    return (
        operation == "attach_to_pending_followup"
        or source == "pending_followup_state"
        or any(target.get(key) not in (None, "") for key in ("meal_thread_id", "meal_item_id", "target_meal_id", "source_meal_id"))
    )


def _target_matches_active_meal(target: dict[str, Any], active_meal: dict[str, Any]) -> bool:
    if not target:
        return False
    operation = str(target.get("operation") or target.get("action_type") or "").strip()
    source = str(target.get("target_resolution_source") or "").strip()
    if operation == "attach_to_pending_followup" or source == "pending_followup_state":
        return any(
            active_meal.get(key) not in (None, "")
            for key in ("meal_thread_id", "meal_item_id", "canonical_name", "meal_title")
        )
    target_ids = {
        value
        for key in ("meal_thread_id", "meal_item_id", "target_meal_id", "source_meal_id")
        if (value := target.get(key)) not in (None, "")
    }
    active_ids = {
        value
        for key in ("meal_thread_id", "meal_item_id")
        if (value := active_meal.get(key)) not in (None, "")
    }
    if target_ids and active_ids:
        return bool(target_ids.intersection(active_ids))
    return False


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
