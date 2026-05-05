from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from typing import Any


def build_websearch_exact_candidate_review_packet(
    *,
    extract_result_artifact: dict[str, Any],
) -> dict[str, Any]:
    blockers = _extract_result_artifact_blockers(extract_result_artifact)
    if not blockers:
        blockers.extend(_extract_result_candidate_blockers(extract_result_artifact))
    candidates = [] if blockers else _extract_result_candidates(extract_result_artifact)
    if not candidates and not blockers:
        blockers.append("extract_result_candidate_missing")
    review_packets = [] if blockers else [_review_packet(candidate) for candidate in candidates]
    blockers.extend(_review_packet_blockers(review_packets))
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_websearch_exact_candidate_review_packet_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_exact_candidate_review_packet_only",
        "claim_scope": "websearch_exact_candidate_review_packet_without_truth_promotion",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_websearch_used": False,
        "live_extract_used": False,
        "live_provider_used": False,
        "readiness_claimed": False,
        "source_artifacts": {
            "extract_result_artifact_type": extract_result_artifact.get("artifact_type"),
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
            "websearch_live_extract_preflight"
            if clear
            else "inspect_websearch_exact_candidate_review_packet_blockers"
        ),
        "non_claims": [
            "no_live_websearch_call",
            "no_live_extract_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def _extract_result_artifact_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "accurate_intake_websearch_extract_result_candidate_smoke_v1":
        blockers.append("unsupported_extract_result_candidate_artifact")
    if artifact.get("status") != "pass":
        blockers.append("extract_result_candidate_artifact_not_pass")
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("extract_result_candidate_artifact_changed_runtime_truth")
    if artifact.get("runtime_mutation_allowed") is not False:
        blockers.append("extract_result_candidate_artifact_allowed_runtime_mutation")
    if artifact.get("live_websearch_used") is not False:
        blockers.append("extract_result_candidate_artifact_used_live_websearch")
    if artifact.get("live_extract_used") is not False:
        blockers.append("extract_result_candidate_artifact_used_live_extract")
    if artifact.get("live_provider_used") is not False:
        blockers.append("extract_result_candidate_artifact_used_live_provider")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("extract_result_candidate_artifact_claimed_readiness")
    return blockers


def _extract_result_candidates(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        candidate
        for candidate in artifact.get("extract_result_candidates") or []
        if isinstance(candidate, dict)
    ]


def _extract_result_candidate_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for candidate in artifact.get("extract_result_candidates") or []:
        if not isinstance(candidate, dict):
            blockers.append("extract_result_candidate_malformed")
            continue
        if candidate.get("runtime_truth_allowed") is not False:
            blockers.append("extract_result_candidate_allowed_runtime_truth")
        if candidate.get("packet_ready_truth_allowed") is not False:
            blockers.append("extract_result_candidate_allowed_packet_ready_truth")
        if candidate.get("promotion_allowed") is not False:
            blockers.append("extract_result_candidate_allowed_promotion")
        if candidate.get("exact_card_created") is not False:
            blockers.append("extract_result_candidate_created_exact_card")
        if candidate.get("runtime_mutation_allowed") is not False:
            blockers.append("extract_result_candidate_allowed_runtime_mutation")
        if candidate.get("raw_content_included") is not False:
            blockers.append("extract_result_candidate_included_raw_content")
        if candidate.get("raw_source_rows_included") is not False:
            blockers.append("extract_result_candidate_included_raw_source_rows")
        fields = candidate.get("extracted_fields") if isinstance(candidate.get("extracted_fields"), dict) else {}
        if _kcal_value(fields.get("kcal_value_candidate")) is None:
            blockers.append("extract_result_candidate_missing_kcal_candidate")
        if fields.get("kcal_text_present") is not True:
            blockers.append("extract_result_candidate_missing_kcal_text")
        if not str(fields.get("serving_basis_candidate") or "").strip():
            blockers.append("extract_result_candidate_missing_serving_basis")
        if fields.get("identity_text_present") is not True:
            blockers.append("extract_result_candidate_missing_identity_text")
    return blockers


def _review_packet(candidate: dict[str, Any]) -> dict[str, Any]:
    fields = candidate["extracted_fields"]
    source_provenance = candidate.get("source_provenance") if isinstance(candidate.get("source_provenance"), dict) else {}
    packet_id = _packet_id(candidate)
    return {
        "packet_id": packet_id,
        "packet_type": "ExactCardReviewPacket",
        "packet_role": "review_only_exact_card_candidate",
        "truth_level": "review_candidate",
        "source_type": "websearch_extract_result",
        "source_extract_result_candidate_id": candidate.get("candidate_id"),
        "source_selected_extract_packet_id": candidate.get("source_selected_extract_packet_id"),
        "source_exact_card_candidate_id": candidate.get("source_exact_card_candidate_id"),
        "source_url": candidate.get("source_url"),
        "source_title": candidate.get("source_title"),
        "canonical_name": candidate.get("canonical_name"),
        "matched_name": candidate.get("matched_name"),
        "review_fields": {
            "kcal_value_candidate": _kcal_value(fields.get("kcal_value_candidate")),
            "kcal_text_present": fields.get("kcal_text_present") is True,
            "serving_basis_candidate": fields.get("serving_basis_candidate"),
            "identity_text_present": fields.get("identity_text_present") is True,
        },
        "approval_checklist": {
            "identity_variant_confirmation_required": True,
            "serving_basis_confirmation_required": True,
            "kcal_value_confirmation_required": True,
            "source_license_confirmation_required": True,
            "explicit_exact_card_approval_required": True,
        },
        "source_provenance": {
            "raw_extract_ref": source_provenance.get("raw_extract_ref"),
            "selected_extract_packet_id": source_provenance.get("selected_extract_packet_id"),
            "source_url": source_provenance.get("source_url") or candidate.get("source_url"),
        },
        "approval_metadata": {
            "approval_mode": "none",
            "approval_scope": "exact_card_review_packet_only",
            "policy_version": "websearch_exact_candidate_review_packet_v1",
            "runtime_truth_allowed": False,
        },
        "approval_allowed_by_this_packet": False,
        "runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "promotion_allowed": False,
        "exact_card_created": False,
        "runtime_mutation_allowed": False,
        "raw_content_included": False,
        "raw_source_rows_included": False,
        "manager_visible_role": "review_packet_only_not_manager_truth",
        "required_before_runtime_truth": [
            "human_or_batch_exact_card_approval",
            "exact_card_record_creation",
            "exact_card_runtime_gate",
        ],
    }


def _review_packet_blockers(packets: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for packet in packets:
        if packet.get("approval_allowed_by_this_packet") is not False:
            blockers.append("review_packet_allowed_approval")
        if packet.get("runtime_truth_allowed") is not False:
            blockers.append("review_packet_allowed_runtime_truth")
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


def _kcal_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _packet_id(candidate: dict[str, Any]) -> str:
    seed = "|".join(
        str(candidate.get(key) or "")
        for key in ("candidate_id", "source_url", "source_selected_extract_packet_id")
    )
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"pkt_exact_card_review_{digest}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_exact_candidate_review_packet"]
