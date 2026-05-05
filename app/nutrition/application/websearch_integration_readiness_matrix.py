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


def build_websearch_integration_readiness_matrix(
    *,
    fooddb_status_packet: dict[str, Any] | None = None,
    websearch_status_packet: dict[str, Any] | None = None,
    source_adapter_preflight: dict[str, Any] | None = None,
    live_search_canary_report: dict[str, Any] | None = None,
    exact_lane_status_packet: dict[str, Any] | None = None,
    live_extract_preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    edge_inputs = {
        "manager_decision_to_retrieval_intent": fooddb_status_packet,
        "retrieval_router_to_fooddb_local_adapter": fooddb_status_packet,
        "retrieval_router_to_sqlite_fts_adapter": fooddb_status_packet,
        "retrieval_router_to_websearch_candidate": websearch_status_packet,
        "websearch_candidate_to_source_adapter": source_adapter_preflight,
        "source_adapter_to_live_search_canary": live_search_canary_report,
        "websearch_candidate_to_selected_extract_request": exact_lane_status_packet,
        "exact_card_review_packet_to_live_extract_preflight": live_extract_preflight,
        "retriever_output_to_compact_packet": websearch_status_packet,
        "packet_to_manager_seam": websearch_status_packet,
        "packet_to_mutation_guard": websearch_status_packet,
        "exact_candidate_to_no_mutation": exact_lane_status_packet,
        "basket_listed_components_to_approved_anchors_only": fooddb_status_packet,
    }
    edge_specs = _edge_specs()
    edges = [
        _edge_result(
            edge_id=edge_id,
            artifact=edge_inputs[edge_id],
            spec=edge_specs[edge_id],
        )
        for edge_id in edge_specs
    ]
    blocked_edges = [edge for edge in edges if edge["status"] != "clear"]
    status = "clear" if not blocked_edges else "blocked"
    return {
        "artifact_type": "accurate_intake_websearch_integration_readiness_matrix_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_integration_readiness_matrix_only",
        "claim_scope": "fooddb_websearch_evidence_integration_readiness_without_runtime_activation",
        "status": status,
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
        "ready_for_runtime_truth": False,
        "ready_for_runtime_mutation": False,
        "edges": edges,
        "summary": {
            "edge_count": len(edges),
            "clear_edge_count": sum(1 for edge in edges if edge["status"] == "clear"),
            "blocked_edge_count": len(blocked_edges),
            "missing_artifact_edge_count": sum(
                1 for edge in edges if "artifact_missing" in edge["blockers"]
            ),
            "runtime_activation_ready_count": 0,
        },
        "next_required_slice": (
            "websearch_exact_candidate_or_live_extract_trace_diagnostic"
            if status == "clear"
            else _first_next_required_slice(blocked_edges)
        ),
        "non_claims": [
            "no_runtime_web_activation",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_product_loop_integration",
            "no_context_engineering_change",
            "no_webshell_change",
            "no_readiness_claim",
        ],
    }


def _edge_specs() -> dict[str, dict[str, Any]]:
    return {
        "manager_decision_to_retrieval_intent": {
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "clear_statuses": {"pass", "clear", "ready"},
            "fallback_next": "inspect_fooddb_status_packet",
            "required_note": "retrieval intent must come from Manager decision, not raw text workflow routing",
        },
        "retrieval_router_to_fooddb_local_adapter": {
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "clear_statuses": {"pass", "clear", "ready"},
            "fallback_next": "inspect_fooddb_status_packet",
            "required_note": "FoodDB local adapter stays behind retriever/router boundary",
        },
        "retrieval_router_to_sqlite_fts_adapter": {
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "clear_statuses": {"pass", "clear", "ready"},
            "fallback_next": "inspect_fooddb_status_packet",
            "required_note": "SQLite FTS remains adapter-backed and not Manager-owned",
        },
        "retrieval_router_to_websearch_candidate": {
            "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
            "clear_statuses": {"pass", "clear"},
            "fallback_next": "inspect_websearch_status_packet",
            "required_next": "websearch_live_search_preflight_or_candidate_source_adapter",
        },
        "websearch_candidate_to_source_adapter": {
            "artifact_type": "accurate_intake_websearch_source_adapter_preflight_v1",
            "clear_statuses": {"pass"},
            "fallback_next": "inspect_websearch_source_adapter_preflight_blockers",
            "required_ready_key": "ready_for_live_search_diagnostic",
        },
        "source_adapter_to_live_search_canary": {
            "artifact_type": "accurate_intake_websearch_live_search_canary_report_v1",
            "clear_statuses": {"trace_only_canary_clean"},
            "fallback_next": "inspect_websearch_live_search_canary_blockers",
            "required_selected_option": "trace_only_canary_continues",
        },
        "websearch_candidate_to_selected_extract_request": {
            "artifact_type": "accurate_intake_exact_evidence_lane_status_packet_v1",
            "clear_statuses": {"pass", "clear"},
            "fallback_next": "inspect_exact_evidence_lane_status_packet",
            "required_next": "grokfast_websearch_packet_live_diagnostic",
        },
        "exact_card_review_packet_to_live_extract_preflight": {
            "artifact_type": "accurate_intake_websearch_live_extract_preflight_v1",
            "clear_statuses": {"pass"},
            "fallback_next": "inspect_websearch_live_extract_preflight_blockers",
            "required_ready_key": "ready_for_live_extract_diagnostic",
        },
        "retriever_output_to_compact_packet": {
            "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
            "clear_statuses": {"pass", "clear"},
            "fallback_next": "inspect_websearch_status_packet",
        },
        "packet_to_manager_seam": {
            "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
            "clear_statuses": {"pass", "clear"},
            "fallback_next": "inspect_websearch_status_packet",
        },
        "packet_to_mutation_guard": {
            "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
            "clear_statuses": {"pass", "clear"},
            "fallback_next": "inspect_websearch_status_packet",
        },
        "exact_candidate_to_no_mutation": {
            "artifact_type": "accurate_intake_exact_evidence_lane_status_packet_v1",
            "clear_statuses": {"pass", "clear"},
            "fallback_next": "inspect_exact_evidence_lane_status_packet",
        },
        "basket_listed_components_to_approved_anchors_only": {
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "clear_statuses": {"pass", "clear", "ready"},
            "fallback_next": "inspect_fooddb_status_packet",
            "required_note": "listed basket estimates must remain limited to approved runtime anchors",
        },
    }


def _edge_result(
    *,
    edge_id: str,
    artifact: dict[str, Any] | None,
    spec: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(artifact, dict):
        blockers.append("artifact_missing")
        return _edge_payload(edge_id=edge_id, status="missing", blockers=blockers, spec=spec)
    if artifact.get("artifact_type") != spec["artifact_type"]:
        blockers.append("artifact_type_mismatch")
    blockers.extend(_unsafe_artifact_blockers(artifact))
    status = str(artifact.get("status") or "").strip()
    if status and status not in spec["clear_statuses"]:
        blockers.append(f"status_not_clear:{status}")
    if not status:
        next_required = _next_required_from_artifact(artifact)
        if next_required and next_required != spec.get("required_next"):
            blockers.append(f"next_slice_not_clear:{next_required}")
    required_next = spec.get("required_next")
    if required_next and required_next not in _next_required_candidates(artifact):
        blockers.append(f"required_next_slice_missing:{required_next}")
    required_ready_key = spec.get("required_ready_key")
    if required_ready_key and artifact.get(required_ready_key) is not True:
        blockers.append(f"required_ready_key_false:{required_ready_key}")
    required_selected_option = spec.get("required_selected_option")
    if required_selected_option and artifact.get("selected_option") != required_selected_option:
        blockers.append(f"selected_option_mismatch:{artifact.get('selected_option')}")
    if artifact.get("blockers"):
        blockers.append("artifact_has_blockers")
    edge_status = "clear" if not blockers else "blocked"
    return _edge_payload(
        edge_id=edge_id,
        status=edge_status,
        blockers=sorted(set(blockers)),
        spec=spec,
    )


def _unsafe_artifact_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers = [
        blocker
        for key, blocker in _FORBIDDEN_TRUE_FLAGS.items()
        if artifact.get(key) is True
    ]
    decision_boundary = (
        artifact.get("decision_boundary")
        if isinstance(artifact.get("decision_boundary"), dict)
        else {}
    )
    for key, blocker in (
        (
            "trace_canary_is_runtime_activation_evidence",
            "decision_boundary_runtime_activation_evidence",
        ),
        ("accepted_extract_packet_is_exact_truth", "decision_boundary_exact_truth"),
        ("mutation_allowed", "decision_boundary_mutation_allowed"),
        ("product_readiness_claim_allowed", "decision_boundary_readiness_allowed"),
    ):
        if decision_boundary.get(key) is True:
            blockers.append(blocker)
    diagnostic_contract = (
        artifact.get("diagnostic_contract")
        if isinstance(artifact.get("diagnostic_contract"), dict)
        else {}
    )
    for key, blocker in (
        ("live_call_allowed_by_this_artifact", "diagnostic_contract_allowed_live_call"),
        (
            "raw_content_allowed_in_manager_context",
            "diagnostic_contract_allowed_raw_content_in_manager_context",
        ),
        ("ledger_mutation_allowed", "diagnostic_contract_allowed_ledger_mutation"),
        ("exact_card_creation_allowed", "diagnostic_contract_allowed_exact_card_creation"),
    ):
        if diagnostic_contract.get(key) is True:
            blockers.append(blocker)
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    if int(summary.get("runtime_truth_allowed_count") or 0) != 0:
        blockers.append("summary_runtime_truth_allowed")
    if int(summary.get("ready_for_runtime_truth_count") or 0) != 0:
        blockers.append("summary_ready_for_runtime_truth")
    if int(summary.get("runtime_activation_ready_count") or 0) != 0:
        blockers.append("summary_runtime_activation_ready")
    return blockers


def _edge_payload(
    *,
    edge_id: str,
    status: str,
    blockers: list[str],
    spec: dict[str, Any],
) -> dict[str, Any]:
    return {
        "edge_id": edge_id,
        "status": status,
        "blockers": blockers,
        "source_artifact_type": spec["artifact_type"],
        "next_required_slice_if_blocked": spec["fallback_next"],
        "runtime_truth_allowed": False,
        "runtime_mutation_allowed": False,
        "shared_contract_changed": False,
        "note": spec.get("required_note"),
    }


def _next_required_candidates(artifact: dict[str, Any]) -> set[str]:
    candidates: set[str] = set()
    next_required_slice = artifact.get("next_required_slice")
    if isinstance(next_required_slice, str) and next_required_slice.strip():
        candidates.add(next_required_slice.strip())
    next_required_slices = artifact.get("next_required_slices")
    if isinstance(next_required_slices, list):
        candidates.update(str(item).strip() for item in next_required_slices if str(item).strip())
    return candidates


def _next_required_from_artifact(artifact: dict[str, Any]) -> str | None:
    candidates = _next_required_candidates(artifact)
    return sorted(candidates)[0] if candidates else None


def _first_next_required_slice(blocked_edges: list[dict[str, Any]]) -> str:
    if not blocked_edges:
        return "websearch_exact_candidate_or_live_extract_trace_diagnostic"
    return str(blocked_edges[0]["next_required_slice_if_blocked"])


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_integration_readiness_matrix"]
