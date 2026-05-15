from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.composition.accurate_intake_responder_input_contract_claims import (
    allowed_fact_map,
    evaluate_response,
    json_safe,
)
from app.composition.accurate_intake_responder_input_contract_scenarios import (
    REQUIRED_SCENARIO_IDS,
    scenario_specs,
)


_REQUIRED_SCENARIO_IDS = REQUIRED_SCENARIO_IDS
_allowed_fact_map = allowed_fact_map
_evaluate_response = evaluate_response
_scenario_specs = scenario_specs


def _validate(scenarios: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    scenario_ids = [str(scenario.get("scenario_id") or "") for scenario in scenarios]
    if scenario_ids != list(REQUIRED_SCENARIO_IDS):
        blockers.append("required_scenario_order_mismatch")
    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id") or "unknown")
        if scenario.get("semantic_owner") != "manager_and_backend_structured_runtime_facts":
            blockers.append(f"{scenario_id}.semantic_owner_not_backend_runtime_facts")
        if scenario.get("responder_role") != "mirror_allowed_facts_only":
            blockers.append(f"{scenario_id}.responder_role_not_mirror_only")
        renderer = scenario.get("renderer")
        renderer_input = renderer.get("input") if isinstance(renderer, dict) else None
        if not isinstance(renderer_input, dict):
            blockers.append(f"{scenario_id}.renderer_input_missing")
        else:
            if not isinstance(renderer_input.get("allowed_facts"), list):
                blockers.append(f"{scenario_id}.renderer_allowed_facts_missing")
            if not isinstance(renderer_input.get("forbidden_claims"), list):
                blockers.append(f"{scenario_id}.renderer_forbidden_claims_missing")
            if not isinstance(renderer_input.get("item_results"), list):
                blockers.append(f"{scenario_id}.renderer_item_results_missing")
            if not isinstance(renderer_input.get("ledger_mutation_result"), dict):
                blockers.append(f"{scenario_id}.renderer_ledger_mutation_result_missing")
        if scenario.get("fake_responder_used") is not True:
            blockers.append(f"{scenario_id}.fake_responder_not_used")
        if scenario.get("responder_claims_require_allowed_fact_id") is not True:
            blockers.append(f"{scenario_id}.allowed_fact_id_not_required")
        if scenario.get("raw_text_claim_grading_used") is not False:
            blockers.append(f"{scenario_id}.raw_text_claim_grading_used")
        if scenario.get("live_llm_invoked") is not False:
            blockers.append(f"{scenario_id}.live_llm_invoked")
        if scenario.get("mutation_authority") is not False:
            blockers.append(f"{scenario_id}.mutation_authority")
        accepted = scenario.get("accepted_response")
        rejected = scenario.get("rejected_response")
        if not isinstance(accepted, dict) or accepted.get("verdict") != "accepted":
            blockers.append(f"{scenario_id}.accepted_response_not_accepted")
        if not isinstance(rejected, dict) or rejected.get("verdict") != "blocked":
            blockers.append(f"{scenario_id}.rejected_response_not_blocked")
    return blockers


def build_responder_input_contract_fake_smoke_artifact() -> dict[str, Any]:
    scenarios = scenario_specs()
    blockers = _validate(scenarios)
    return json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_responder_input_contract_fake_smoke",
            "status": "pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "local_responder_input_contract_fake_smoke",
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "fake_responder_used": True,
            "structured_allowed_facts_required": True,
            "responder_claims_require_allowed_fact_id": True,
            "semantic_owner": "manager_and_backend_structured_runtime_facts",
            "responder_role": "mirror_allowed_facts_only",
            "raw_text_claim_grading_used": False,
            "live_llm_invoked": False,
            "live_provider_called": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "fooddb_evidence_used": False,
            "fooddb_truth_updated": False,
            "mutation_authority": False,
            "mutation_changed": False,
            "runtime_truth_changed": False,
            "manager_context_packet_schema_changed": False,
            "production_db_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": blockers,
            "summary": {
                "scenario_count": len(scenarios),
                "accepted_response_count": sum(
                    1
                    for scenario in scenarios
                    if scenario["accepted_response"]["verdict"] == "accepted"
                ),
                "rejected_response_count": sum(
                    1
                    for scenario in scenarios
                    if scenario["rejected_response"]["verdict"] == "blocked"
                ),
                "raw_text_claim_grading_used": False,
                "live_llm_invoked": False,
            },
            "scenarios": scenarios,
            "best_practice_basis": {
                "structured_outputs": "responder claims are schema-like objects with required fact_id links",
                "tool_context": "responder sees app-provided allowed facts instead of raw tool traces",
            },
        }
    )


__all__ = ["build_responder_input_contract_fake_smoke_artifact"]
