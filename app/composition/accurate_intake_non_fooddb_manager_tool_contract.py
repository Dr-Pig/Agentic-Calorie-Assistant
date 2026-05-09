from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.composition.accurate_intake_manager_tool_surface_inventory import (
    REQUIRED_DIRECT_LANE_IDS,
    build_manager_tool_surface_inventory_artifact,
)

_OWNER = "manager"
_ROLE = "choose_tool_then_validate_guard_and_execute_domain_contract"


def _row(name: str, kind: str, owner: str, stage: str, lanes: list[str], *, callable_by_manager: bool = True, guard: bool = False, stored: bool = False, explicit: list[str] | None = None, allowed: list[str] | None = None, forbidden: list[str] | None = None, manager_target: bool = False, debt: str | None = None) -> dict[str, Any]:
    return {
        "tool_name": name,
        "tool_kind": kind,
        "truth_owner": owner,
        "contract_stage": stage,
        "tool_callable_by_manager": callable_by_manager,
        "guard_required": guard,
        "stored_proposal_required": stored,
        "explicit_request_fields": explicit or [],
        "allowed_domain_effects": allowed or [],
        "forbidden_domain_effects": forbidden or [],
        "manager_structured_target_required": manager_target,
        "debt_marker": debt,
        "current_direct_lane_ids": lanes,
        "raw_text_authorizes_mutation": False,
        "frontend_semantic_owner": False,
        "semantic_owner": _OWNER,
        "deterministic_role": _ROLE,
    }


def _bridge(lane_id: str, tool_names: list[str], stage: str, *, debt: str | None = None) -> dict[str, Any]:
    return {
        "direct_lane_id": lane_id,
        "contract_tool_names": tool_names,
        "contract_stage": stage,
        "debt_marker": debt,
    }


_ROWS = (
    _row("budget.get_today_summary", "read_only", "budget_domain", "inventory_backed", ["estimate_general_chat_budget_summary"]),
    _row("budget.get_remaining_calories", "read_only", "budget_domain", "inventory_backed", ["estimate_general_chat_budget_summary"]),
    _row("budget.get_day_meal_log", "read_only", "intake_and_budget_projection", "inventory_backed", []),
    _row("body.get_active_plan", "read_only", "body_domain", "inventory_backed", ["estimate_general_chat_goal_summary"]),
    _row("body.get_latest_observation", "read_only", "body_domain", "inventory_backed", []),
    _row("body.record_observation", "mutation_bearing", "body_domain", "inventory_backed", ["estimate_body_observation_record_weight"], guard=True, allowed=["body_observation_write_only"], forbidden=["body_plan_mutation", "ledger_mutation"]),
    _row("calibration.preview_proposal", "proposal_persisting", "calibration_domain", "inventory_backed", ["estimate_explicit_calibration_preview"], guard=True, allowed=["proposal_preview_optional_open_container"], forbidden=["body_plan_mutation", "ledger_mutation"]),
    _row("calibration.get_pending_proposal", "read_only", "calibration_domain", "inventory_backed", []),
    _row("calibration.apply_stored_proposal_action", "mutation_bearing", "calibration_domain", "inventory_backed", ["estimate_explicit_calibration_action"], guard=True, stored=True, explicit=["calibration_proposal_container_id", "calibration_action"], allowed=["proposal_status_change", "body_plan_mutation", "ledger_mutation", "current_budget_refresh"]),
    _row("app.answer_usage_question", "read_only", "app_product_policy", "inventory_backed", ["estimate_general_chat_fallback_answer"]),
    _row("budget.set_manual_daily_target", "mutation_bearing", "budget_domain", "inventory_backed", ["estimate_manual_daily_target_structured_update"], guard=True, explicit=["daily_target_kcal"], allowed=["body_plan_mutation", "ledger_mutation", "current_budget_refresh"], manager_target=True),
)

_BRIDGES = (
    _bridge("estimate_general_chat_budget_summary", ["budget.get_today_summary", "budget.get_remaining_calories"], "inventory_backed"),
    _bridge("estimate_general_chat_goal_summary", ["body.get_active_plan"], "inventory_backed"),
    _bridge("estimate_general_chat_fallback_answer", ["app.answer_usage_question"], "inventory_backed"),
    _bridge("estimate_explicit_calibration_preview", ["calibration.preview_proposal"], "inventory_backed"),
    _bridge("estimate_explicit_calibration_action", ["calibration.apply_stored_proposal_action"], "inventory_backed"),
    _bridge("estimate_body_observation_record_weight", ["body.record_observation"], "inventory_backed"),
    _bridge("estimate_manual_daily_target_structured_update", ["budget.set_manual_daily_target"], "inventory_backed"),
)


def build_tool_contract_index(payload: dict[str, Any], *, stages: set[str] | None = None, callable_only: bool = False) -> dict[str, dict[str, Any]]:
    rows = list(payload.get("tool_contract_rows") or [])
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if stages and str(row.get("contract_stage")) not in stages:
            continue
        if callable_only and row.get("tool_callable_by_manager") is not True:
            continue
        name = str(row.get("tool_name") or "")
        if name:
            index[name] = row
    return index


