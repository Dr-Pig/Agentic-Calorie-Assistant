from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_manager_tool_choice_regression_wall import (
    build_manager_tool_choice_regression_wall_artifact,
)
from app.composition.accurate_intake_manager_tool_surface_inventory import (
    build_manager_tool_surface_inventory_artifact,
)

REQUIRED_CASE_IDS = (
    "budget_remaining_read",
    "budget_day_meal_log_read",
    "body_active_plan_read",
    "body_latest_observation_read",
    "calibration_pending_proposal_read",
    "app_usage_help_read",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _fact(fact_id: str, claim_type: str, value: Any) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "claim_type": claim_type,
        "value": value,
        "source": "deterministic_domain_read_model_fixture",
        "read_only": True,
        "mutation_authority": False,
    }


def _claim(claim_type: str, fact_id: str, value: Any) -> dict[str, Any]:
    return {"claim_type": claim_type, "fact_id": fact_id, "value": value}


def _evaluate(claims: list[dict[str, Any]], allowed_facts: list[dict[str, Any]]) -> dict[str, Any]:
    allowed = {str(fact["fact_id"]): fact for fact in allowed_facts}
    blockers: list[str] = []
    normalized: list[dict[str, Any]] = []
    for claim in claims:
        fact = allowed.get(str(claim.get("fact_id")))
        normalized.append({**claim, "allowed_fact_present": fact is not None})
        if fact is None:
            blockers.append("claim_fact_id_not_allowed")
        elif fact.get("claim_type") != claim.get("claim_type"):
            blockers.append("claim_type_does_not_match_allowed_fact")
        elif fact.get("value") != claim.get("value"):
            blockers.append("claim_value_does_not_match_allowed_fact")
    return {"verdict": "accepted" if not blockers else "blocked", "blockers": sorted(set(blockers)), "claims": normalized}


