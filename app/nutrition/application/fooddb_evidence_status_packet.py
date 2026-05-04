from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .exact_evidence_lane_policy import build_exact_evidence_lane_policy_artifact
from .fooddb_activation_gap_report import build_fooddb_activation_gap_report
from .fooddb_guarded_afk_truth_audit import build_fooddb_guarded_afk_truth_audit
from .fooddb_integration_readiness_matrix import build_fooddb_integration_readiness_matrix
from .websearch_source_policy import build_websearch_source_policy_artifact

MINIMUM_COMMON_SERVING_ANCHORS = 40
MINIMUM_LISTED_COMPONENT_ANCHORS = 30


def build_fooddb_evidence_status_packet(
    *,
    small_anchor_payload: dict[str, Any],
    tfda_source_payload: dict[str, Any],
    exact_card_payload: dict[str, Any],
) -> dict[str, Any]:
    truth_audit = build_fooddb_guarded_afk_truth_audit(
        small_anchor_payload=small_anchor_payload,
        tfda_source_payload=tfda_source_payload,
        exact_card_payload=exact_card_payload,
    )
    gap_report = build_fooddb_activation_gap_report(
        small_anchor_payload=small_anchor_payload,
        tfda_source_payload=tfda_source_payload,
        exact_card_payload=exact_card_payload,
    )
    exact_lane = build_exact_evidence_lane_policy_artifact()
    integration = build_fooddb_integration_readiness_matrix()
    websearch_policy = build_websearch_source_policy_artifact()

    truth_summary = truth_audit["summary"]
    gap_summary = gap_report["summary"]
    exact_staging_count = exact_lane["summary"]["exact_card_staging_candidate_count"]
    integration_summary = integration["summary"]
    listed_count = gap_summary["listed_component_anchor_count"]
    runtime_anchor_count = truth_summary["runtime_common_serving_anchor_count"]

    return {
        "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "fooddb_websearch_evidence_status_for_future_seams",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "runtime_common_serving_anchor_count": runtime_anchor_count,
            "listed_component_anchor_count": listed_count,
            "source_evidence_only_count": truth_summary["tfda_source_evidence_only_count"],
            "semantic_only_basket_family_count": gap_summary["semantic_only_basket_family_count"],
            "exact_card_staging_candidate_count": exact_staging_count,
            "exact_card_existing_report_only_count": truth_summary["exact_card_count"],
            "integration_edges_contract_backed": integration_summary["contract_backed"],
            "integration_edges_draft": integration_summary["draft"],
        },
        "activation_thresholds": {
            "minimum_common_serving_anchors": MINIMUM_COMMON_SERVING_ANCHORS,
            "minimum_listed_component_anchors": MINIMUM_LISTED_COMPONENT_ANCHORS,
            "meets_common_serving_anchor_minimum": runtime_anchor_count
            >= MINIMUM_COMMON_SERVING_ANCHORS,
            "meets_listed_component_minimum": listed_count >= MINIMUM_LISTED_COMPONENT_ANCHORS,
        },
        "fooddb_status": {
            "truth_audit_stop_gate_status": truth_audit["stop_gate_status"],
            "runtime_anchor_catalog_included": False,
            "runtime_anchor_catalog_reason": "status_packet_counts_only_not_manager_evidence_payload",
            "known_basket_limitations": gap_report["activation_gap_report"]["known_basket_limitations"],
            "known_modifier_limitations": gap_report["activation_gap_report"][
                "known_modifier_limitations"
            ],
        },
        "websearch_status": {
            "websearch_runtime_truth_allowed": False,
            "source_policy": {
                "max_search_attempts": websearch_policy["max_search_attempts"],
                "default_search_depth": websearch_policy["search_depth_policy"]["default"],
                "max_results": websearch_policy["rate_policy"]["max_results"],
                "extract_allowed_license_statuses": list(
                    websearch_policy["license_policy"]["extract_allowed_license_statuses"]
                ),
            },
            "exact_card_staging": {
                "candidate_count": exact_staging_count,
                "runtime_truth_allowed": False,
                "packet_ready_truth_allowed": False,
                "exact_card_created": False,
            },
        },
        "integration_status": {
            "matrix_artifact_type": integration["artifact_type"],
            "contract_backed_edge_count": integration_summary["contract_backed"],
            "draft_edge_count": integration_summary["draft"],
            "websearch_runtime_truth_allowed": integration["websearch_runtime_truth_allowed"],
        },
        "next_required_slices": _next_required_slices(
            runtime_anchor_count=runtime_anchor_count,
            listed_component_count=listed_count,
            integration_summary=integration_summary,
        ),
        "non_claims": [
            "no_product_loop_integration",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_runtime_truth_promotion",
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_readiness_claim",
        ],
    }


def _next_required_slices(
    *,
    runtime_anchor_count: int,
    listed_component_count: int,
    integration_summary: dict[str, Any],
) -> list[str]:
    slices: list[str] = []
    if runtime_anchor_count < MINIMUM_COMMON_SERVING_ANCHORS:
        slices.append("common_serving_anchor_expansion")
    if listed_component_count < MINIMUM_LISTED_COMPONENT_ANCHORS:
        slices.append("listed_component_anchor_expansion")
    if integration_summary["draft"]:
        slices.append("packet_to_mutation_guard_hardening")
    if not slices:
        slices.append("manager_fooddb_packet_seam_smoke")
    return slices


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_fooddb_evidence_status_packet"]
