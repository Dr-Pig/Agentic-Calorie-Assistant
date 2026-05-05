from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.nutrition.application.websearch_manager_output_diagnostic import (
    build_fixture_websearch_manager_outputs,
    evaluate_manager_output_against_websearch_packet,
)


GROKFAST_WEBSEARCH_PACKET_PROFILE = {
    "provider_profile_id": "builderspace-grok-4-fast-websearch-packet-smoke",
    "provider": "builderspace",
    "model": "grok-4-fast",
    "provider_profile_role": "live_diagnostic_probe",
    "cost_tier": "low",
    "production_selected": False,
    "readiness_owner": False,
}

WEBSEARCH_GROKFAST_NON_CLAIMS = [
    "no_readiness_claim",
    "no_production_model_selection",
    "no_self_use_approval",
    "no_runtime_mutation",
    "no_websearch_runtime_truth",
    "no_exact_card_truth_promotion",
    "no_fooddb_truth_promotion",
    "no_kimi_call",
]


def build_fixture_grokfast_websearch_manager_outputs(
    *,
    packet_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    outputs = []
    for output in build_fixture_websearch_manager_outputs(packet_artifact=packet_artifact):
        provider_trace = dict(output.get("provider_trace") or {})
        provider_trace.update(
            {
                "fixture_provider": True,
                "provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"],
                "provider_profile_model": GROKFAST_WEBSEARCH_PACKET_PROFILE["model"],
                "provider_profile_role": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_role"],
            }
        )
        outputs.append(
            {
                "case_id": output.get("case_id"),
                "manager_output": dict(output.get("manager_output") or {}),
                "provider_trace": provider_trace,
            }
        )
    return outputs


