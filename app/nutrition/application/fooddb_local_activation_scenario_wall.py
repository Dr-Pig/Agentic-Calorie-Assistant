from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .fooddb_local_activation_scenario_cases import (
    FOODDB_LOCAL_ACTIVATION_SCENARIO_CASES,
    FoodDBActivationScenarioCase,
)
from .fooddb_local_activation_scenario_eval import build_case_result
from .fooddb_retrieval_policy import IndexedFoodRecord


def build_fooddb_local_activation_scenario_wall(
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
    activation_wall_artifact: dict[str, Any] | None = None,
    cases: tuple[
        FoodDBActivationScenarioCase, ...
    ] = FOODDB_LOCAL_ACTIVATION_SCENARIO_CASES,
) -> dict[str, Any]:
    case_results = [
        build_case_result(case, retrieval_records=retrieval_records) for case in cases
    ]
    blockers = [
        f"{case['turn_id']}:{check['check_id']}"
        for case in case_results
        for check in case["checks"]
        if check["status"] != "pass"
    ]
    activation_wall_status = _activation_wall_status(activation_wall_artifact)
    if activation_wall_status != "pass":
        blockers.append(f"activation_wall_status:{activation_wall_status}")
    status = "pass" if not blockers else "blocked"
    upstream_next_required = _activation_wall_upstream_next_required(
        activation_wall_artifact
    )
    return {
        "artifact_type": "accurate_intake_fooddb_local_activation_scenario_wall_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_fooddb_local_activation_scenario_wall_only",
        "claim_scope": "fooddb_real_packet_scenario_wall_without_runtime_mutation",
        "status": status,
        "blockers": blockers,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "runner_inferred_semantics": False,
        "activation_wall_status": activation_wall_status,
        "upstream_next_required_slices": upstream_next_required,
        "summary": _summary(case_results),
        "cases": case_results,
        "next_required_slice": _next_required_slice(
            status=status, upstream_next_required=upstream_next_required
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


def _summary(case_results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "scenario_turn_count": len(case_results),
        "fooddb_packet_required_turn_count": _case_count(
            case_results, "fooddb_packet_required"
        ),
        "fooddb_packet_pass_turn_count": _case_count(
            case_results, "fooddb_packet_required", status="pass"
        ),
        "no_fooddb_lookup_turn_count": _case_count(
            case_results,
            "target_evidence_only_no_fooddb_lookup",
            "read_only_query_no_fooddb_lookup",
        ),
        "followup_no_mutation_turn_count": _case_count(
            case_results, "followup_no_mutation_no_fooddb_estimate"
        ),
    }


def _case_count(
    case_results: list[dict[str, Any]], *postures: str, status: str | None = None
) -> int:
    return sum(
        1
        for case in case_results
        if case["packet_posture"] in postures
        and (status is None or case["status"] == status)
    )


def _activation_wall_status(activation_wall_artifact: dict[str, Any] | None) -> str:
    if not isinstance(activation_wall_artifact, dict):
        return "not_provided"
    if (
        activation_wall_artifact.get("artifact_type")
        != "accurate_intake_fooddb_activation_wall_v1"
    ):
        return "unsupported_activation_wall_artifact"
    return str(activation_wall_artifact.get("status") or "unknown")


def _activation_wall_upstream_next_required(
    activation_wall_artifact: dict[str, Any] | None,
) -> list[str]:
    if not isinstance(activation_wall_artifact, dict):
        return ["not_provided"]
    return [
        str(slice_id)
        for slice_id in activation_wall_artifact.get("upstream_next_required_slices")
        or []
        if str(slice_id).strip()
    ]


def _next_required_slice(*, status: str, upstream_next_required: list[str]) -> str:
    if status != "pass":
        return (
            "build_fooddb_activation_wall_first"
            if "not_provided" in upstream_next_required
            else "inspect_fooddb_local_activation_scenario_wall_blockers"
        )
    if upstream_next_required:
        return upstream_next_required[0]
    return "grokfast_fooddb_activation_packet_seam_rerun"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "FOODDB_LOCAL_ACTIVATION_SCENARIO_CASES",
    "FoodDBActivationScenarioCase",
    "build_fooddb_local_activation_scenario_wall",
]
