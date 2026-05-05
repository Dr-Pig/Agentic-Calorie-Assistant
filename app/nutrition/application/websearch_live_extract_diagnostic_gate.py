from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


_FORBIDDEN_TRUE_FLAGS = {
    "live_provider_used": "used_live_provider",
    "live_websearch_used": "used_live_websearch",
    "source_live_websearch_used": "used_source_live_websearch",
    "live_extract_used": "used_live_extract",
    "runtime_truth_changed": "changed_runtime_truth",
    "mutation_changed": "changed_mutation",
    "runtime_mutation_allowed": "allowed_runtime_mutation",
    "websearch_runtime_truth_allowed": "allowed_websearch_runtime_truth",
    "runtime_web_activation_approved": "approved_runtime_web_activation",
    "runtime_web_activation_recommended": "recommended_runtime_web_activation",
    "ready_for_runtime_truth": "claimed_ready_for_runtime_truth",
    "ready_for_runtime_mutation": "claimed_ready_for_runtime_mutation",
    "readiness_claimed": "claimed_readiness",
    "manager_context_changed": "changed_manager_context",
    "manager_context_packet_changed": "changed_manager_context_packet",
    "manager_context_packet_schema_changed": "changed_manager_context_packet_schema",
    "packetizer_format_changed": "changed_packetizer_format",
    "packetizer_changed": "changed_packetizer",
    "shared_contract_changed": "changed_shared_contract",
    "nutrition_evidence_store_port_changed": "changed_nutrition_evidence_store_port",
    "basket_semantics_changed": "changed_basket_semantics",
    "product_loop_activated": "activated_product_loop",
    "product_loop_integration_claimed": "claimed_product_loop_integration",
    "ce_activated": "activated_context_engineering",
    "context_engineering_changed": "changed_context_engineering",
    "webshell_activated": "activated_webshell",
    "webshell_changed": "changed_webshell",
}


def build_websearch_live_extract_diagnostic_gate(
    *,
    integration_matrix_artifact: dict[str, Any],
    live_extract_preflight_artifact: dict[str, Any],
) -> dict[str, Any]:
    matrix_gate = _matrix_gate(integration_matrix_artifact)
    preflight_gate = _preflight_gate(live_extract_preflight_artifact)
    blockers = [
        *[f"integration_matrix:{blocker}" for blocker in matrix_gate["blockers"]],
        *[f"live_extract_preflight:{blocker}" for blocker in preflight_gate["blockers"]],
    ]
    clear = not blockers
    review_packet_refs = (
        list(live_extract_preflight_artifact.get("review_packet_refs") or [])
        if clear
        else []
    )
    return {
        "artifact_type": "accurate_intake_websearch_live_extract_diagnostic_gate_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_live_extract_diagnostic_gate_only",
        "claim_scope": "websearch_live_extract_diagnostic_gate_without_live_call",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
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
        "live_extract_used": False,
        "readiness_claimed": False,
        "ready_for_runtime_truth": False,
        "ready_for_runtime_mutation": False,
        "ready_for_trace_only_live_extract_diagnostic": clear,
        "source_artifacts": {
            "integration_matrix_artifact_type": integration_matrix_artifact.get("artifact_type"),
            "live_extract_preflight_artifact_type": live_extract_preflight_artifact.get("artifact_type"),
        },
        "matrix_gate": matrix_gate,
        "preflight_gate": preflight_gate,
        "diagnostic_contract": {
            "live_call_allowed_by_this_artifact": False,
            "requires_explicit_allow_live_flag": True,
            "extract_result_role": "review_candidate_only",
            "max_extract_urls_per_case": 1,
            "raw_content_allowed_in_manager_context": False,
            "extract_snippet_truth_allowed": False,
            "exact_card_creation_allowed": False,
            "ledger_mutation_allowed": False,
            "runtime_activation_allowed": False,
        },
        "review_packet_refs": [
            {
                "packet_id": packet.get("packet_id"),
                "source_url": packet.get("source_url"),
                "canonical_name": packet.get("canonical_name"),
                "packet_digest": packet.get("packet_digest"),
            }
            for packet in review_packet_refs
            if isinstance(packet, dict)
        ],
        "summary": {
            "review_packet_ref_count": len(review_packet_refs),
            "ready_for_trace_only_live_extract_diagnostic_count": (
                len(review_packet_refs) if clear else 0
            ),
            "runtime_truth_allowed_count": 0,
            "runtime_activation_ready_count": 0,
        },
        "next_required_slice": (
            "websearch_live_extract_diagnostic_canary_harness"
            if clear
            else _blocked_next_slice(matrix_gate=matrix_gate, preflight_gate=preflight_gate)
        ),
        "non_claims": [
            "no_live_extract_call",
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_runtime_web_activation",
            "no_readiness_claim",
        ],
    }


