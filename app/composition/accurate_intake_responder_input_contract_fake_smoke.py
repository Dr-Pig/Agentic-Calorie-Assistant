from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


_REQUIRED_SCENARIO_IDS = (
    "clarification_no_commit",
    "candidate_supported_no_mutation",
    "committed_backend_budget",
    "degraded_budget_unavailable",
    "correction_ambiguity",
)

_FORBIDDEN_CLAIM_TYPES = {
    "readiness",
    "self_use_approval",
    "fooddb_truth",
    "web_truth",
    "selected_target",
}

_FORBIDDEN_CLAIMS_CONTRACT = [
    "logged_status_without_allowed_fact",
    "kcal_without_allowed_fact",
    "remaining_without_allowed_fact",
    "exactness_without_allowed_fact",
    "selected_target_without_manager_decision",
    "readiness_or_self_use_approval",
]

_INVENTION_BLOCKER_BY_CLAIM_TYPE = {
    "logged_status": "invented_logged_status",
    "kcal": "invented_kcal_claim",
    "remaining": "invented_remaining_claim",
    "exactness": "invented_exactness_claim",
    "selected_target": "invented_target_selection",
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _fact(
    fact_id: str,
    claim_type: str,
    value: Any,
    *,
    source: str = "backend_structured_read_model",
) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "claim_type": claim_type,
        "value": value,
        "source": source,
        "read_only": True,
        "mutation_authority": False,
    }


def _claim(
    claim_type: str,
    fact_id: str,
    value: Any,
) -> dict[str, Any]:
    return {
        "claim_type": claim_type,
        "fact_id": fact_id,
        "value": value,
    }


def _allowed_fact_map(allowed_facts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(fact.get("fact_id") or ""): fact for fact in allowed_facts}