def _case(case_id: str, selected_tool: str, truth_owner: str, facts: list[dict[str, Any]], accepted: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> dict[str, Any]:
    result = {
        "tool_name": selected_tool,
        "truth_owner": truth_owner,
        "tool_execution_source": "deterministic_domain_read_model_fixture",
        "read_only": True,
        "mutation_authority": False,
        "allowed_facts": facts,
    }
    return {
        "case_id": case_id,
        "selected_tool": selected_tool,
        "fixture_manager_decision": {
            "semantic_source": "fixture_manager_structured_decision",
            "selected_tool": selected_tool,
        },
        "tool_result_envelope": result,
        "responder_input": {"allowed_facts": facts, "forbidden_claims": ["readiness", "fooddb_truth", "mutation_without_guard"]},
        "accepted_response": _evaluate(accepted, facts),
        "rejected_response": _evaluate(rejected, facts),
    }


def _cases() -> list[dict[str, Any]]:
    return [
        _case("budget_remaining_read", "budget.get_remaining_calories", "budget_domain", [_fact("remaining-kcal", "remaining", 880)], [_claim("remaining", "remaining-kcal", 880)], [_claim("remaining", "missing", 500)]),
        _case("budget_day_meal_log_read", "budget.get_day_meal_log", "intake_and_budget_projection", [_fact("meal-log-status", "meal_log_status", "available")], [_claim("meal_log_status", "meal-log-status", "available")], [_claim("kcal", "missing-kcal", 999)]),
        _case("body_active_plan_read", "body.get_active_plan", "body_domain", [_fact("body-plan", "body_plan_status", "active")], [_claim("body_plan_status", "body-plan", "active")], [_claim("tdee", "missing-tdee", 2000)]),
        _case("body_latest_observation_read", "body.get_latest_observation", "body_domain", [_fact("latest-weight", "latest_weight", 72.4)], [_claim("latest_weight", "latest-weight", 72.4)], [_claim("latest_weight", "missing-weight", 70.0)]),
        _case("calibration_pending_proposal_read", "calibration.get_pending_proposal", "calibration_domain", [_fact("pending-proposal", "pending_proposal_status", "not_available")], [_claim("pending_proposal_status", "pending-proposal", "not_available")], [_claim("calibration_action", "missing-action", "applied")]),
        _case("app_usage_help_read", "app.answer_usage_question", "app_product_policy", [_fact("usage-help", "usage_guidance", "record_food_with_context")], [_claim("usage_guidance", "usage-help", "record_food_with_context")], [_claim("readiness", "missing-ready", "approved")]),
    ]


def _validate(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    ids = {str(case.get("case_id")) for case in cases}
    for case_id in REQUIRED_CASE_IDS:
        if case_id not in ids:
            blockers.append(f"missing_case:{case_id}")
    for case in cases:
        case_id = str(case.get("case_id"))
        decision = case.get("fixture_manager_decision") if isinstance(case.get("fixture_manager_decision"), dict) else {}
        result = case.get("tool_result_envelope") if isinstance(case.get("tool_result_envelope"), dict) else {}
        if decision.get("selected_tool") != case.get("selected_tool"):
            blockers.append(f"{case_id}.fixture_selected_tool_mismatch")
        if result.get("read_only") is not True:
            blockers.append(f"{case_id}.tool_result_not_read_only")
        if result.get("mutation_authority") is not False:
            blockers.append(f"{case_id}.mutation_authority")
        if not result.get("allowed_facts"):
            blockers.append(f"{case_id}.allowed_facts_missing")
        if case.get("accepted_response", {}).get("verdict") != "accepted":
            blockers.append(f"{case_id}.accepted_response_not_accepted")
        if case.get("rejected_response", {}).get("verdict") != "blocked":
            blockers.append(f"{case_id}.rejected_response_not_blocked")
    return blockers


def _read_only_contract_map(inventory_payload: dict[str, Any]) -> dict[str, str]:
    return {
        str(tool.get("tool_name")): str(tool.get("truth_owner"))
        for tool in list(inventory_payload.get("target_manager_tools") or [])
        if isinstance(tool, dict) and tool.get("tool_kind") == "read_only"
    }


def _validate_against_contract(cases: list[dict[str, Any]], contract: dict[str, str]) -> list[str]:
    blockers: list[str] = []
    allowed_truth_owners = set(contract.values())
    for case in cases:
        case_id = str(case.get("case_id"))
        selected_tool = str(case.get("selected_tool") or "")
        result = case.get("tool_result_envelope") if isinstance(case.get("tool_result_envelope"), dict) else {}
        responder_input = case.get("responder_input") if isinstance(case.get("responder_input"), dict) else {}
        result_tool_name = str(result.get("tool_name") or "")
        result_truth_owner = str(result.get("truth_owner") or "")
        if selected_tool not in contract:
            blockers.append(f"{case_id}.selected_tool_not_in_non_fooddb_read_only_contract")
        if result_tool_name and result_tool_name != selected_tool:
            blockers.append(f"{case_id}.tool_result_tool_name_selected_tool_mismatch")
        if result_tool_name and result_tool_name not in contract:
            blockers.append(f"{case_id}.tool_result_tool_name_not_in_non_fooddb_read_only_contract")
        expected_truth_owner = contract.get(selected_tool) or contract.get(result_tool_name)
        if result_truth_owner not in allowed_truth_owners or (
            expected_truth_owner is not None and result_truth_owner != expected_truth_owner
        ):
            blockers.append(f"{case_id}.truth_owner_contract_mismatch")
        if result.get("tool_execution_source") != "deterministic_domain_read_model_fixture":
            blockers.append(f"{case_id}.tool_execution_source_not_deterministic_read_model_fixture")
        if not isinstance(responder_input.get("forbidden_claims"), list) or not responder_input.get("forbidden_claims"):
            blockers.append(f"{case_id}.responder_forbidden_claims_missing")
    return blockers


def build_non_fooddb_read_only_tool_loop_fake_smoke_artifact(
    *, inventory: dict[str, Any] | None = None, tool_choice_wall: dict[str, Any] | None = None, cases: list[dict[str, Any]] | None = None, overrides: dict[str, Any] | None = None
) -> dict[str, Any]:
    inventory_payload = inventory if inventory is not None else build_manager_tool_surface_inventory_artifact()
    wall_payload = tool_choice_wall if tool_choice_wall is not None else build_manager_tool_choice_regression_wall_artifact()
    scenario_cases = deepcopy(cases if cases is not None else _cases())
    contract = _read_only_contract_map(inventory_payload)
    blockers = _validate(scenario_cases) + _validate_against_contract(scenario_cases, contract)
    if inventory_payload.get("status") != "manager_tool_surface_inventory_ready_for_human_review":
        blockers.append("manager_tool_surface_inventory.not_ready")
    if wall_payload.get("status") != "manager_tool_choice_regression_wall_pass":
        blockers.append("manager_tool_choice_regression_wall.not_pass")
    artifact: dict[str, Any] = {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke",
        "status": "non_fooddb_read_only_tool_loop_fake_smoke_pass",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "claim_scope": "non_fooddb_read_only_tool_loop_fixture_smoke",
        "cases": scenario_cases,
        "summary": {"case_count": len(scenario_cases)},
        "fixture_manager_used": True,
        "semantic_owner": "fixture_manager_structured_decision",
        "tool_execution_owner": "deterministic_domain_read_model_fixture",
        "responder_role": "mirror_allowed_facts_only",
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
    artifact["blockers"] = list(artifact.get("blockers") or []) + _validate(final_cases) + _validate_against_contract(final_cases, contract)
    artifact["summary"] = {"case_count": len(final_cases)}
    for flag in ("live_llm_invoked", "fooddb_used", "web_tavily_used", "mutation_changed", "product_readiness_claimed"):
        if artifact.get(flag) is True and flag not in artifact["blockers"]:
            artifact["blockers"].append(flag)
    artifact["blockers"] = sorted(set(str(blocker) for blocker in artifact["blockers"]))
    if artifact["blockers"]:
        artifact["status"] = "blocked"
    return _json_safe(artifact)


__all__ = ["build_non_fooddb_read_only_tool_loop_fake_smoke_artifact"]
