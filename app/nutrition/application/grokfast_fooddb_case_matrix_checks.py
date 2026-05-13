from __future__ import annotations

from typing import Any


def case_matrix_blockers(
    artifact: dict[str, Any],
    *,
    expected_artifact_type: str,
    required_case_ids: tuple[str, ...],
    required_non_claims: tuple[str, ...],
) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != expected_artifact_type:
        blockers.append("unsupported_fooddb_grokfast_case_matrix_artifact")
        return blockers
    summary = dict(artifact.get("summary") or {})
    if artifact.get("status") != "pass":
        blockers.append("fooddb_grokfast_case_matrix_not_pass")
    if artifact.get("plan_only") is not True:
        blockers.append("fooddb_grokfast_case_matrix_not_plan_only")
    if artifact.get("live_llm_invoked") is not False:
        blockers.append("fooddb_grokfast_case_matrix_invoked_live_llm")
    if artifact.get("live_provider_invoked") is not False:
        blockers.append("fooddb_grokfast_case_matrix_invoked_live_provider")
    if artifact.get("websearch_invoked") is not False:
        blockers.append("fooddb_grokfast_case_matrix_invoked_websearch")
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("fooddb_grokfast_case_matrix_changed_runtime_truth")
    if artifact.get("mutation_changed") is not False:
        blockers.append("fooddb_grokfast_case_matrix_changed_mutation")
    if artifact.get("manager_context_packet_changed") is not False:
        blockers.append("fooddb_grokfast_case_matrix_changed_manager_context")
    if artifact.get("shared_contract_changed") is not False:
        blockers.append("fooddb_grokfast_case_matrix_changed_shared_contract")
    if artifact.get("product_readiness_claimed") is not False:
        blockers.append("fooddb_grokfast_case_matrix_claimed_readiness")
    if artifact.get("private_self_use_approved") is not False:
        blockers.append("fooddb_grokfast_case_matrix_claimed_self_use_approval")
    if int(summary.get("case_count", 0) or 0) < len(required_case_ids):
        blockers.append("fooddb_grokfast_case_matrix_too_few_cases")
    case_ids = [
        str(case.get("case_id") or "")
        for case in artifact.get("cases") or []
        if isinstance(case, dict)
    ]
    if case_ids != list(required_case_ids):
        blockers.append("fooddb_grokfast_case_matrix_required_case_order_mismatch")
    if int(summary.get("modifier_guard_cases", 0) or 0) < 2:
        blockers.append("fooddb_grokfast_case_matrix_missing_modifier_guard_cases")
    if int(summary.get("bare_basket_cases", 0) or 0) < 1:
        blockers.append("fooddb_grokfast_case_matrix_missing_bare_basket_case")
    if int(summary.get("listed_basket_cases", 0) or 0) < 1:
        blockers.append("fooddb_grokfast_case_matrix_missing_listed_basket_case")
    if int(summary.get("websearch_cases", 0) or 0) != 0:
        blockers.append("fooddb_grokfast_case_matrix_includes_websearch_cases")
    if int(summary.get("exact_card_cases", 0) or 0) < 1:
        blockers.append("fooddb_grokfast_case_matrix_missing_exact_card_case")
    if int(summary.get("query_only_cases", 0) or 0) < 1:
        blockers.append("fooddb_grokfast_case_matrix_missing_query_only_case")
    if int(summary.get("macro_hidden_cases", 0) or 0) < 1:
        blockers.append("fooddb_grokfast_case_matrix_missing_macro_hidden_case")
    non_claims = set(artifact.get("non_claims") or [])
    for required in required_non_claims:
        if required not in non_claims:
            blockers.append(f"fooddb_grokfast_case_matrix_missing_non_claim.{required}")
    return blockers


__all__ = ["case_matrix_blockers"]
