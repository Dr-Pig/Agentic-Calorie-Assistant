from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from typing import Any


_EXPECTED_NEXT_SLICE = "websearch_exact_card_review_packet_refresh"

_FORBIDDEN_TRUE_FLAGS = {
    "runtime_truth_changed": "candidate_plan_changed_runtime_truth",
    "mutation_changed": "candidate_plan_changed_mutation",
    "runtime_mutation_allowed": "candidate_plan_allowed_runtime_mutation",
    "websearch_runtime_truth_allowed": "candidate_plan_allowed_websearch_runtime_truth",
    "runtime_web_activation_approved": "candidate_plan_approved_runtime_web_activation",
    "runtime_web_activation_recommended": (
        "candidate_plan_recommended_runtime_web_activation"
    ),
    "packet_ready_truth_allowed": "candidate_plan_allowed_packet_ready_truth",
    "promotion_allowed": "candidate_plan_allowed_promotion",
    "approval_allowed_by_this_packet": "candidate_plan_allowed_approval",
    "ready_for_runtime_truth": "candidate_plan_claimed_ready_for_runtime_truth",
    "ready_for_runtime_mutation": "candidate_plan_claimed_ready_for_runtime_mutation",
    "readiness_claimed": "candidate_plan_claimed_readiness",
    "shared_contract_changed": "candidate_plan_changed_shared_contract",
    "manager_context_changed": "candidate_plan_changed_manager_context",
    "manager_context_packet_changed": "candidate_plan_changed_manager_context_packet",
    "manager_context_packet_schema_changed": (
        "candidate_plan_changed_manager_context_packet_schema"
    ),
    "packetizer_format_changed": "candidate_plan_changed_packetizer_format",
    "packetizer_changed": "candidate_plan_changed_packetizer",
    "basket_semantics_changed": "candidate_plan_changed_basket_semantics",
    "nutrition_evidence_store_port_changed": (
        "candidate_plan_changed_nutrition_evidence_store_port"
    ),
    "live_provider_used": "candidate_plan_used_live_provider",
    "live_websearch_used": "candidate_plan_used_live_websearch",
    "source_live_websearch_used": "candidate_plan_used_source_live_websearch",
    "exact_card_created": "candidate_plan_created_exact_card",
    "product_loop_activated": "candidate_plan_activated_product_loop",
    "product_loop_integration_claimed": "candidate_plan_claimed_product_loop_integration",
    "ce_activated": "candidate_plan_activated_context_engineering",
    "context_engineering_changed": "candidate_plan_changed_context_engineering",
    "webshell_activated": "candidate_plan_activated_webshell",
    "webshell_changed": "candidate_plan_changed_webshell",
}


def build_websearch_exact_card_review_packet_refresh(
    *,
    exact_card_candidate_plan: dict[str, Any],
) -> dict[str, Any]:
    blockers = _candidate_plan_blockers(exact_card_candidate_plan)
    candidates = [] if blockers else _planned_candidates(exact_card_candidate_plan)
    blockers.extend(_planned_candidate_blockers(candidates))
    review_packets = [] if blockers else [_review_packet(candidate) for candidate in candidates]
    blockers.extend(_review_packet_blockers(review_packets))
    if not review_packets and not blockers:
        blockers.append("review_packet_refresh_candidate_missing")
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_websearch_exact_card_review_packet_refresh_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_exact_card_review_packet_refresh_only",
        "claim_scope": "websearch_exact_card_review_packet_refresh_without_truth_promotion",
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
            "exact_card_candidate_plan_type": exact_card_candidate_plan.get("artifact_type"),
        },
        "review_packets": review_packets,
        "summary": {
            "review_packet_count": len(review_packets),
            "runtime_truth_allowed_count": sum(
                1 for packet in review_packets if packet["runtime_truth_allowed"] is True
            ),
            "exact_card_created_count": sum(
                1 for packet in review_packets if packet["exact_card_created"] is True
            ),
            "approval_allowed_count": sum(
                1 for packet in review_packets if packet["approval_allowed_by_this_packet"] is True
            ),
        },
        "next_required_slice": (
            "websearch_exact_card_candidate_approval_wall"
            if clear
            else "inspect_websearch_exact_card_review_packet_refresh_blockers"
        ),
        "non_claims": [
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_runtime_web_activation",
            "no_readiness_claim",
        ],
    }