def _evaluate_response(
    *,
    response: dict[str, Any],
    allowed_facts: dict[str, dict[str, Any]],
    budget_status: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    normalized_claims: list[dict[str, Any]] = []
    claims = response.get("claims", [])
    if not isinstance(claims, list) or not claims:
        blockers.append("claims_missing")
        claims = []
    for claim in claims:
        if not isinstance(claim, dict):
            blockers.append("claim_not_structured_object")
            continue
        claim_type = str(claim.get("claim_type") or "")
        fact_id = str(claim.get("fact_id") or "")
        allowed_fact = allowed_facts.get(fact_id)
        normalized_claims.append(
            {
                "claim_type": claim_type,
                "fact_id": fact_id,
                "value": claim.get("value"),
                "allowed_fact_present": allowed_fact is not None,
            }
        )
        if claim_type in _FORBIDDEN_CLAIM_TYPES:
            if claim_type == "readiness":
                blockers.append("readiness_claim_forbidden")
            elif claim_type == "selected_target":
                blockers.append("invented_target_selection")
            else:
                blockers.append(f"{claim_type}_claim_forbidden")
        if allowed_fact is None:
            blockers.append("claim_fact_id_not_allowed")
            invention_blocker = _INVENTION_BLOCKER_BY_CLAIM_TYPE.get(claim_type)
            if invention_blocker is not None:
                blockers.append(invention_blocker)
            continue
        if allowed_fact.get("claim_type") != claim_type:
            blockers.append("claim_type_does_not_match_allowed_fact")
        if allowed_fact.get("value") != claim.get("value"):
            blockers.append("claim_value_does_not_match_allowed_fact")
    if budget_status != "ready":
        for claim in response.get("claims", []):
            if isinstance(claim, dict) and claim.get("claim_type") == "remaining":
                blockers.append("degraded_budget_concrete_remaining_forbidden")
    blockers = sorted(set(blockers))
    return _json_safe(
        {
            "response_id": response.get("response_id"),
            "verdict": "accepted" if not blockers else "blocked",
            "blockers": blockers,
            "claims": normalized_claims,
            "structured_claims_used": True,
            "raw_text_claim_grading_used": False,
        }
    )


def _scenario(
    *,
    scenario_id: str,
    budget_status: str,
    allowed_facts: list[dict[str, Any]],
    accepted_claims: list[dict[str, Any]],
    rejected_claims: list[dict[str, Any]],
) -> dict[str, Any]:
    allowed = _allowed_fact_map(allowed_facts)
    renderer_input = {
        "allowed_facts": allowed_facts,
        "forbidden_claims": list(_FORBIDDEN_CLAIMS_CONTRACT),
        "item_results": [
            fact
            for fact in allowed_facts
            if fact.get("claim_type") in {"kcal", "candidate_state", "logged_status"}
        ],
        "ledger_mutation_result": {
            "mutation_authority": False,
            "source": "backend_structured_runtime_result",
        },
        "read_only": True,
    }
    accepted = _evaluate_response(
        response={"response_id": f"{scenario_id}:accepted", "claims": accepted_claims},
        allowed_facts=allowed,
        budget_status=budget_status,
    )
    rejected = _evaluate_response(
        response={"response_id": f"{scenario_id}:rejected", "claims": rejected_claims},
        allowed_facts=allowed,
        budget_status=budget_status,
    )
    return _json_safe(
        {
            "scenario_id": scenario_id,
            "budget_status": budget_status,
            "renderer": {"input": renderer_input},
            "allowed_facts": renderer_input["allowed_facts"],
            "forbidden_claims": renderer_input["forbidden_claims"],
            "item_results": renderer_input["item_results"],
            "ledger_mutation_result": renderer_input["ledger_mutation_result"],
            "allowed_fact_ids": sorted(allowed),
            "accepted_response": accepted,
            "rejected_response": rejected,
            "semantic_owner": "manager_and_backend_structured_runtime_facts",
            "responder_role": "mirror_allowed_facts_only",
            "fake_responder_used": True,
            "responder_claims_require_allowed_fact_id": True,
            "raw_text_claim_grading_used": False,
            "live_llm_invoked": False,
            "mutation_authority": False,
        }
    )


def _scenario_specs() -> list[dict[str, Any]]:
    return [
        _scenario(
            scenario_id="clarification_no_commit",
            budget_status="ready",
            allowed_facts=[
                _fact("fact-no-commit", "logged_status", "not_logged"),
                _fact("fact-followup", "followup", "\u8acb\u88dc\u5145\u6ef7\u5473\u54c1\u9805"),
            ],
            accepted_claims=[
                _claim("logged_status", "fact-no-commit", "not_logged"),
                _claim("followup", "fact-followup", "\u8acb\u88dc\u5145\u6ef7\u5473\u54c1\u9805"),
            ],
            rejected_claims=[
                _claim("logged_status", "missing-logged", "logged"),
                _claim("kcal", "missing-kcal", 420),
            ],
        ),
        _scenario(
            scenario_id="candidate_supported_no_mutation",
            budget_status="ready",
            allowed_facts=[
                _fact("fact-candidate-state", "candidate_state", "candidate_supported"),
                _fact("fact-no-mutation", "logged_status", "not_logged"),
            ],
            accepted_claims=[
                _claim("candidate_state", "fact-candidate-state", "candidate_supported"),
                _claim("logged_status", "fact-no-mutation", "not_logged"),
            ],
            rejected_claims=[
                _claim("selected_target", "missing-target", "drink-001"),
                _claim("logged_status", "missing-logged", "logged"),
            ],
        ),
        _scenario(
            scenario_id="committed_backend_budget",
            budget_status="ready",
            allowed_facts=[
                _fact("fact-logged", "logged_status", "logged"),
                _fact("fact-kcal", "kcal", 420),
                _fact("fact-remaining", "remaining", 980),
            ],
            accepted_claims=[
                _claim("logged_status", "fact-logged", "logged"),
                _claim("kcal", "fact-kcal", 420),
                _claim("remaining", "fact-remaining", 980),
            ],
            rejected_claims=[
                _claim("exactness", "missing-exactness", "official_exact"),
                _claim("readiness", "missing-readiness", "private_self_use_ready"),
            ],
        ),
        _scenario(
            scenario_id="degraded_budget_unavailable",
            budget_status="onboarding_required",
            allowed_facts=[
                _fact("fact-budget-status", "budget_status", "onboarding_required"),
                _fact("fact-no-remaining", "remaining_status", "not_available"),
            ],
            accepted_claims=[
                _claim("budget_status", "fact-budget-status", "onboarding_required"),
                _claim("remaining_status", "fact-no-remaining", "not_available"),
            ],
            rejected_claims=[
                _claim("remaining", "missing-remaining", 500),
            ],
        ),
        _scenario(
            scenario_id="correction_ambiguity",
            budget_status="ready",
            allowed_facts=[
                _fact("fact-ambiguity", "candidate_state", "ambiguous"),
                _fact("fact-no-commit", "logged_status", "not_logged"),
            ],
            accepted_claims=[
                _claim("candidate_state", "fact-ambiguity", "ambiguous"),
                _claim("logged_status", "fact-no-commit", "not_logged"),
            ],
            rejected_claims=[
                _claim("selected_target", "missing-target", "tofu-001"),
                _claim("logged_status", "missing-logged", "logged"),
            ],
        ),
    ]


def _validate(scenarios: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    scenario_ids = [str(scenario.get("scenario_id") or "") for scenario in scenarios]
    if scenario_ids != list(_REQUIRED_SCENARIO_IDS):
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
    scenarios = _scenario_specs()
    blockers = _validate(scenarios)
    return _json_safe(
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
                    1 for scenario in scenarios if scenario["accepted_response"]["verdict"] == "accepted"
                ),
                "rejected_response_count": sum(
                    1 for scenario in scenarios if scenario["rejected_response"]["verdict"] == "blocked"
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
