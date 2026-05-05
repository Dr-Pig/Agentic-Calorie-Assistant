from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


_EXPECTED_NEXT_SLICE = "websearch_exact_card_candidate_planning_after_live_extract"

_FORBIDDEN_TRUE_FLAGS = {
    "runtime_truth_changed": "post_extract_status_changed_runtime_truth",
    "mutation_changed": "post_extract_status_changed_mutation",
    "runtime_mutation_allowed": "post_extract_status_allowed_runtime_mutation",
    "websearch_runtime_truth_allowed": "post_extract_status_allowed_websearch_runtime_truth",
    "runtime_web_activation_approved": (
        "post_extract_status_approved_runtime_web_activation"
    ),
    "runtime_web_activation_recommended": (
        "post_extract_status_recommended_runtime_web_activation"
    ),
    "ready_for_runtime_truth": "post_extract_status_claimed_ready_for_runtime_truth",
    "ready_for_runtime_mutation": "post_extract_status_claimed_ready_for_runtime_mutation",
    "readiness_claimed": "post_extract_status_claimed_readiness",
    "shared_contract_changed": "post_extract_status_changed_shared_contract",
    "manager_context_changed": "post_extract_status_changed_manager_context",
    "manager_context_packet_changed": "post_extract_status_changed_manager_context_packet",
    "manager_context_packet_schema_changed": (
        "post_extract_status_changed_manager_context_packet_schema"
    ),
    "packetizer_format_changed": "post_extract_status_changed_packetizer_format",
    "packetizer_changed": "post_extract_status_changed_packetizer",
    "basket_semantics_changed": "post_extract_status_changed_basket_semantics",
    "nutrition_evidence_store_port_changed": (
        "post_extract_status_changed_nutrition_evidence_store_port"
    ),
    "live_provider_used": "post_extract_status_used_live_provider",
    "live_websearch_used": "post_extract_status_used_live_websearch",
    "source_live_websearch_used": "post_extract_status_used_source_live_websearch",
    "exact_card_created": "post_extract_status_created_exact_card",
    "product_loop_activated": "post_extract_status_activated_product_loop",
    "product_loop_integration_claimed": "post_extract_status_claimed_product_loop_integration",
    "ce_activated": "post_extract_status_activated_context_engineering",
    "context_engineering_changed": "post_extract_status_changed_context_engineering",
    "webshell_activated": "post_extract_status_activated_webshell",
    "webshell_changed": "post_extract_status_changed_webshell",
}


def build_websearch_exact_card_candidate_plan(
    *,
    post_extract_status_packet: dict[str, Any],
) -> dict[str, Any]:
    blockers = _status_packet_blockers(post_extract_status_packet)
    candidates = [] if blockers else [_planned_candidate(post_extract_status_packet)]
    blockers.extend(_candidate_blockers(candidates))
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_websearch_exact_card_candidate_plan_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_exact_card_candidate_plan_only",
        "claim_scope": "websearch_exact_card_candidate_plan_without_truth_promotion",
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
        "readiness_claimed": False,
        "exact_card_created": False,
        "source_artifacts": {
            "post_extract_status_packet_type": post_extract_status_packet.get(
                "artifact_type"
            ),
        },
        "planned_candidates": candidates,
        "summary": {
            "planned_candidate_count": len(candidates),
            "runtime_truth_allowed_count": sum(
                1 for candidate in candidates if candidate["runtime_truth_allowed"] is True
            ),
            "exact_card_created_count": sum(
                1 for candidate in candidates if candidate["exact_card_created"] is True
            ),
            "promotion_allowed_count": sum(
                1 for candidate in candidates if candidate["promotion_allowed"] is True
            ),
        },
        "approval_boundary": {
            "planning_artifact_can_create_exact_card": False,
            "planning_artifact_can_create_runtime_truth": False,
            "planning_artifact_can_mutate_ledger": False,
            "required_approval_mode_before_runtime_truth": "explicit_exact_card_approval",
        },
        "next_required_slice": (
            "websearch_exact_card_review_packet_refresh"
            if clear
            else "inspect_websearch_exact_card_candidate_plan_blockers"
        ),
        "non_claims": [
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_runtime_web_activation",
            "no_readiness_claim",
        ],
    }


