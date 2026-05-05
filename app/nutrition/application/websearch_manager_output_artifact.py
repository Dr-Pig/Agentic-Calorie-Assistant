from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.nutrition.application.websearch_manager_output_evaluation import (
    evaluate_manager_output_against_websearch_packet,
)
from app.nutrition.application.websearch_manager_output_policy import (
    WEBSEARCH_MANAGER_OUTPUT_NON_CLAIMS,
)


def build_websearch_manager_output_diagnostic(
    *,
    packet_artifact: dict[str, Any],
    manager_outputs: list[dict[str, Any]],
    live_provider_used: bool = False,
    status: str | None = None,
) -> dict[str, Any]:
    outputs_by_case = {
        str(output.get("case_id")): output
        for output in manager_outputs
        if isinstance(output, dict) and output.get("case_id")
    }
    case_results = []
    for packet_case in packet_artifact.get("cases") or []:
        if not isinstance(packet_case, dict):
            continue
        output = outputs_by_case.get(str(packet_case.get("case_id") or ""))
        if output is None:
            case_results.append(
                {
                    "case_id": packet_case.get("case_id"),
                    "status": "fail",
                    "failure_families": ["missing_manager_output"],
                    "provider_trace": {},
                }
            )
            continue
        evaluation = evaluate_manager_output_against_websearch_packet(
            packet_case=packet_case,
            manager_output=dict(output.get("manager_output") or {}),
        )
        evaluation["provider_trace"] = dict(output.get("provider_trace") or {})
        case_results.append(evaluation)

    artifact_failure_families = []
    if live_provider_used:
        artifact_failure_families.append("live_provider_used_in_deterministic_diagnostic")

    pass_count = sum(1 for item in case_results if item.get("status") == "pass")
    fail_count = len(case_results) - pass_count + len(artifact_failure_families)
    resolved_status = "diagnostic_fail" if fail_count else (status or "pass")
    return {
        "artifact_type": "accurate_intake_websearch_manager_output_diagnostic",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_diagnostic_only",
        "status": resolved_status,
        "claim_scope": "websearch_manager_output_candidate_boundary",
        "live_provider_used": live_provider_used,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "runtime_mutation_attempted": False,
        "runtime_truth_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "packet_artifact_type": packet_artifact.get("artifact_type"),
        "cases": case_results,
        "summary": build_websearch_manager_output_summary(
            case_results=case_results,
            artifact_failure_families=artifact_failure_families,
        ),
        "non_claims": list(WEBSEARCH_MANAGER_OUTPUT_NON_CLAIMS),
    }


def build_websearch_manager_output_summary(
    *,
    case_results: list[dict[str, Any]],
    artifact_failure_families: list[str],
) -> dict[str, Any]:
    pass_count = sum(1 for item in case_results if item.get("status") == "pass")
    fail_count = len(case_results) - pass_count + len(artifact_failure_families)
    return {
        "case_count": len(case_results),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "failure_families": sorted(
            {
                family
                for family in artifact_failure_families
            }
            | {
                family
                for item in case_results
                for family in item.get("failure_families", [])
                if family
            }
        ),
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "build_websearch_manager_output_diagnostic",
    "build_websearch_manager_output_summary",
]
