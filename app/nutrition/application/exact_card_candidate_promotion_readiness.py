from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def build_exact_card_candidate_promotion_readiness(
    *,
    exact_lane_artifact: dict[str, Any],
) -> dict[str, Any]:
    blockers = _artifact_blockers(exact_lane_artifact)
    candidates = _candidate_reports(exact_lane_artifact) if not blockers else []
    blockers.extend(_candidate_blockers(candidates))
    if not candidates and not blockers:
        blockers.append("exact_card_candidate_missing")
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_exact_card_candidate_promotion_readiness_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_exact_candidate_readiness_only",
        "claim_scope": "exact_card_candidate_promotion_readiness_without_truth_promotion",
        "status": "pass" if clear else "blocked",
        "blockers": blockers,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_websearch_used": False,
        "live_provider_used": False,
        "readiness_claimed": False,
        "source_artifact_type": exact_lane_artifact.get("artifact_type"),
        "candidates": candidates,
        "summary": {
            "exact_card_candidate_count": len(candidates),
            "runtime_truth_allowed_count": sum(
                1 for candidate in candidates if candidate["runtime_truth_allowed"] is True
            ),
            "promotion_allowed_count": sum(
                1 for candidate in candidates if candidate["promotion_allowed"] is True
            ),
            "candidate_ready_for_review_count": sum(
                1
                for candidate in candidates
                if candidate["readiness_status"] == "selected_extract_candidate_ready_for_review"
            ),
        },
        "promotion_boundary": {
            "candidate_can_trigger_extract_review": True,
            "candidate_can_create_exact_card": False,
            "candidate_can_create_runtime_truth": False,
            "required_approval_mode_before_runtime_truth": "explicit_exact_card_approval",
        },
        "next_required_slice": (
            "websearch_selected_extract_packet_smoke"
            if clear
            else "inspect_exact_card_candidate_readiness_blockers"
        ),
        "non_claims": [
            "no_exact_card_truth_promotion",
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_readiness_claim",
        ],
    }


def _artifact_blockers(exact_lane_artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if exact_lane_artifact.get("artifact_type") != "accurate_intake_exact_evidence_lane_policy_v1":
        blockers.append("unsupported_exact_lane_artifact")
    if exact_lane_artifact.get("runtime_truth_changed") is not False:
        blockers.append("exact_lane_changed_runtime_truth")
    if exact_lane_artifact.get("runtime_mutation_allowed") is not False:
        blockers.append("exact_lane_allowed_runtime_mutation")
    if exact_lane_artifact.get("live_websearch_used") is not False:
        blockers.append("exact_lane_used_live_websearch")
    if exact_lane_artifact.get("live_provider_used") is not False:
        blockers.append("exact_lane_used_live_provider")
    return blockers


def _candidate_reports(exact_lane_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    reports = []
    for case in exact_lane_artifact.get("cases") or []:
        if not isinstance(case, dict):
            continue
        staging = case.get("exact_card_staging") if isinstance(case.get("exact_card_staging"), dict) else {}
        for candidate in staging.get("candidates") or []:
            if not isinstance(candidate, dict):
                continue
            reports.append(_candidate_report(case_id=str(case.get("case_id") or ""), candidate=candidate))
    return reports


def _candidate_report(*, case_id: str, candidate: dict[str, Any]) -> dict[str, Any]:
    missing = [
        field
        for field in ("candidate_id", "source_url", "canonical_name", "selected_search_packet_id")
        if not str(candidate.get(field) or "").strip()
    ]
    source_policy = dict(candidate.get("source_policy") or {})
    readiness_status = (
        "selected_extract_candidate_ready_for_review" if not missing else "missing_required_metadata"
    )
    return {
        "case_id": case_id,
        "candidate_id": candidate.get("candidate_id"),
        "readiness_status": readiness_status,
        "missing_required_fields": missing,
        "promotion_decision": "blocked_until_explicit_exact_card_approval",
        "promotion_allowed": candidate.get("promotion_allowed") is True,
        "runtime_truth_allowed": candidate.get("runtime_truth_allowed") is True,
        "packet_ready_truth_allowed": candidate.get("packet_ready_truth_allowed") is True,
        "exact_card_created": candidate.get("exact_card_created") is True,
        "source_url": candidate.get("source_url"),
        "source_title": candidate.get("source_title"),
        "canonical_name": candidate.get("canonical_name"),
        "matched_name": candidate.get("matched_name"),
        "selected_search_packet_id": candidate.get("selected_search_packet_id"),
        "license_status": source_policy.get("license_status"),
        "robots_status": source_policy.get("robots_status"),
        "identity_confidence": source_policy.get("identity_confidence"),
        "serving_basis_candidate": source_policy.get("serving_basis_candidate"),
        "required_before_runtime_truth": [
            "selected_extract_content",
            "serving_basis_confirmation",
            "kcal_field_extraction",
            "approval_metadata",
        ],
    }


def _candidate_blockers(candidates: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for candidate in candidates:
        if candidate["runtime_truth_allowed"] is True:
            blockers.append("exact_card_candidate_runtime_truth_leak")
        if candidate["packet_ready_truth_allowed"] is True:
            blockers.append("exact_card_candidate_packet_ready_truth_leak")
        if candidate["promotion_allowed"] is True:
            blockers.append("exact_card_candidate_promotion_allowed_without_approval")
        if candidate["exact_card_created"] is True:
            blockers.append("exact_card_candidate_created_exact_card")
        if candidate["missing_required_fields"]:
            blockers.append("exact_card_candidate_missing_required_metadata")
    return sorted(set(blockers))


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_exact_card_candidate_promotion_readiness"]
