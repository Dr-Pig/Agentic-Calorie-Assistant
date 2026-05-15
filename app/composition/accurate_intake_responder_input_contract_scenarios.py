from __future__ import annotations

from typing import Any

from app.composition.accurate_intake_responder_input_contract_claims import (
    FORBIDDEN_CLAIMS_CONTRACT,
    allowed_fact_map,
    claim,
    evaluate_response,
    fact,
    json_safe,
)
from app.composition.responder_macro_claim_contract import (
    committed_macro_accepted_claims,
    committed_macro_allowed_facts,
    hidden_macro_scenario,
)


REQUIRED_SCENARIO_IDS = (
    "clarification_no_commit",
    "candidate_supported_no_mutation",
    "committed_backend_budget",
    "degraded_budget_unavailable",
    "correction_ambiguity",
    "macro_hidden_no_visible_claim",
)


def scenario(
    *,
    scenario_id: str,
    budget_status: str,
    allowed_facts: list[dict[str, Any]],
    accepted_claims: list[dict[str, Any]],
    rejected_claims: list[dict[str, Any]],
) -> dict[str, Any]:
    allowed = allowed_fact_map(allowed_facts)
    renderer_input = {
        "allowed_facts": allowed_facts,
        "forbidden_claims": list(FORBIDDEN_CLAIMS_CONTRACT),
        "item_results": [
            fact_row
            for fact_row in allowed_facts
            if fact_row.get("claim_type") in {"kcal", "candidate_state", "logged_status"}
        ],
        "ledger_mutation_result": {
            "mutation_authority": False,
            "source": "backend_structured_runtime_result",
        },
        "read_only": True,
    }
    accepted = evaluate_response(
        response={"response_id": f"{scenario_id}:accepted", "claims": accepted_claims},
        allowed_facts=allowed,
        budget_status=budget_status,
    )
    rejected = evaluate_response(
        response={"response_id": f"{scenario_id}:rejected", "claims": rejected_claims},
        allowed_facts=allowed,
        budget_status=budget_status,
    )
    return json_safe(
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


def scenario_specs() -> list[dict[str, Any]]:
    return [
        scenario(
            scenario_id="clarification_no_commit",
            budget_status="ready",
            allowed_facts=[
                fact("fact-no-commit", "logged_status", "not_logged"),
                fact("fact-followup", "followup", "\u8acb\u88dc\u5145\u6ef7\u5473\u54c1\u9805"),
            ],
            accepted_claims=[
                claim("logged_status", "fact-no-commit", "not_logged"),
                claim("followup", "fact-followup", "\u8acb\u88dc\u5145\u6ef7\u5473\u54c1\u9805"),
            ],
            rejected_claims=[
                claim("logged_status", "missing-logged", "logged"),
                claim("kcal", "missing-kcal", 420),
            ],
        ),
        scenario(
            scenario_id="candidate_supported_no_mutation",
            budget_status="ready",
            allowed_facts=[
                fact("fact-candidate-state", "candidate_state", "candidate_supported"),
                fact("fact-no-mutation", "logged_status", "not_logged"),
            ],
            accepted_claims=[
                claim("candidate_state", "fact-candidate-state", "candidate_supported"),
                claim("logged_status", "fact-no-mutation", "not_logged"),
            ],
            rejected_claims=[
                claim("selected_target", "missing-target", "drink-001"),
                claim("logged_status", "missing-logged", "logged"),
            ],
        ),
        scenario(
            scenario_id="committed_backend_budget",
            budget_status="ready",
            allowed_facts=[
                fact("fact-logged", "logged_status", "logged"),
                fact("fact-kcal", "kcal", 420),
                fact("fact-remaining", "remaining", 980),
                *[
                    fact(item["fact_id"], item["claim_type"], item["value"])
                    for item in committed_macro_allowed_facts()
                ],
            ],
            accepted_claims=[
                claim("logged_status", "fact-logged", "logged"),
                claim("kcal", "fact-kcal", 420),
                claim("remaining", "fact-remaining", 980),
                *[
                    claim(item["claim_type"], item["fact_id"], item["value"])
                    for item in committed_macro_accepted_claims()
                ],
            ],
            rejected_claims=[
                claim("exactness", "missing-exactness", "official_exact"),
                claim("readiness", "missing-readiness", "private_self_use_ready"),
            ],
        ),
        scenario(
            scenario_id="degraded_budget_unavailable",
            budget_status="onboarding_required",
            allowed_facts=[
                fact("fact-budget-status", "budget_status", "onboarding_required"),
                fact("fact-no-remaining", "remaining_status", "not_available"),
            ],
            accepted_claims=[
                claim("budget_status", "fact-budget-status", "onboarding_required"),
                claim("remaining_status", "fact-no-remaining", "not_available"),
            ],
            rejected_claims=[
                claim("remaining", "missing-remaining", 500),
            ],
        ),
        scenario(
            scenario_id="correction_ambiguity",
            budget_status="ready",
            allowed_facts=[
                fact("fact-ambiguity", "candidate_state", "ambiguous"),
                fact("fact-no-commit", "logged_status", "not_logged"),
            ],
            accepted_claims=[
                claim("candidate_state", "fact-ambiguity", "ambiguous"),
                claim("logged_status", "fact-no-commit", "not_logged"),
            ],
            rejected_claims=[
                claim("selected_target", "missing-target", "tofu-001"),
                claim("logged_status", "missing-logged", "logged"),
            ],
        ),
        scenario(**hidden_macro_scenario()),
    ]


__all__ = ["REQUIRED_SCENARIO_IDS", "scenario", "scenario_specs"]
