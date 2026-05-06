from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_manager_tool_surface_inventory import REQUIRED_MANAGER_TOOLS

REQUIRED_CASE_IDS = (
    "budget_remaining_today_query",
    "budget_today_meal_log_query",
    "body_active_plan_query",
    "body_latest_weight_query",
    "body_record_weight_mutation_candidate",
    "calibration_preview_request",
    "calibration_apply_without_stored_proposal",
    "calibration_apply_with_stored_proposal",
    "app_usage_help_question",
    "food_logging_deferred_to_intake_fooddb_track",
    "ambiguous_general_health_chat_no_tool",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _case(
    case_id: str,
    utterance: str,
    selected_tool: str,
    tool_kind: str,
    *,
    guard: bool = False,
    stored: bool = False,
    blocked_reason: str | None = None,
    ambiguity: bool = False,
    fooddb_used: bool = False,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "raw_user_input": utterance,
        "expected_tool_choice": selected_tool,
        "tool_kind": tool_kind,
        "guard_required": guard,
        "stored_proposal_required": stored,
        "blocked_reason": blocked_reason,
        "ambiguity_preserved": ambiguity,
        "mutation_allowed": tool_kind == "mutation_bearing" and guard and blocked_reason is None,
        "raw_text_authorizes_mutation": False,
        "fooddb_used": fooddb_used,
        "web_tavily_used": False,
        "runtime_truth_changed": False,
        "fixture_manager_decision": {
            "semantic_source": "fixture_manager_structured_decision",
            "selected_tool": selected_tool,
            "tool_kind": tool_kind,
            "deterministic_role": "provide_allowed_tools_context_and_validate_boundaries",
        },
    }


def _cases() -> list[dict[str, Any]]:
    return [
        _case("budget_remaining_today_query", "我今天還可以吃多少？", "budget.get_remaining_calories", "read_only"),
        _case("budget_today_meal_log_query", "今天吃了什麼？", "budget.get_day_meal_log", "read_only"),
        _case("body_active_plan_query", "我現在的目標是什麼？", "body.get_active_plan", "read_only"),
        _case("body_latest_weight_query", "我現在體重紀錄是多少？", "body.get_latest_observation", "read_only"),
        _case("body_record_weight_mutation_candidate", "今天體重 72.4", "body.record_observation", "mutation_bearing", guard=True),
        _case("calibration_preview_request", "最近都沒瘦，要不要調整熱量？", "calibration.preview_proposal", "proposal_persisting", guard=True),
        _case(
            "calibration_apply_without_stored_proposal",
            "好，幫我套用",
            "calibration.get_pending_proposal",
            "read_only",
            blocked_reason="missing_stored_proposal",
        ),
        _case(
            "calibration_apply_with_stored_proposal",
            "套用剛剛那個建議",
            "calibration.apply_stored_proposal_action",
            "mutation_bearing",
            guard=True,
            stored=True,
        ),
        _case("app_usage_help_question", "滷味應該怎麼記？", "app.answer_usage_question", "read_only"),
        _case("food_logging_deferred_to_intake_fooddb_track", "我喝一杯珍奶", "intake_fooddb_track_deferred", "deferred"),
        _case("ambiguous_general_health_chat_no_tool", "我最近好累怎麼辦", "none", "no_tool", ambiguity=True),
    ]


def _validate(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    case_ids = {str(case.get("case_id")) for case in cases}
    for case_id in REQUIRED_CASE_IDS:
        if case_id not in case_ids:
            blockers.append(f"missing_case:{case_id}")
    for case in cases:
        case_id = str(case.get("case_id"))
        decision = case.get("fixture_manager_decision") if isinstance(case.get("fixture_manager_decision"), dict) else {}
        if decision.get("semantic_source") != "fixture_manager_structured_decision":
            blockers.append(f"{case_id}.semantic_source_not_fixture_manager")
        if decision.get("selected_tool") != case.get("expected_tool_choice"):
            blockers.append(f"{case_id}.fixture_selected_tool_mismatch")
        if case.get("raw_text_authorizes_mutation") is not False:
            blockers.append(f"{case_id}.raw_text_authorizes_mutation")
        if case.get("tool_kind") == "mutation_bearing" and case.get("guard_required") is not True:
            blockers.append(f"{case_id}.mutation_guard_missing")
        if case.get("expected_tool_choice") == "calibration.apply_stored_proposal_action" and case.get("stored_proposal_required") is not True:
            blockers.append(f"{case_id}.stored_proposal_required_missing")
        if case.get("expected_tool_choice") == "intake_fooddb_track_deferred" and case.get("fooddb_used") is not False:
            blockers.append(f"{case_id}.fooddb_used_in_plce_wall")
    return blockers


def build_manager_tool_choice_regression_wall_artifact(
    *, cases: list[dict[str, Any]] | None = None, overrides: dict[str, Any] | None = None
) -> dict[str, Any]:
    scenario_cases = deepcopy(cases if cases is not None else _cases())
    blockers = _validate(scenario_cases)
    artifact: dict[str, Any] = {
        "artifact_type": "accurate_intake_manager_tool_choice_regression_wall",
        "status": "manager_tool_choice_regression_wall_pass",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "claim_scope": "non_fooddb_manager_tool_choice_fixture_regression",
        "required_case_ids": list(REQUIRED_CASE_IDS),
        "required_manager_tools": list(REQUIRED_MANAGER_TOOLS),
        "cases": scenario_cases,
        "summary": {
            "case_count": len(scenario_cases),
            "read_only_cases": sum(1 for case in scenario_cases if case.get("tool_kind") == "read_only"),
            "mutation_bearing_cases": sum(1 for case in scenario_cases if case.get("tool_kind") == "mutation_bearing"),
        },
        "fixture_manager_used": True,
        "semantic_owner": "fixture_manager_structured_decision",
        "deterministic_selected_tool": False,
        "deterministic_selected_intent": False,
        "frontend_raw_text_semantic_router": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_packet_schema_changed": False,
        "fooddb_used": False,
        "web_tavily_used": False,
        "live_llm_invoked": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "blockers": blockers,
    }
    artifact.update(overrides or {})
    for flag in ("live_llm_invoked", "fooddb_used", "web_tavily_used", "mutation_changed", "product_readiness_claimed"):
        if artifact.get(flag) is True and flag not in artifact["blockers"]:
            artifact["blockers"].append(flag)
    if artifact["blockers"]:
        artifact["status"] = "blocked"
    return _json_safe(artifact)


__all__ = ["build_manager_tool_choice_regression_wall_artifact"]
