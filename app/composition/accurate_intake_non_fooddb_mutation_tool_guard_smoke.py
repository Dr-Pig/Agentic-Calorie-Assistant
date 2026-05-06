from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_manager_tool_choice_regression_wall import build_manager_tool_choice_regression_wall_artifact
from app.composition.accurate_intake_non_fooddb_manager_tool_contract import (
    build_non_fooddb_manager_tool_contract_artifact,
    build_tool_contract_index,
)

REQUIRED_CASE_IDS = ("body_record_weight_observation_only", "body_record_weight_invalid_payload_blocked", "calibration_preview_no_persist_default", "calibration_preview_persist_open_proposal_only", "calibration_apply_missing_stored_proposal_blocked", "calibration_apply_accept_stored_proposal_guarded", "calibration_apply_reject_stored_proposal_no_plan_ledger", "manual_daily_target_manager_structured_only", "manual_daily_target_out_of_bounds_blocked", "legacy_delta_kcal_direct_route_debt")
_TOOL_ROLE = "validate_guard_and_execute_existing_domain_contract"

def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))

def _effects(**overrides: bool) -> dict[str, bool]:
    base = {
        "body_observation_written": False,
        "proposal_persisted": False,
        "proposal_status_changed": False,
        "body_plan_mutated": False,
        "ledger_mutated": False,
        "current_budget_refreshed": False,
    }
    base.update(overrides)
    return base

def _case(
    case_id: str,
    selected_tool: str,
    tool_kind: str,
    truth_owner: str,
    guard_posture: str,
    expected_effects: dict[str, bool],
    *,
    guard_required: bool = False,
    stored_proposal_required: bool = False,
    mutation_allowed: bool = False,
    inventory_alignment: str = "inventory_backed",
    manager_structured_target_required: bool = False,
    debt_marker: str | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "selected_tool": selected_tool,
        "tool_kind": tool_kind,
        "truth_owner": truth_owner,
        "guard_posture": guard_posture,
        "guard_required": guard_required,
        "stored_proposal_required": stored_proposal_required,
        "mutation_allowed": mutation_allowed,
        "raw_text_authorizes_mutation": False,
        "frontend_semantic_owner": False,
        "deterministic_role": _TOOL_ROLE,
        "inventory_alignment": inventory_alignment,
        "manager_structured_target_required": manager_structured_target_required,
        "debt_marker": debt_marker,
        "expected_effects": expected_effects,
        "fixture_manager_decision": {
            "semantic_source": "fixture_manager_structured_decision",
            "selected_tool": selected_tool,
            "tool_kind": tool_kind,
            "semantic_owner": "manager",
        },
    }

def _cases() -> list[dict[str, Any]]:
    return [
        _case("body_record_weight_observation_only", "body.record_observation", "mutation_bearing", "body_domain", "observation_only_guarded_write", _effects(body_observation_written=True), guard_required=True, mutation_allowed=True),
        _case("body_record_weight_invalid_payload_blocked", "body.record_observation", "mutation_bearing", "body_domain", "invalid_payload_blocked", _effects(), guard_required=True),
        _case("calibration_preview_no_persist_default", "calibration.preview_proposal", "proposal_persisting", "calibration_domain", "proposal_preview_without_persistence", _effects(), guard_required=True),
        _case("calibration_preview_persist_open_proposal_only", "calibration.preview_proposal", "proposal_persisting", "calibration_domain", "proposal_preview_persist_open_container_only", _effects(proposal_persisted=True), guard_required=True),
        _case("calibration_apply_missing_stored_proposal_blocked", "calibration.get_pending_proposal", "read_only", "calibration_domain", "blocked_without_stored_proposal", _effects()),
        _case("calibration_apply_accept_stored_proposal_guarded", "calibration.apply_stored_proposal_action", "mutation_bearing", "calibration_domain", "stored_proposal_action_guarded_mutation", _effects(proposal_status_changed=True, body_plan_mutated=True, ledger_mutated=True, current_budget_refreshed=True), guard_required=True, stored_proposal_required=True, mutation_allowed=True),
        _case("calibration_apply_reject_stored_proposal_no_plan_ledger", "calibration.apply_stored_proposal_action", "mutation_bearing", "calibration_domain", "stored_proposal_action_status_only", _effects(proposal_status_changed=True), guard_required=True, stored_proposal_required=True, mutation_allowed=True),
        _case("manual_daily_target_manager_structured_only", "budget.set_manual_daily_target", "mutation_bearing", "budget_domain", "manager_structured_budget_target_write", _effects(body_plan_mutated=True, ledger_mutated=True, current_budget_refreshed=True), guard_required=True, mutation_allowed=True, inventory_alignment="adjacent_pending_inventory_expansion", manager_structured_target_required=True),
        _case("manual_daily_target_out_of_bounds_blocked", "budget.set_manual_daily_target", "mutation_bearing", "budget_domain", "manager_structured_budget_target_blocked", _effects(), guard_required=True, inventory_alignment="adjacent_pending_inventory_expansion", manager_structured_target_required=True),
        _case("legacy_delta_kcal_direct_route_debt", "legacy.calibration_delta_kcal_direct_route", "legacy_direct_route", "calibration_domain", "legacy_direct_route_debt", _effects(), inventory_alignment="legacy_direct_lane_debt", debt_marker="direct_route_mutation_before_manager_tool_contract"),
    ]

