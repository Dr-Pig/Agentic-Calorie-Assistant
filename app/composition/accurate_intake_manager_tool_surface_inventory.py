from __future__ import annotations

from copy import deepcopy
from typing import Any

REQUIRED_MANAGER_TOOLS = (
    "budget.get_today_summary",
    "budget.get_remaining_calories",
    "budget.get_day_meal_log",
    "body.get_active_plan",
    "body.get_latest_observation",
    "body.record_observation",
    "calibration.preview_proposal",
    "calibration.get_pending_proposal",
    "calibration.apply_stored_proposal_action",
    "app.answer_usage_question",
)

REQUIRED_DIRECT_LANE_IDS = (
    "estimate_general_chat_budget_summary",
    "estimate_general_chat_goal_summary",
    "estimate_general_chat_fallback_answer",
    "estimate_explicit_calibration_preview",
    "estimate_explicit_calibration_action",
    "estimate_body_observation_record_weight",
)


def _tool(name: str, kind: str, owner: str, source: str, *, guard: bool = False, mutation_authority: bool | str = False, stored: bool = False) -> dict[str, Any]:
    return {
        "tool_name": name,
        "tool_kind": kind,
        "truth_owner": owner,
        "mutation_authority": mutation_authority,
        "guard_required": guard,
        "stored_proposal_required": stored,
        "allowed_facts_source": source,
    }


def _lane(lane_id: str, signal: str, tools: list[str], kind: str, owner: str, stage: str, **extra: Any) -> dict[str, Any]:
    return {
        "direct_lane_id": lane_id,
        "current_entrypoint": "app.composition.intake_routes.estimate",
        "current_signal": signal,
        "future_manager_tools": tools,
        "tool_kind": kind,
        "truth_owner": owner,
        "safe_conversion_stage": stage,
        **extra,
    }


_TARGET_TOOLS: tuple[dict[str, Any], ...] = (
    _tool("budget.get_today_summary", "read_only", "budget_domain", "CurrentBudgetView"),
    _tool("budget.get_remaining_calories", "read_only", "budget_domain", "RemainingBudgetAnswerContract"),
    _tool("budget.get_day_meal_log", "read_only", "intake_and_budget_projection", "CurrentBudgetView.meals"),
    _tool("body.get_active_plan", "read_only", "body_domain", "ActiveBodyPlanView"),
    _tool("body.get_latest_observation", "read_only", "body_domain", "BodyObservationHistory"),
    _tool(
        "body.record_observation",
        "mutation_bearing",
        "body_domain",
        "BodyObservationResult",
        guard=True,
        mutation_authority="guarded_domain_service",
    ),
    _tool("calibration.preview_proposal", "proposal_persisting", "calibration_domain", "CalibrationPreview", guard=True),
    _tool("calibration.get_pending_proposal", "read_only", "calibration_domain", "CalibrationProposalInbox"),
    _tool(
        "calibration.apply_stored_proposal_action",
        "mutation_bearing",
        "calibration_domain",
        "CalibrationProposalActionResult",
        guard=True,
        mutation_authority="stored_proposal_guard",
        stored=True,
    ),
    _tool("app.answer_usage_question", "read_only", "app_product_policy", "AppUsagePolicy"),
)

_DIRECT_LANES: tuple[dict[str, Any], ...] = (
    _lane(
        "estimate_general_chat_budget_summary",
        "general_chat answer_only + CurrentBudgetView",
        ["budget.get_today_summary", "budget.get_remaining_calories"],
        "read_only",
        "budget_domain",
        "read_only_tool_loop_fake_smoke",
    ),
    _lane(
        "estimate_general_chat_goal_summary",
        "general_chat answer_only + ActiveBodyPlanView",
        ["body.get_active_plan"],
        "read_only",
        "body_domain",
        "read_only_tool_loop_fake_smoke",
    ),
    _lane(
        "estimate_general_chat_fallback_answer",
        "general_chat fallback_answer",
        ["app.answer_usage_question"],
        "read_only",
        "app_product_policy",
        "read_only_tool_loop_fake_smoke",
    ),
    _lane(
        "estimate_explicit_calibration_preview",
        "calibration_preview_requested",
        ["calibration.preview_proposal"],
        "proposal_persisting",
        "calibration_domain",
        "proposal_tool_guard_smoke",
    ),
    _lane(
        "estimate_explicit_calibration_action",
        "calibration_action or proposal container id",
        ["calibration.apply_stored_proposal_action"],
        "mutation_bearing",
        "calibration_domain",
        "mutation_tool_guard_smoke",
        guard_required=True,
        stored_proposal_required=True,
    ),
    _lane(
        "estimate_body_observation_record_weight",
        "body_observation + parsed weight",
        ["body.record_observation"],
        "mutation_bearing",
        "body_domain",
        "mutation_tool_guard_smoke",
        guard_required=True,
    ),
)


def _with_boundary_defaults(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        row.setdefault("guard_required", False)
        row.setdefault("stored_proposal_required", False)
        row.setdefault("raw_text_authorizes_mutation", False)
        row.setdefault("semantic_owner", "manager")
        row.setdefault("deterministic_role", "provide_context_validate_guard_execute_tool")
        row.setdefault("frontend_semantic_owner", False)
    return rows


def build_manager_tool_surface_inventory_artifact(
    *, direct_lanes: list[dict[str, Any]] | None = None, target_tools: list[dict[str, Any]] | None = None, overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lanes = _with_boundary_defaults(deepcopy(direct_lanes if direct_lanes is not None else list(_DIRECT_LANES)))
    tools = deepcopy(target_tools if target_tools is not None else list(_TARGET_TOOLS))
    blockers: list[str] = []

    lane_ids = {str(lane.get("direct_lane_id")) for lane in lanes}
    tool_names = {str(tool.get("tool_name")) for tool in tools}
    for lane_id in REQUIRED_DIRECT_LANE_IDS:
        if lane_id not in lane_ids:
            blockers.append(f"missing_direct_lane:{lane_id}")
    for tool_name in REQUIRED_MANAGER_TOOLS:
        if tool_name not in tool_names:
            blockers.append(f"missing_manager_tool:{tool_name}")

    artifact: dict[str, Any] = {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_manager_tool_surface_inventory",
        "status": "manager_tool_surface_inventory_ready_for_human_review",
        "scope": "plce_non_fooddb_app_state_tool_convergence",
        "required_direct_lane_ids": list(REQUIRED_DIRECT_LANE_IDS),
        "required_manager_tools": list(REQUIRED_MANAGER_TOOLS),
        "current_direct_lanes": lanes,
        "target_manager_tools": tools,
        "summary": {
            "direct_lane_count": len(lanes),
            "target_tool_count": len(tools),
            "mutation_bearing_lane_count": sum(1 for lane in lanes if lane.get("tool_kind") == "mutation_bearing"),
            "read_only_tool_count": sum(1 for tool in tools if tool.get("tool_kind") == "read_only"),
        },
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_packet_schema_changed": False,
        "shared_contract_changed": False,
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
    return artifact