def _matrix_gate(artifact: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if (
        artifact.get("artifact_type")
        != "accurate_intake_websearch_integration_readiness_matrix_v1"
    ):
        blockers.append("unsupported_artifact_type")
    if artifact.get("status") != "clear":
        blockers.append(f"status_not_clear:{artifact.get('status')}")
    blockers.extend(_unsafe_artifact_blockers(artifact))
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    if int(summary.get("blocked_edge_count") or 0) != 0:
        blockers.append("blocked_edges_present")
    if int(summary.get("runtime_activation_ready_count") or 0) != 0:
        blockers.append("runtime_activation_ready_count_nonzero")
    if artifact.get("next_required_slice") != "websearch_exact_candidate_or_live_extract_trace_diagnostic":
        blockers.append("next_slice_not_exact_or_live_extract_trace_diagnostic")
    return {
        "status": "clear" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "next_required_slice": (
            "websearch_live_extract_diagnostic_gate"
            if not blockers
            else "inspect_websearch_integration_readiness_matrix"
        ),
    }


def _preflight_gate(artifact: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "accurate_intake_websearch_live_extract_preflight_v1":
        blockers.append("unsupported_artifact_type")
    if artifact.get("status") != "pass":
        blockers.append(f"status_not_pass:{artifact.get('status')}")
    if artifact.get("ready_for_live_extract_diagnostic") is not True:
        blockers.append("not_ready_for_live_extract_diagnostic")
    if artifact.get("ready_for_runtime_truth") is not False:
        blockers.append("claimed_ready_for_runtime_truth")
    if artifact.get("blockers"):
        blockers.append("artifact_has_blockers")
    blockers.extend(_unsafe_artifact_blockers(artifact))
    contract = artifact.get("diagnostic_contract") if isinstance(artifact.get("diagnostic_contract"), dict) else {}
    if contract.get("live_call_allowed_by_this_artifact") is not False:
        blockers.append("contract_allowed_live_call")
    if contract.get("requires_explicit_allow_live_flag") is not True:
        blockers.append("contract_missing_explicit_allow_live_flag")
    if contract.get("raw_content_allowed_in_manager_context") is not False:
        blockers.append("contract_allowed_raw_content_in_manager_context")
    if contract.get("extract_snippet_truth_allowed") is True:
        blockers.append("contract_allowed_extract_snippet_truth")
    if contract.get("ledger_mutation_allowed") is not False:
        blockers.append("contract_allowed_ledger_mutation")
    if contract.get("exact_card_creation_allowed") is not False:
        blockers.append("contract_allowed_exact_card_creation")
    if contract.get("runtime_activation_allowed") is True:
        blockers.append("contract_allowed_runtime_activation")
    review_packet_refs = [
        packet
        for packet in artifact.get("review_packet_refs") or []
        if isinstance(packet, dict)
    ]
    if not review_packet_refs:
        blockers.append("review_packet_refs_missing")
    blockers.extend(_review_packet_ref_blockers(review_packet_refs))
    return {
        "status": "clear" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "next_required_slice": (
            "websearch_live_extract_diagnostic_canary_harness"
            if not blockers
            else "inspect_websearch_live_extract_preflight"
        ),
    }


def _unsafe_artifact_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers = [
        blocker
        for key, blocker in _FORBIDDEN_TRUE_FLAGS.items()
        if artifact.get(key) is True
    ]
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    if int(summary.get("runtime_truth_allowed_count") or 0) != 0:
        blockers.append("summary_runtime_truth_allowed")
    if int(summary.get("ready_for_runtime_truth_count") or 0) != 0:
        blockers.append("summary_ready_for_runtime_truth")
    return blockers


def _review_packet_ref_blockers(packets: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for packet in packets:
        if not str(packet.get("packet_id") or "").strip():
            blockers.append("review_packet_ref_missing_packet_id")
        if not str(packet.get("source_url") or "").strip():
            blockers.append("review_packet_ref_missing_source_url")
        if not str(packet.get("packet_digest") or "").strip():
            blockers.append("review_packet_ref_missing_packet_digest")
    return blockers


def _blocked_next_slice(*, matrix_gate: dict[str, Any], preflight_gate: dict[str, Any]) -> str:
    if matrix_gate["blockers"]:
        return "inspect_websearch_integration_readiness_matrix"
    if preflight_gate["blockers"]:
        return "inspect_websearch_live_extract_preflight"
    return "inspect_websearch_live_extract_diagnostic_gate"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_live_extract_diagnostic_gate"]