def _candidate_plan_blockers(plan: dict[str, Any]) -> list[str]:
    if (
        str(plan.get("artifact_type") or "")
        != "accurate_intake_websearch_exact_card_candidate_plan_v1"
    ):
        raise ValueError("unsupported_exact_card_review_refresh_candidate_plan")
    blockers: list[str] = []
    if plan.get("status") != "pass":
        blockers.append(f"candidate_plan_not_pass:{plan.get('status')}")
    blockers.extend(
        blocker for key, blocker in _FORBIDDEN_TRUE_FLAGS.items() if plan.get(key) is True
    )
    if plan.get("next_required_slice") != _EXPECTED_NEXT_SLICE:
        blockers.append("candidate_plan_next_slice_not_review_packet_refresh")
    summary = plan.get("summary") if isinstance(plan.get("summary"), dict) else {}
    if int(summary.get("runtime_truth_allowed_count") or 0) != 0:
        blockers.append("candidate_plan_runtime_truth_allowed_count_nonzero")
    if int(summary.get("exact_card_created_count") or 0) != 0:
        blockers.append("candidate_plan_exact_card_created_count_nonzero")
    if int(summary.get("promotion_allowed_count") or 0) != 0:
        blockers.append("candidate_plan_promotion_allowed_count_nonzero")
    boundary = (
        plan.get("approval_boundary")
        if isinstance(plan.get("approval_boundary"), dict)
        else {}
    )
    if boundary.get("planning_artifact_can_create_exact_card") is not False:
        blockers.append("candidate_plan_boundary_allowed_exact_card_creation")
    if boundary.get("planning_artifact_can_create_runtime_truth") is not False:
        blockers.append("candidate_plan_boundary_allowed_runtime_truth")
    if boundary.get("planning_artifact_can_mutate_ledger") is not False:
        blockers.append("candidate_plan_boundary_allowed_ledger_mutation")
    if (
        boundary.get("required_approval_mode_before_runtime_truth")
        != "explicit_exact_card_approval"
    ):
        blockers.append("candidate_plan_boundary_missing_exact_card_approval")
    return blockers


def _planned_candidates(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        candidate
        for candidate in plan.get("planned_candidates") or []
        if isinstance(candidate, dict)
    ]