def build_grokfast_websearch_packet_diagnostic(
    *,
    packet_artifact: dict[str, Any],
    manager_outputs: list[dict[str, Any]],
    live_provider_used: bool,
    status: str | None = None,
    failure_family: str | None = None,
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
        provider_trace = dict(output.get("provider_trace") or {})
        provider_failure_family = _provider_failure_family(provider_trace)
        if provider_failure_family:
            evaluation["failure_families"] = [
                *evaluation.get("failure_families", []),
                provider_failure_family,
            ]
            evaluation["status"] = "fail"
        evaluation["provider_trace"] = _sanitize_provider_trace(provider_trace)
        case_results.append(_sanitize_case_evaluation(evaluation))

    pass_count = sum(1 for item in case_results if item.get("status") == "pass")
    fail_count = len(case_results) - pass_count
    resolved_status = status or ("pass" if fail_count == 0 else "diagnostic_fail")
    return {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "live_diagnostic_only",
        "status": resolved_status,
        "failure_family": failure_family,
        "claim_scope": "grokfast_manager_websearch_packet_seam_smoke",
        "provider_profile": dict(GROKFAST_WEBSEARCH_PACKET_PROFILE),
        "live_provider_used": live_provider_used,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "runtime_mutation_attempted": False,
        "runtime_truth_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "websearch_runtime_truth_allowed": False,
        "packet_artifact_type": packet_artifact.get("artifact_type"),
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
        "non_claims": list(WEBSEARCH_GROKFAST_NON_CLAIMS),
    }


def build_live_websearch_manager_payload(*, packet_case: dict[str, Any]) -> dict[str, Any]:
    packet = dict(packet_case.get("manager_evidence_packet") or {})
    return {
        "diagnostic_scope": "websearch_packet_manager_seam_smoke",
        "raw_user_input": packet_case.get("raw_user_input") or packet.get("raw_user_input"),
        "websearch_evidence_packet": packet,
        "instructions": [
            "Use only the provided compact WebSearch evidence packet.",
            "Treat every WebSearch packet as candidate-only and not runtime nutrition truth.",
            "Do not invent source IDs, kcal values, exact-card truth, FoodDB truth, item_results, or ledger writes.",
            "Do not call tools for WebSearch candidate-only packets; this is source candidate review, not nutrition estimation.",
            "Use final_action='no_commit' for candidate review or weak-source rejection; use final_action='ask_followup' when identity, size, or variant is ambiguous.",
            "Cite only provided candidate packet IDs or provided source_url values in answer_contract.source_candidate_refs.",
            "Keep top-level target_attachment empty for candidate-only WebSearch evidence.",
            "Keep semantic_decision.target_attachment empty too; do not attach candidate packets as mutation or correction targets.",
            "Set semantic_decision.mutation_intent_candidate='no_mutation' for every WebSearch candidate-only response.",
            "For exact brand/menu candidates, keep the source candidate pending for later promotion review.",
            "For related or weak candidates, ask follow-up or reject/request a better source.",
            "This diagnostic is no-commit and grants no readiness.",
        ],
        "constraints": {
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": "common_commercial_drink",
            "websearch_packet_smoke": True,
            "websearch_runtime_truth_allowed": False,
            "runtime_mutation_allowed": False,
            "expected_behavior": packet_case.get("manager_expected_behavior"),
            "case_id": packet_case.get("case_id"),
        },
        "allowed_evidence_refs": _allowed_evidence_refs(packet),
    }


def _allowed_evidence_refs(packet: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    packet_id = str(packet.get("packet_id") or "").strip()
    if packet_id:
        refs.append(packet_id)
    for item in packet.get("evidence_items") or []:
        if not isinstance(item, dict):
            continue
        for key in ("candidate_packet_id", "source_url"):
            value = str(item.get(key) or "").strip()
            if value and value not in refs:
                refs.append(value)
    return refs


def blocked_live_artifact() -> dict[str, Any]:
    return {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "live_diagnostic_only",
        "status": "blocked",
        "failure_family": "live_mode_requires_explicit_allow_live",
        "claim_scope": "grokfast_manager_websearch_packet_seam_smoke",
        "provider_profile": dict(GROKFAST_WEBSEARCH_PACKET_PROFILE),
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "runtime_mutation_attempted": False,
        "runtime_truth_changed": False,
        "websearch_runtime_truth_allowed": False,
        "non_claims": list(WEBSEARCH_GROKFAST_NON_CLAIMS),
    }


def _sanitize_case_evaluation(evaluation: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": evaluation.get("case_id"),
        "status": evaluation.get("status"),
        "failure_families": list(evaluation.get("failure_families") or []),
        "manager_expected_behavior": evaluation.get("manager_expected_behavior"),
        "used_evidence_ref_count": len(evaluation.get("used_evidence_refs") or []),
        "allowed_evidence_ref_count": evaluation.get("allowed_evidence_ref_count"),
        "invented_evidence_ref_count": len(evaluation.get("invented_evidence_refs") or []),
        "manager_action": evaluation.get("manager_action"),
        "final_action": evaluation.get("final_action"),
        "runtime_mutation_attempted": bool(evaluation.get("runtime_mutation_attempted")),
        "mutation_signal": dict(evaluation.get("mutation_signal") or {}),
        "provider_trace": dict(evaluation.get("provider_trace") or {}),
    }


def _sanitize_provider_trace(provider_trace: dict[str, Any]) -> dict[str, Any]:
    trace = provider_trace.get("trace")
    trace_source = trace if isinstance(trace, dict) else provider_trace
    trace_summary = {}
    if isinstance(trace_source, dict):
        trace_summary = {
            "failure_family": trace_source.get("failure_family"),
            "failing_component": trace_source.get("failing_component"),
            "request_failure_family": trace_source.get("request_failure_family"),
            "parse_contract_status": trace_source.get("parse_contract_status"),
            "repair_attempted": trace_source.get("repair_attempted"),
            "repair_result": trace_source.get("repair_result"),
            "transport_attempt_count": len(trace_source.get("transport_attempts") or []),
            "parse_attempt_count": len(trace_source.get("parse_attempts") or []),
            "structured_output_transport_mode": trace_source.get("structured_output_transport_mode"),
            "decision_transport_mode": trace_source.get("decision_transport_mode"),
            "decision_transport_attempted": trace_source.get("decision_transport_attempted"),
            "decision_transport_contract_breach": trace_source.get("decision_transport_contract_breach"),
            "schema_name": trace_source.get("schema_name"),
            "schema_version": trace_source.get("schema_version"),
        }
    return {
        "provider_profile_id": provider_trace.get("provider_profile_id"),
        "provider_profile_model": provider_trace.get("provider_profile_model"),
        "provider_profile_role": provider_trace.get("provider_profile_role"),
        "fixture_provider": provider_trace.get("fixture_provider"),
        "failure_family": provider_trace.get("failure_family"),
        "error_type": provider_trace.get("failure_family"),
        "trace_summary": trace_summary,
    }


def _provider_failure_family(provider_trace: dict[str, Any]) -> str | None:
    failure_family = str(provider_trace.get("failure_family") or "").strip()
    if failure_family:
        return failure_family
    trace = provider_trace.get("trace")
    if isinstance(trace, dict):
        failure_family = str(trace.get("failure_family") or "").strip()
        if failure_family:
            return failure_family
    return None


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "GROKFAST_WEBSEARCH_PACKET_PROFILE",
    "WEBSEARCH_GROKFAST_NON_CLAIMS",
    "blocked_live_artifact",
    "build_fixture_grokfast_websearch_manager_outputs",
    "build_grokfast_websearch_packet_diagnostic",
    "build_live_websearch_manager_payload",
]