def _status_packet_blockers(packet: dict[str, Any]) -> list[str]:
    if (
        str(packet.get("artifact_type") or "")
        != "accurate_intake_websearch_post_extract_lane_status_packet_v1"
    ):
        raise ValueError("unsupported_exact_card_candidate_plan_status_packet")
    blockers: list[str] = []
    if packet.get("status") != "clear_for_exact_card_candidate_planning":
        blockers.append(f"post_extract_status_not_clear:{packet.get('status')}")
    blockers.extend(
        blocker for key, blocker in _FORBIDDEN_TRUE_FLAGS.items() if packet.get(key) is True
    )
    upstream_gate = (
        packet.get("upstream_gate") if isinstance(packet.get("upstream_gate"), dict) else {}
    )
    if upstream_gate.get("blocked") is True:
        blockers.append("post_extract_upstream_gate_blocked")
    blockers.extend(
        f"post_extract_upstream_gate:{blocker}"
        for blocker in upstream_gate.get("blockers") or []
    )
    if str(upstream_gate.get("next_required_slice") or "").strip() != _EXPECTED_NEXT_SLICE:
        blockers.append("post_extract_upstream_gate_next_slice_drift")
    next_required_slices = list(packet.get("next_required_slices") or [])
    if next_required_slices != [_EXPECTED_NEXT_SLICE]:
        blockers.append("post_extract_next_slice_not_exact_card_candidate_planning")
    summary = packet.get("summary") if isinstance(packet.get("summary"), dict) else {}
    if int(summary.get("runtime_activation_ready_count") or 0) != 0:
        blockers.append("post_extract_runtime_activation_ready_count_nonzero")
    if int(summary.get("runtime_truth_allowed_count") or 0) != 0:
        blockers.append("post_extract_runtime_truth_allowed_count_nonzero")
    return blockers


def _planned_candidate(packet: dict[str, Any]) -> dict[str, Any]:
    summary = packet.get("summary") if isinstance(packet.get("summary"), dict) else {}
    return {
        "candidate_id": "exact_card_candidate_plan:websearch_live_extract_trace_clean",
        "candidate_role": "exact_card_candidate_plan",
        "promotion_status": "review_candidate_only",
        "source_type": "websearch_live_extract_trace",
        "source_post_extract_status": packet.get("status"),
        "source_extract_report_status": summary.get("extract_report_status"),
        "source_extract_report_selected_option": summary.get(
            "extract_report_selected_option"
        ),
        "evidence_basis": {
            "extract_report_case_count": int(summary.get("extract_report_case_count") or 0),
            "extract_report_failure_count": int(
                summary.get("extract_report_failure_count") or 0
            ),
            "extract_port_used": summary.get("extract_port_used") is True,
            "live_extract_used": summary.get("live_extract_used") is True,
        },
        "planning_scope": {
            "allowed_next_artifact": "exact_card_review_packet_refresh",
            "allowed_record_type": "review_candidate_only",
            "runtime_exact_card_creation_allowed": False,
        },
        "approval_metadata": {
            "approval_mode": "none",
            "approval_scope": "exact_card_candidate_plan_only",
            "policy_version": "websearch_exact_card_candidate_plan_v1",
            "runtime_truth_allowed": False,
        },
        "runtime_truth_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "promotion_allowed": False,
        "exact_card_created": False,
        "runtime_mutation_allowed": False,
        "manager_visible_role": "review_plan_only_not_manager_truth",
        "required_before_runtime_truth": [
            "exact_identity_variant_match",
            "serving_basis_confirmation",
            "kcal_value_confirmation",
            "source_license_confirmation",
            "explicit_exact_card_approval",
            "exact_card_runtime_gate",
        ],
    }


def _candidate_blockers(candidates: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for candidate in candidates:
        if candidate.get("runtime_truth_allowed") is True:
            blockers.append("planned_candidate_allowed_runtime_truth")
        if candidate.get("websearch_runtime_truth_allowed") is True:
            blockers.append("planned_candidate_allowed_websearch_runtime_truth")
        if candidate.get("packet_ready_truth_allowed") is True:
            blockers.append("planned_candidate_allowed_packet_ready_truth")
        if candidate.get("promotion_allowed") is True:
            blockers.append("planned_candidate_allowed_promotion")
        if candidate.get("exact_card_created") is True:
            blockers.append("planned_candidate_created_exact_card")
        if candidate.get("runtime_mutation_allowed") is True:
            blockers.append("planned_candidate_allowed_runtime_mutation")
    return blockers


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_exact_card_candidate_plan"]
