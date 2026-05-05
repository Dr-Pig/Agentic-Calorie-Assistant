from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .food_evidence_index_port import FoodEvidenceIndexPort
from .food_evidence_retriever_execution_cases import (
    RetrieverExecutionCase,
    default_retriever_execution_cases,
)
from .food_evidence_retriever_execution_paths import case_result
from .food_evidence_retriever_router import (
    RetrieverBackendAvailability,
)


def build_food_evidence_retriever_execution_smoke(
    *,
    index: FoodEvidenceIndexPort,
    availability: RetrieverBackendAvailability,
    cases: tuple[RetrieverExecutionCase, ...] = (),
) -> dict[str, Any]:
    execution_cases = cases or default_retriever_execution_cases()
    case_results = [
        case_result(case, index=index, availability=availability) for case in execution_cases
    ]
    blockers = [
        f"retriever_execution_case_failed:{case['case_id']}"
        for case in case_results
        if case["status"] != "pass"
    ]
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_food_evidence_retriever_execution_smoke_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_retriever_execution_smoke_only",
        "claim_scope": "fooddb_websearch_retriever_execution_boundary",
        "status": "pass" if clear else "blocked",
        "blockers": blockers,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "pass_count": sum(1 for case in case_results if case["status"] == "pass"),
            "fail_count": sum(1 for case in case_results if case["status"] != "pass"),
            "fooddb_tool_result_count": sum(
                1 for case in case_results if case["tool_name"] == "lookup_food_evidence"
            ),
            "websearch_tool_result_count": sum(
                1 for case in case_results if case["tool_name"] == "search_official_nutrition"
            ),
            "ask_followup_case_count": sum(
                1 for case in case_results if case["route_plan"]["primary_backend"] == "ask_followup"
            ),
            "blocked_no_execution_case_count": sum(
                1
                for case in case_results
                if case["route_plan"]["primary_backend"] == "blocked_no_execution"
            ),
        },
        "dependency_inversion": {
            "intent_source": "manager_owned_retrieval_intent_or_fixture_in_tests",
            "deterministic_role": "execute_route_plan_and_validate_boundaries",
            "deterministic_does_not_own": [
                "user_intent",
                "workflow_effect",
                "final_action",
                "mutation_legality",
                "fooddb_truth_promotion",
            ],
            "backend_implementation_manager_visible": False,
        },
        "next_required_slice": (
            "grokfast_fooddb_diagnostic_preflight"
            if clear
            else "inspect_food_evidence_retriever_execution_blockers"
        ),
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_readiness_claim",
        ],
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "RetrieverExecutionCase",
    "build_food_evidence_retriever_execution_smoke",
]