def _planned_candidate_blockers(candidates: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for candidate in candidates:
        if candidate.get("candidate_role") != "exact_card_candidate_plan":
            blockers.append("planned_candidate_role_not_exact_card_plan")
        if candidate.get("promotion_status") != "review_candidate_only":
            blockers.append("planned_candidate_status_not_review_only")
        if candidate.get("runtime_truth_allowed") is not False:
            blockers.append("planned_candidate_allowed_runtime_truth")
        if candidate.get("websearch_runtime_truth_allowed") is not False:
            blockers.append("planned_candidate_allowed_websearch_runtime_truth")
        if candidate.get("packet_ready_truth_allowed") is not False:
            blockers.append("planned_candidate_allowed_packet_ready_truth")
        if candidate.get("promotion_allowed") is not False:
            blockers.append("planned_candidate_allowed_promotion")
        if candidate.get("exact_card_created") is not False:
            blockers.append("planned_candidate_created_exact_card")
        if candidate.get("runtime_mutation_allowed") is not False:
            blockers.append("planned_candidate_allowed_runtime_mutation")
        approval = (
            candidate.get("approval_metadata")
            if isinstance(candidate.get("approval_metadata"), dict)
            else {}
        )
        if approval.get("runtime_truth_allowed") is not False:
            blockers.append("planned_candidate_approval_allowed_runtime_truth")
        for key in (
            "websearch_runtime_truth_allowed",
            "packet_ready_truth_allowed",
            "promotion_allowed",
            "approval_allowed_by_this_packet",
            "exact_card_created",
            "runtime_mutation_allowed",
        ):
            if approval.get(key) is True:
                blockers.append(f"planned_candidate_approval_{key}")
        planning_scope = (
            candidate.get("planning_scope")
            if isinstance(candidate.get("planning_scope"), dict)
            else {}
        )
        if planning_scope.get("runtime_exact_card_creation_allowed") is not False:
            blockers.append("planned_candidate_scope_allowed_exact_card_creation")
        for key in (
            "runtime_truth_allowed",
            "websearch_runtime_truth_allowed",
            "packet_ready_truth_allowed",
            "promotion_allowed",
            "approval_allowed_by_this_packet",
            "exact_card_created",
            "runtime_mutation_allowed",
        ):
            if planning_scope.get(key) is True:
                blockers.append(f"planned_candidate_scope_{key}")
        blockers.extend(_evidence_basis_blockers(candidate))
    return blockers


def _review_packet(candidate: dict[str, Any]) -> dict[str, Any]:
    packet_id = _packet_id(candidate)
    return {
        "packet_id": packet_id,
        "packet_type": "ExactCardReviewPacketRefresh",
        "packet_role": "review_only_exact_card_candidate",
        "truth_level": "review_candidate",
        "source_type": "websearch_exact_card_candidate_plan",
        "source_plan_candidate_id": candidate.get("candidate_id"),
        "source_post_extract_status": candidate.get("source_post_extract_status"),
        "source_extract_report_status": candidate.get("source_extract_report_status"),
        "evidence_basis": _safe_evidence_basis(candidate),
        "review_fields": {
            "exact_identity_variant_match_required": True,
            "serving_basis_confirmation_required": True,
            "kcal_value_confirmation_required": True,
            "source_license_confirmation_required": True,
        },
        "approval_checklist": {
            "identity_variant_confirmation_required": True,
            "serving_basis_confirmation_required": True,
            "kcal_value_confirmation_required": True,
            "source_license_confirmation_required": True,
            "explicit_exact_card_approval_required": True,
        },
        "approval_metadata": {
            "approval_mode": "none",
            "approval_scope": "exact_card_review_packet_refresh_only",
            "policy_version": "websearch_exact_card_review_packet_refresh_v1",
            "runtime_truth_allowed": False,
        },
        "approval_allowed_by_this_packet": False,
        "runtime_truth_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "promotion_allowed": False,
        "exact_card_created": False,
        "runtime_mutation_allowed": False,
        "raw_content_included": False,
        "raw_source_rows_included": False,
        "manager_visible_role": "review_packet_only_not_manager_truth",
        "required_before_runtime_truth": [
            "exact_identity_variant_match",
            "serving_basis_confirmation",
            "kcal_value_confirmation",
            "source_license_confirmation",
            "explicit_exact_card_approval",
            "exact_card_runtime_gate",
        ],
    }


def _evidence_basis_blockers(candidate: dict[str, Any]) -> list[str]:
    evidence_basis = (
        candidate.get("evidence_basis")
        if isinstance(candidate.get("evidence_basis"), dict)
        else {}
    )
    allowed_keys = {
        "extract_report_case_count",
        "extract_report_failure_count",
        "extract_port_used",
        "live_extract_used",
    }
    blockers: list[str] = []
    unexpected_keys = set(evidence_basis) - allowed_keys
    if unexpected_keys:
        blockers.append("planned_candidate_evidence_basis_unexpected_keys")
    if any(key in evidence_basis for key in ("raw_content", "raw_source_rows")):
        blockers.append("planned_candidate_evidence_basis_raw_payload")
    for key in (
        "runtime_truth_allowed",
        "websearch_runtime_truth_allowed",
        "packet_ready_truth_allowed",
        "promotion_allowed",
        "approval_allowed_by_this_packet",
        "exact_card_created",
        "runtime_mutation_allowed",
    ):
        if evidence_basis.get(key) is True:
            blockers.append(f"planned_candidate_evidence_basis_{key}")
    return blockers


def _safe_evidence_basis(candidate: dict[str, Any]) -> dict[str, Any]:
    evidence_basis = (
        candidate.get("evidence_basis")
        if isinstance(candidate.get("evidence_basis"), dict)
        else {}
    )
    return {
        "extract_report_case_count": int(
            evidence_basis.get("extract_report_case_count") or 0
        ),
        "extract_report_failure_count": int(
            evidence_basis.get("extract_report_failure_count") or 0
        ),
        "extract_port_used": evidence_basis.get("extract_port_used") is True,
        "live_extract_used": evidence_basis.get("live_extract_used") is True,
    }


def _review_packet_blockers(packets: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for packet in packets:
        if packet.get("approval_allowed_by_this_packet") is not False:
            blockers.append("review_packet_allowed_approval")
        if packet.get("runtime_truth_allowed") is not False:
            blockers.append("review_packet_allowed_runtime_truth")
        if packet.get("websearch_runtime_truth_allowed") is not False:
            blockers.append("review_packet_allowed_websearch_runtime_truth")
        if packet.get("packet_ready_truth_allowed") is not False:
            blockers.append("review_packet_allowed_packet_ready_truth")
        if packet.get("promotion_allowed") is not False:
            blockers.append("review_packet_allowed_promotion")
        if packet.get("exact_card_created") is not False:
            blockers.append("review_packet_created_exact_card")
        if packet.get("runtime_mutation_allowed") is not False:
            blockers.append("review_packet_allowed_runtime_mutation")
        if packet.get("raw_content_included") is not False:
            blockers.append("review_packet_included_raw_content")
        if packet.get("raw_source_rows_included") is not False:
            blockers.append("review_packet_included_raw_source_rows")
    return blockers


def _packet_id(candidate: dict[str, Any]) -> str:
    seed = str(candidate.get("candidate_id") or "")
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"pkt_exact_card_review_refresh_{digest}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_exact_card_review_packet_refresh"]