def _validate(cases: list[dict[str, Any]], contract: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    case_ids = {str(case.get("case_id")) for case in cases}
    for case_id in REQUIRED_CASE_IDS:
        if case_id not in case_ids:
            blockers.append(f"missing_case:{case_id}")
    for case in cases:
        case_id = str(case.get("case_id"))
        selected_tool = str(case.get("selected_tool") or "")
        tool_kind = str(case.get("tool_kind") or "")
        truth_owner = str(case.get("truth_owner") or "")
        effects = case.get("expected_effects") if isinstance(case.get("expected_effects"), dict) else {}
        decision = case.get("fixture_manager_decision") if isinstance(case.get("fixture_manager_decision"), dict) else {}
        alignment = str(case.get("inventory_alignment") or "inventory_backed")
        if decision.get("semantic_source") != "fixture_manager_structured_decision":
            blockers.append(f"{case_id}.semantic_source_not_fixture_manager")
        if decision.get("selected_tool") != selected_tool:
            blockers.append(f"{case_id}.fixture_selected_tool_mismatch")
        if case.get("raw_text_authorizes_mutation") is not False:
            blockers.append(f"{case_id}.raw_text_authorizes_mutation")
        if case.get("frontend_semantic_owner") is not False:
            blockers.append(f"{case_id}.frontend_semantic_owner")
        if case.get("deterministic_role") != _TOOL_ROLE:
            blockers.append(f"{case_id}.deterministic_role_mismatch")
        if selected_tool == "body.record_observation" and (effects.get("body_plan_mutated") or effects.get("ledger_mutated")):
            blockers.append(f"{case_id}.body_observation_must_not_mutate_body_plan")
        if selected_tool == "calibration.preview_proposal" and (effects.get("body_plan_mutated") or effects.get("ledger_mutated")):
            blockers.append(f"{case_id}.calibration_preview_must_not_mutate_plan_or_ledger")
        if selected_tool == "calibration.apply_stored_proposal_action" and case.get("stored_proposal_required") is not True:
            blockers.append(f"{case_id}.stored_proposal_required_missing")
        if alignment == "inventory_backed":
            expected = contract.get(selected_tool)
            if expected is None:
                blockers.append(f"{case_id}.selected_tool_not_in_inventory_contract")
            else:
                if tool_kind != str(expected.get("tool_kind") or ""):
                    blockers.append(f"{case_id}.tool_kind_contract_mismatch")
                if truth_owner != str(expected.get("truth_owner") or ""):
                    blockers.append(f"{case_id}.truth_owner_contract_mismatch")
                if bool(case.get("guard_required")) is not bool(expected.get("guard_required")):
                    blockers.append(f"{case_id}.guard_requirement_contract_mismatch")
                if bool(case.get("stored_proposal_required")) is not bool(expected.get("stored_proposal_required")):
                    blockers.append(f"{case_id}.stored_proposal_contract_mismatch")
        elif alignment == "adjacent_pending_inventory_expansion":
            expected = contract.get(selected_tool)
            if selected_tool != "budget.set_manual_daily_target" or expected is None:
                blockers.append(f"{case_id}.manual_daily_target_selected_tool_mismatch")
            if tool_kind != "mutation_bearing" or tool_kind != str(expected.get("tool_kind") or ""):
                blockers.append(f"{case_id}.manual_daily_target_tool_kind_mismatch")
            if truth_owner != "budget_domain" or truth_owner != str(expected.get("truth_owner") or ""):
                blockers.append(f"{case_id}.manual_daily_target_truth_owner_mismatch")
            if case.get("guard_required") is not True or bool(expected.get("guard_required")) is not True:
                blockers.append(f"{case_id}.manual_daily_target_guard_required_missing")
            if case.get("manager_structured_target_required") is not True or bool(expected.get("manager_structured_target_required")) is not True:
                blockers.append(f"{case_id}.manager_structured_target_required_missing")
            if case_id == "manual_daily_target_out_of_bounds_blocked" and case.get("mutation_allowed") is not False:
                blockers.append(f"{case_id}.manual_daily_target_blocked_case_must_not_allow_mutation")
        elif alignment == "legacy_direct_lane_debt":
            expected = contract.get(selected_tool)
            if expected is None or case.get("debt_marker") != str(expected.get("debt_marker") or ""):
                blockers.append(f"{case_id}.legacy_direct_route_debt_marker_missing")
            if case.get("mutation_allowed") is not False:
                blockers.append(f"{case_id}.legacy_direct_route_must_not_be_allowed")
        else:
            blockers.append(f"{case_id}.unknown_inventory_alignment")
    return blockers

def build_non_fooddb_mutation_tool_guard_smoke_artifact(
    *, tool_contract: dict[str, Any] | None = None, tool_choice_wall: dict[str, Any] | None = None,
    cases: list[dict[str, Any]] | None = None, overrides: dict[str, Any] | None = None
) -> dict[str, Any]:
    contract_payload = tool_contract if tool_contract is not None else build_non_fooddb_manager_tool_contract_artifact()
    wall_payload = tool_choice_wall if tool_choice_wall is not None else build_manager_tool_choice_regression_wall_artifact()
    scenario_cases = deepcopy(cases if cases is not None else _cases())
    blockers = _validate(scenario_cases, build_tool_contract_index(contract_payload))
    if contract_payload.get("status") != "non_fooddb_manager_tool_contract_ready_for_human_review":
        blockers.append("non_fooddb_manager_tool_contract.not_ready")
    if wall_payload.get("status") != "manager_tool_choice_regression_wall_pass":
        blockers.append("manager_tool_choice_regression_wall.not_pass")
    artifact: dict[str, Any] = {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_non_fooddb_mutation_tool_guard_smoke",
        "status": "non_fooddb_mutation_tool_guard_smoke_pass",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "claim_scope": "non_fooddb_mutation_and_proposal_guard_fixture_smoke",
        "cases": scenario_cases,
        "summary": {"case_count": len(scenario_cases)},
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
    final_cases = deepcopy(artifact.get("cases") if isinstance(artifact.get("cases"), list) else [])
    artifact["blockers"] = list(artifact.get("blockers") or []) + _validate(final_cases, build_tool_contract_index(contract_payload))
    artifact["summary"] = {"case_count": len(final_cases)}
    for flag in ("live_llm_invoked", "fooddb_used", "web_tavily_used", "runtime_truth_changed", "mutation_changed", "manager_context_packet_schema_changed", "product_readiness_claimed", "private_self_use_approved"):
        if artifact.get(flag) is True and flag not in artifact["blockers"]:
            artifact["blockers"].append(flag)
    artifact["blockers"] = sorted(set(str(blocker) for blocker in artifact["blockers"]))
    if artifact["blockers"]:
        artifact["status"] = "blocked"
    return _json_safe(artifact)

__all__ = ["build_non_fooddb_mutation_tool_guard_smoke_artifact"]
