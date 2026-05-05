from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def build_websearch_live_search_canary_report(
    *,
    canary_artifact: dict[str, Any],
) -> dict[str, Any]:
    if (
        str(canary_artifact.get("artifact_type") or "")
        != "accurate_intake_websearch_live_search_diagnostic_canary_v1"
    ):
        raise ValueError("unsupported_websearch_live_search_canary_artifact")
    cases = [case for case in canary_artifact.get("cases") or [] if isinstance(case, dict)]
    input_integrity = _input_integrity(canary_artifact=canary_artifact, cases=cases)
    evidence_summary = _evidence_summary(canary_artifact=canary_artifact, cases=cases)
    blocked = (
        input_integrity["passed"] is not True
        or evidence_summary["failure_count"] > 0
        or evidence_summary["summary_fail_count"] > 0
        or evidence_summary["input_blocker_count"] > 0
        or bool(evidence_summary["blockers"])
    )
    clean = (
        canary_artifact.get("status") == "pass"
        and evidence_summary["case_count"] > 0
        and not blocked
    )
    selected_option = "trace_only_canary_continues" if clean else "no_live_search_seam"
    return {
        "artifact_type": "accurate_intake_websearch_live_search_canary_report_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "diagnostic_report_only",
        "claim_scope": "websearch_live_search_canary_report_without_runtime_activation",
        "status": "trace_only_canary_clean" if clean else "blocked",
        "source_artifact_type": canary_artifact.get("artifact_type"),
        "readiness_claimed": False,
        "runtime_web_activation_approved": False,
        "runtime_web_activation_recommended": False,
        "ready_for_runtime_truth": False,
        "ready_for_runtime_mutation": False,
        "requires_owner_decision": False,
        "selected_option": selected_option,
        "selection_reason": (
            "trace_only_canary_clean_but_runtime_activation_not_approved"
            if clean
            else "canary_blocked_or_not_clean"
        ),
        "decision_boundary": {
            "trace_canary_is_runtime_activation_evidence": False,
            "accepted_extract_packet_is_exact_truth": False,
            "runtime_web_seam_requires_new_slice": True,
            "mutation_allowed": False,
            "product_readiness_claim_allowed": False,
        },
        "input_integrity": input_integrity,
        "evidence_summary": evidence_summary,
        "next_required_slice": (
            "websearch_trace_only_canary_observation_or_exact_lane_decision"
            if clean
            else "inspect_websearch_live_search_canary_blockers"
        ),
        "non_claims": [
            "no_runtime_web_activation",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def _input_integrity(
    *,
    canary_artifact: dict[str, Any],
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers: list[str] = []
    if canary_artifact.get("readiness_claimed") is True:
        blockers.append("input_readiness_claimed")
    if canary_artifact.get("live_provider_used") is True:
        blockers.append("input_used_live_provider")
    if canary_artifact.get("live_websearch_used") is True:
        blockers.append("input_used_external_live_websearch")
    for key, blocker in (
        ("runtime_truth_changed", "input_runtime_truth_changed"),
        ("websearch_runtime_truth_allowed", "input_websearch_runtime_truth_allowed"),
        ("runtime_mutation_allowed", "input_runtime_mutation_allowed"),
        ("mutation_changed", "input_mutation_changed"),
        ("runtime_web_activation_approved", "input_runtime_web_activation_approved"),
        ("runtime_web_activation_recommended", "input_runtime_web_activation_recommended"),
        ("shared_contract_changed", "input_shared_contract_changed"),
        ("manager_context_changed", "input_manager_context_changed"),
        ("manager_context_packet_changed", "input_manager_context_packet_changed"),
        (
            "manager_context_packet_schema_changed",
            "input_manager_context_packet_schema_changed",
        ),
        ("packetizer_format_changed", "input_packetizer_format_changed"),
        ("packetizer_changed", "input_packetizer_changed"),
        ("ready_for_runtime_truth", "input_ready_for_runtime_truth"),
        ("ready_for_runtime_mutation", "input_ready_for_runtime_mutation"),
        ("nutrition_evidence_store_port_changed", "input_nutrition_evidence_store_port_changed"),
        ("basket_semantics_changed", "input_basket_semantics_changed"),
        ("product_loop_activated", "input_product_loop_activated"),
        ("product_loop_integration_claimed", "input_product_loop_integration_claimed"),
        ("ce_activated", "input_ce_activated"),
        ("context_engineering_changed", "input_context_engineering_changed"),
        ("webshell_activated", "input_webshell_activated"),
        ("webshell_changed", "input_webshell_changed"),
    ):
        if canary_artifact.get(key) is True:
            blockers.append(blocker)
    summary = canary_artifact.get("summary") if isinstance(canary_artifact.get("summary"), dict) else {}
    if int(summary.get("runtime_truth_allowed_count") or 0) != 0:
        blockers.append("summary_runtime_truth_allowed")
    for case in cases:
        if case.get("runtime_truth_allowed") is True:
            blockers.append("case_runtime_truth_allowed")
        if case.get("runtime_mutation_allowed") is True:
            blockers.append("case_runtime_mutation_allowed")
        if case.get("exact_card_created") is True:
            blockers.append("case_exact_card_created")
        trace = case.get("trace") if isinstance(case.get("trace"), dict) else {}
        boundary = trace.get("truth_boundary") if isinstance(trace.get("truth_boundary"), dict) else {}
        if boundary.get("web_candidate_truth_authority") is True:
            blockers.append("case_web_candidate_claimed_truth")
        if boundary.get("accepted_extract_packet_truth_authority") is True:
            blockers.append("case_accepted_extract_packet_claimed_truth")
        if boundary.get("runtime_web_activation_recommended") is True:
            blockers.append("case_runtime_web_activation_recommended")
        if trace.get("rejected_web_candidates_used_as_evidence") is True:
            blockers.append("case_rejected_candidate_used_as_evidence")
    return {
        "passed": not blockers,
        "blockers": sorted(set(blockers)),
    }


def _evidence_summary(
    *,
    canary_artifact: dict[str, Any],
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = canary_artifact.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    input_blockers = list(canary_artifact.get("blockers") or [])
    failure_cases = [case for case in cases if case.get("status") != "pass"]
    return {
        "canary_status": canary_artifact.get("status"),
        "case_count": len(cases),
        "pass_count": sum(1 for case in cases if case.get("status") == "pass"),
        "failure_count": len(failure_cases),
        "summary_fail_count": int(summary.get("fail_count") or 0),
        "input_blocker_count": len(input_blockers),
        "blockers": input_blockers,
        "search_port_used": canary_artifact.get("search_port_used") is True,
        "extract_port_used": canary_artifact.get("extract_port_used") is True,
        "live_websearch_used": canary_artifact.get("live_websearch_used") is True,
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_live_search_canary_report"]
