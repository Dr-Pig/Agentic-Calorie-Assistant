from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.nutrition.application.grokfast_websearch_packet_evaluation import (
    evaluate_manager_output_against_review_packet,
)
from app.nutrition.application.grokfast_websearch_packet_fixtures import (
    build_fixture_manager_outputs,
)
from app.nutrition.application.grokfast_websearch_packet_payload import (
    build_live_manager_payload,
)
from app.nutrition.application.grokfast_websearch_packet_profile import (
    GROKFAST_WEBSEARCH_PACKET_PROFILE,
    ManagerContractValidator,
    NON_CLAIMS,
    WEBSEARCH_PACKET_MANAGER_REQUIRED_FIELDS,
)


def build_grokfast_websearch_packet_diagnostic(
    *,
    review_packet_artifact: dict[str, Any],
    manager_outputs: list[dict[str, Any]],
    live_provider_used: bool,
    status: str | None = None,
    failure_family: str | None = None,
    manager_contract_validator: ManagerContractValidator | None = None,
) -> dict[str, Any]:
    outputs_by_packet = {
        str(item.get("packet_id")): item
        for item in manager_outputs
        if isinstance(item, dict) and item.get("packet_id")
    }
    case_results = []
    review_packets = [
        packet
        for packet in review_packet_artifact.get("review_packets") or []
        if isinstance(packet, dict)
    ]
    if not review_packets:
        return {
            "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
            "artifact_schema_version": "1.0",
            "generated_at_utc": _now(),
            "track": "FDB",
            "classification": "live_diagnostic_only",
            "status": status or "blocked",
            "failure_family": failure_family or "missing_review_packets",
            "claim_scope": "grokfast_manager_websearch_review_packet_seam_smoke",
            "provider_profile": dict(GROKFAST_WEBSEARCH_PACKET_PROFILE),
            "live_provider_used": live_provider_used,
            "readiness_claimed": False,
            "self_use_approved": False,
            "production_selected": False,
            "runtime_mutation_attempted": False,
            "runtime_truth_changed": False,
            "manager_context_changed": False,
            "packetizer_format_changed": False,
            "review_packet_artifact_type": review_packet_artifact.get("artifact_type"),
            "cases": [],
            "summary": {
                "case_count": 0,
                "pass_count": 0,
                "fail_count": 1,
                "failure_families": ["missing_review_packets"],
            },
            "non_claims": list(NON_CLAIMS),
        }

    for packet in review_packets:
        output = outputs_by_packet.get(str(packet.get("packet_id") or ""))
        if output is None:
            case_results.append(
                {
                    "packet_id": packet.get("packet_id"),
                    "status": "fail",
                    "failure_families": ["missing_manager_output"],
                    "provider_trace": {},
                }
            )
            continue
        evaluation = evaluate_manager_output_against_review_packet(
            review_packet=packet,
            manager_output=dict(output.get("manager_output") or {}),
            manager_contract_validation_errors=(
                manager_contract_validator(packet, dict(output.get("manager_output") or {}))
                if manager_contract_validator is not None
                else []
            ),
        )
        evaluation["provider_trace"] = dict(output.get("provider_trace") or {})
        case_results.append(evaluation)

    pass_count = sum(1 for item in case_results if item.get("status") == "pass")
    fail_count = len(case_results) - pass_count
    return {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "live_diagnostic_only",
        "status": status or ("pass" if fail_count == 0 else "diagnostic_fail"),
        "failure_family": failure_family,
        "claim_scope": "grokfast_manager_websearch_review_packet_seam_smoke",
        "provider_profile": dict(GROKFAST_WEBSEARCH_PACKET_PROFILE),
        "live_provider_used": live_provider_used,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "runtime_mutation_attempted": False,
        "runtime_truth_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "review_packet_artifact_type": review_packet_artifact.get("artifact_type"),
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "failure_families": sorted(
                {
                    family
                    for item in case_results
                    for family in item.get("failure_families", [])
                    if family
                }
            ),
        },
        "non_claims": list(NON_CLAIMS),
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "GROKFAST_WEBSEARCH_PACKET_PROFILE",
    "ManagerContractValidator",
    "NON_CLAIMS",
    "WEBSEARCH_PACKET_MANAGER_REQUIRED_FIELDS",
    "build_fixture_manager_outputs",
    "build_grokfast_websearch_packet_diagnostic",
    "build_live_manager_payload",
    "evaluate_manager_output_against_review_packet",
]
