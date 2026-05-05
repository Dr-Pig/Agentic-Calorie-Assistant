from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


_FORBIDDEN_TRUE_FLAGS = {
    "live_websearch_used": "extract_report_used_live_websearch",
    "source_live_websearch_used": "extract_report_used_source_live_websearch",
    "live_provider_used": "extract_report_used_live_provider",
    "runtime_truth_changed": "extract_report_changed_runtime_truth",
    "mutation_changed": "extract_report_changed_mutation",
    "websearch_runtime_truth_allowed": "extract_report_allowed_websearch_runtime_truth",
    "runtime_mutation_allowed": "extract_report_allowed_runtime_mutation",
    "runtime_web_activation_approved": "extract_report_approved_runtime_web_activation",
    "runtime_web_activation_recommended": (
        "extract_report_recommended_runtime_web_activation"
    ),
    "ready_for_runtime_truth": "extract_report_claimed_ready_for_runtime_truth",
    "ready_for_runtime_mutation": "extract_report_claimed_ready_for_runtime_mutation",
    "readiness_claimed": "extract_report_claimed_readiness",
    "shared_contract_changed": "extract_report_changed_shared_contract",
    "nutrition_evidence_store_port_changed": (
        "extract_report_changed_nutrition_evidence_store_port"
    ),
    "manager_context_changed": "extract_report_changed_manager_context",
    "manager_context_packet_changed": "extract_report_changed_manager_context_packet",
    "manager_context_packet_schema_changed": (
        "extract_report_changed_manager_context_packet_schema"
    ),
    "packetizer_format_changed": "extract_report_changed_packetizer_format",
    "packetizer_changed": "extract_report_changed_packetizer",
    "basket_semantics_changed": "extract_report_changed_basket_semantics",
    "product_loop_activated": "extract_report_activated_product_loop",
    "product_loop_integration_claimed": "extract_report_claimed_product_loop_integration",
    "ce_activated": "extract_report_activated_context_engineering",
    "context_engineering_changed": "extract_report_changed_context_engineering",
    "webshell_activated": "extract_report_activated_webshell",
    "webshell_changed": "extract_report_changed_webshell",
    "exact_card_created": "extract_report_created_exact_card",
}


def build_websearch_post_extract_lane_status_packet(
    *,
    extract_canary_report: dict[str, Any],
) -> dict[str, Any]:
    upstream_gate = _extract_report_gate(extract_canary_report)
    clear = upstream_gate["blocked"] is False
    return {
        "artifact_type": "accurate_intake_websearch_post_extract_lane_status_packet_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_websearch_post_extract_status_only",
        "claim_scope": "websearch_post_extract_lane_status_without_runtime_activation",
        "status": (
            "clear_for_exact_card_candidate_planning"
            if clear
            else "blocked_on_live_extract_report"
        ),
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "runtime_mutation_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "runtime_web_activation_approved": False,
        "runtime_web_activation_recommended": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "shared_contract_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "upstream_gate": upstream_gate,
        "summary": {
            "extract_report_status": extract_canary_report.get("status"),
            "extract_report_selected_option": extract_canary_report.get("selected_option"),
            "extract_port_used": extract_canary_report.get("extract_port_used") is True,
            "live_extract_used": extract_canary_report.get("live_extract_used") is True,
            "extract_report_case_count": _summary_int(
                extract_canary_report, "case_count"
            ),
            "extract_report_failure_count": _summary_int(
                extract_canary_report, "failure_count"
            ),
            "runtime_activation_ready_count": 0,
            "runtime_truth_allowed_count": 0,
        },
        "next_required_slices": _next_required_slices(upstream_gate),
        "non_claims": [
            "no_runtime_web_activation",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def _extract_report_gate(report: dict[str, Any]) -> dict[str, Any]:
    if (
        str(report.get("artifact_type") or "")
        != "accurate_intake_websearch_live_extract_canary_report_v1"
    ):
        raise ValueError("unsupported_post_extract_status_report")
    blockers: list[str] = []
    if report.get("status") != "trace_only_extract_canary_clean":
        blockers.append(f"extract_report_not_clean:{report.get('status')}")
    if report.get("selected_option") != "trace_only_extract_canary_continues":
        blockers.append("extract_report_not_continuing_trace_canary")
    if report.get("extract_port_used") is not True:
        blockers.append("extract_report_extract_port_not_used")
    blockers.extend(
        blocker for key, blocker in _FORBIDDEN_TRUE_FLAGS.items() if report.get(key) is True
    )
    integrity = report.get("input_integrity") if isinstance(report.get("input_integrity"), dict) else {}
    if integrity.get("passed") is not True:
        blockers.append("extract_report_input_integrity_failed")
    blockers.extend(
        f"extract_report_input_integrity:{blocker}"
        for blocker in integrity.get("blockers") or []
    )
    evidence = (
        report.get("evidence_summary")
        if isinstance(report.get("evidence_summary"), dict)
        else {}
    )
    if int(evidence.get("failure_count") or 0) != 0:
        blockers.append("extract_report_failure_count_nonzero")
    if int(evidence.get("summary_fail_count") or 0) != 0:
        blockers.append("extract_report_summary_fail_count_nonzero")
    if int(evidence.get("input_blocker_count") or 0) != 0:
        blockers.append("extract_report_input_blockers_present")
    blockers.extend(
        f"extract_report_evidence:{blocker}" for blocker in evidence.get("blockers") or []
    )
    boundary = (
        report.get("decision_boundary")
        if isinstance(report.get("decision_boundary"), dict)
        else {}
    )
    boundary_expectations = {
        "trace_extract_canary_is_runtime_activation_evidence": (
            "decision_boundary_claimed_trace_as_runtime_activation"
        ),
        "accepted_extract_rows_are_exact_truth": (
            "decision_boundary_claimed_extract_rows_as_exact_truth"
        ),
        "mutation_allowed": "decision_boundary_allowed_mutation",
        "product_readiness_claim_allowed": "decision_boundary_allowed_readiness_claim",
    }
    blockers.extend(
        blocker
        for key, blocker in boundary_expectations.items()
        if boundary.get(key) is True
    )
    if boundary.get("runtime_web_exact_lane_requires_new_slice") is not True:
        blockers.append("decision_boundary_missing_exact_lane_new_slice_requirement")
    return {
        "status": (
            "clear_for_exact_card_candidate_planning"
            if not blockers
            else "blocked_on_live_extract_report"
        ),
        "blocked": bool(blockers),
        "blockers": sorted(set(blockers)),
        "source_artifact_type": report.get("artifact_type"),
        "next_required_slice": (
            "websearch_exact_card_candidate_planning_after_live_extract"
            if not blockers
            else str(
                report.get("next_required_slice")
                or "inspect_websearch_live_extract_canary_blockers"
            )
        ),
    }


def _summary_int(report: dict[str, Any], key: str) -> int:
    summary = report.get("evidence_summary")
    if not isinstance(summary, dict):
        return 0
    value = summary.get(key)
    return value if isinstance(value, int) else 0


def _next_required_slices(upstream_gate: dict[str, Any]) -> list[str]:
    return [
        str(
            upstream_gate["next_required_slice"]
            or "inspect_websearch_post_extract_lane_status"
        )
    ]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_post_extract_lane_status_packet"]
