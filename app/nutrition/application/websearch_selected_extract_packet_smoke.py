from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from typing import Any

from .websearch_cache_rate_license_wall import (
    MAX_CHUNKS_PER_SOURCE,
    build_websearch_cache_rate_license_wall,
    build_websearch_extract_request_policy,
)


def build_websearch_selected_extract_packet_smoke(
    *,
    exact_card_readiness_artifact: dict[str, Any],
    cache_rate_license_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cache_wall = cache_rate_license_artifact or build_websearch_cache_rate_license_wall()
    blockers = [
        *_readiness_artifact_blockers(exact_card_readiness_artifact),
        *_cache_wall_blockers(cache_wall),
    ]
    if not blockers:
        blockers.extend(_readiness_candidate_blockers(exact_card_readiness_artifact))
    packets = [] if blockers else _selected_extract_packets(exact_card_readiness_artifact)
    blockers.extend(_packet_blockers(packets))
    if not packets and not blockers:
        blockers.append("selected_extract_candidate_missing")
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_websearch_selected_extract_packet_smoke_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_selected_extract_packet_smoke_only",
        "claim_scope": "websearch_selected_extract_request_packet_without_live_extract",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_websearch_used": False,
        "live_provider_used": False,
        "readiness_claimed": False,
        "source_artifacts": {
            "exact_card_readiness_artifact_type": exact_card_readiness_artifact.get("artifact_type"),
            "cache_rate_license_artifact_type": cache_wall.get("artifact_type"),
        },
        "selected_extract_packets": packets,
        "summary": {
            "selected_extract_packet_count": len(packets),
            "runtime_truth_allowed_count": sum(
                1 for packet in packets if packet["runtime_truth_allowed"] is True
            ),
            "raw_content_included_count": sum(
                1 for packet in packets if packet["raw_content_included"] is True
            ),
            "max_chunks_per_source": MAX_CHUNKS_PER_SOURCE,
        },
        "next_required_slice": (
            "websearch_extract_result_candidate_smoke"
            if clear
            else "inspect_websearch_selected_extract_packet_blockers"
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


def _readiness_artifact_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "accurate_intake_exact_card_candidate_promotion_readiness_v1":
        blockers.append("unsupported_exact_card_readiness_artifact")
    if artifact.get("status") != "pass":
        blockers.append("exact_card_readiness_not_pass")
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("exact_card_readiness_changed_runtime_truth")
    if artifact.get("mutation_changed") is not False:
        blockers.append("exact_card_readiness_changed_mutation")
    if artifact.get("live_websearch_used") is not False:
        blockers.append("exact_card_readiness_used_live_websearch")
    if artifact.get("live_provider_used") is not False:
        blockers.append("exact_card_readiness_used_live_provider")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("exact_card_readiness_claimed_readiness")
    return blockers


def _cache_wall_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "accurate_intake_websearch_cache_rate_license_wall_v1":
        blockers.append("unsupported_websearch_cache_rate_license_wall")
    if artifact.get("status") != "pass":
        blockers.append("websearch_cache_rate_license_wall_not_pass")
    if artifact.get("live_websearch_used") is not False:
        blockers.append("websearch_cache_rate_license_wall_used_live_websearch")
    if artifact.get("live_provider_used") is not False:
        blockers.append("websearch_cache_rate_license_wall_used_live_provider")
    if artifact.get("websearch_runtime_truth_allowed") is not False:
        blockers.append("websearch_cache_rate_license_wall_allowed_runtime_truth")
    if artifact.get("runtime_mutation_allowed") is not False:
        blockers.append("websearch_cache_rate_license_wall_allowed_runtime_mutation")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("websearch_cache_rate_license_wall_claimed_readiness")
    return blockers


def _selected_extract_packets(readiness_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _selected_extract_packet(candidate)
        for candidate in readiness_artifact.get("candidates") or []
        if isinstance(candidate, dict)
        and candidate.get("readiness_status") == "selected_extract_candidate_ready_for_review"
    ]


def _readiness_candidate_blockers(readiness_artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for candidate in readiness_artifact.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("runtime_truth_allowed") is not False:
            blockers.append("selected_extract_candidate_allowed_runtime_truth")
        if candidate.get("packet_ready_truth_allowed") is not False:
            blockers.append("selected_extract_candidate_allowed_packet_ready_truth")
        if candidate.get("promotion_allowed") is not False:
            blockers.append("selected_extract_candidate_allowed_promotion")
        if candidate.get("exact_card_created") is not False:
            blockers.append("selected_extract_candidate_created_exact_card")
    return blockers


def _selected_extract_packet(candidate: dict[str, Any]) -> dict[str, Any]:
    source_url = str(candidate.get("source_url") or "").strip()
    query = _extract_query(candidate)
    extract_request = build_websearch_extract_request_policy(
        urls=(source_url,),
        query=query,
    )
    packet_id = _packet_id(candidate)
    return {
        "packet_id": packet_id,
        "packet_type": "SelectedWebExtractRequestPacket",
        "truth_level": "candidate_extract_request",
        "source_type": "websearch_selected_extract",
        "candidate_id": candidate.get("candidate_id"),
        "selected_search_packet_id": candidate.get("selected_search_packet_id"),
        "source_url": source_url,
        "source_title": candidate.get("source_title"),
        "canonical_name": candidate.get("canonical_name"),
        "matched_name": candidate.get("matched_name"),
        "license_status": candidate.get("license_status"),
        "robots_status": candidate.get("robots_status"),
        "identity_confidence": candidate.get("identity_confidence"),
        "serving_basis_candidate": candidate.get("serving_basis_candidate"),
        "extract_request_policy": extract_request,
        "source_boundary": {
            "raw_source_rows_included": False,
            "raw_content_included": False,
            "raw_content_truth_allowed": False,
            "selected_extract_is_truth": False,
            "selected_extract_can_mutate": False,
        },
        "runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "promotion_allowed": False,
        "exact_card_created": False,
        "runtime_mutation_allowed": False,
        "manager_visible_role": "compact_selected_extract_request_candidate",
        "manager_decision_authority": False,
        "required_next_evidence": [
            "bounded_extract_result",
            "serving_basis_confirmation",
            "kcal_field_extraction",
            "explicit_exact_card_approval",
        ],
        "raw_source_rows_included": False,
        "raw_content_included": False,
    }


def _extract_query(candidate: dict[str, Any]) -> str:
    for key in ("canonical_name", "matched_name", "source_title"):
        value = str(candidate.get(key) or "").strip()
        if value:
            return value
    return "exact food nutrition candidate"


def _packet_blockers(packets: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for packet in packets:
        extract_request = packet.get("extract_request_policy")
        if not isinstance(extract_request, dict):
            blockers.append("selected_extract_packet_missing_extract_request_policy")
            continue
        if not str(packet.get("source_url") or "").strip():
            blockers.append("selected_extract_packet_missing_source_url")
        if packet.get("runtime_truth_allowed") is not False:
            blockers.append("selected_extract_packet_allowed_runtime_truth")
        if packet.get("packet_ready_truth_allowed") is not False:
            blockers.append("selected_extract_packet_allowed_packet_ready_truth")
        if packet.get("promotion_allowed") is not False:
            blockers.append("selected_extract_packet_allowed_promotion")
        if packet.get("runtime_mutation_allowed") is not False:
            blockers.append("selected_extract_packet_allowed_runtime_mutation")
        if packet.get("raw_source_rows_included") is not False:
            blockers.append("selected_extract_packet_included_raw_source_rows")
        if packet.get("raw_content_included") is not False:
            blockers.append("selected_extract_packet_included_raw_content")
        if extract_request.get("runtime_truth_allowed") is not False:
            blockers.append("selected_extract_request_allowed_runtime_truth")
        if extract_request.get("raw_content_truth_allowed") is not False:
            blockers.append("selected_extract_request_allowed_raw_content_truth")
        if int(extract_request.get("chunks_per_source") or 0) > MAX_CHUNKS_PER_SOURCE:
            blockers.append("selected_extract_request_unbounded_chunks")
    return blockers


def _packet_id(candidate: dict[str, Any]) -> str:
    seed = "|".join(
        str(candidate.get(key) or "")
        for key in ("candidate_id", "selected_search_packet_id", "source_url")
    )
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"pkt_selected_extract_request_{digest}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_selected_extract_packet_smoke"]