def _inventory_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(tool.get("tool_name")): dict(tool)
        for tool in list(payload.get("target_manager_tools") or [])
        if isinstance(tool, dict)
    }


def _validate(rows: list[dict[str, Any]], bridges: list[dict[str, Any]], inventory_payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if inventory_payload.get("status") != "manager_tool_surface_inventory_ready_for_human_review":
        blockers.append("manager_tool_surface_inventory.not_ready")
    inventory = _inventory_index(inventory_payload)
    backed = [row for row in rows if row.get("contract_stage") == "inventory_backed"]
    if len(backed) < 10:
        blockers.append("inventory_backed_contract_count_too_low")
    if len(inventory) < 10:
        blockers.append("inventory_backed_contract_count_too_low")
    read_only = [row for row in rows if row.get("tool_kind") == "read_only"]
    if len(read_only) < 7:
        blockers.append("read_only_contract_count_too_low")
    if len(bridges) < len(REQUIRED_DIRECT_LANE_IDS):
        blockers.append("direct_lane_bridge_count_too_low")
    bridge_ids = {str(bridge.get("direct_lane_id")) for bridge in bridges}
    for lane_id in REQUIRED_DIRECT_LANE_IDS:
        if lane_id not in bridge_ids:
            blockers.append(f"missing_direct_lane_bridge:{lane_id}")
    for row in backed:
        tool_name = str(row.get("tool_name") or "")
        expected = inventory.get(tool_name)
        if expected is None:
            blockers.append(f"{tool_name}.missing_from_inventory")
            continue
        for key in ("tool_kind", "truth_owner", "guard_required", "stored_proposal_required"):
            if row.get(key) != expected.get(key):
                blockers.append(f"{tool_name}.{key}_contract_mismatch")
        if bool(row.get("manager_structured_target_required")) is not bool(
            expected.get("manager_structured_target_required")
        ):
            blockers.append(f"{tool_name}.manager_structured_target_contract_mismatch")
    row_index = build_tool_contract_index({"tool_contract_rows": rows})
    for bridge in bridges:
        lane_id = str(bridge.get("direct_lane_id") or "")
        for tool_name in list(bridge.get("contract_tool_names") or []):
            if tool_name not in row_index:
                blockers.append(f"{lane_id}.missing_contract_tool:{tool_name}")
    return blockers


def build_non_fooddb_manager_tool_contract_artifact(*, inventory: dict[str, Any] | None = None, rows: list[dict[str, Any]] | None = None, direct_lane_bridge: list[dict[str, Any]] | None = None, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    inventory_payload = inventory if inventory is not None else build_manager_tool_surface_inventory_artifact()
    contract_rows = deepcopy(rows if rows is not None else list(_ROWS))
    bridges = deepcopy(direct_lane_bridge if direct_lane_bridge is not None else list(_BRIDGES))
    blockers = _validate(contract_rows, bridges, inventory_payload)
    artifact: dict[str, Any] = {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_non_fooddb_manager_tool_contract",
        "status": "non_fooddb_manager_tool_contract_ready_for_human_review",
        "claim_scope": "plce_non_fooddb_manager_tool_contract_pre_live_diagnostic_only",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "tool_contract_rows": contract_rows,
        "direct_lane_bridge": bridges,
        "summary": {
            "inventory_backed_tool_count": sum(1 for row in contract_rows if row.get("contract_stage") == "inventory_backed"),
            "read_only_tool_count": sum(1 for row in contract_rows if row.get("tool_kind") == "read_only"),
            "proposal_tool_count": sum(1 for row in contract_rows if row.get("tool_kind") == "proposal_persisting"),
            "mutation_tool_count": sum(1 for row in contract_rows if row.get("tool_kind") == "mutation_bearing"),
            "legacy_direct_route_debt_count": sum(1 for row in contract_rows if row.get("contract_stage") == "legacy_direct_lane_debt"),
            "direct_lane_bridge_count": len(bridges),
        },
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_packet_schema_changed": False,
        "fooddb_used": False,
        "web_tavily_used": False,
        "live_llm_invoked": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "blockers": blockers,
    }
    artifact.update(overrides or {})
    for flag in ("live_llm_invoked", "fooddb_used", "shared_contract_changed", "runtime_truth_changed", "mutation_changed", "manager_context_packet_schema_changed", "product_readiness_claimed", "private_self_use_approved"):
        if artifact.get(flag) is True and flag not in artifact["blockers"]:
            artifact["blockers"].append(flag)
    artifact["blockers"] = sorted(set(str(blocker) for blocker in artifact["blockers"]))
    if artifact["blockers"]:
        artifact["status"] = "blocked"
    return artifact


__all__ = [
    "build_non_fooddb_manager_tool_contract_artifact",
    "build_tool_contract_index",
]
