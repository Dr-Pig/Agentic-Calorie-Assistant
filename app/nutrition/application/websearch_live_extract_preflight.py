from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Any

from .websearch_cache_rate_license_wall import MAX_CHUNKS_PER_SOURCE, MAX_SEARCH_RESULTS


def build_websearch_live_extract_preflight(
    *,
    exact_review_packet_artifact: dict[str, Any],
) -> dict[str, Any]:
    blockers = _review_artifact_blockers(exact_review_packet_artifact)
    candidate_review_packets = _review_packets(exact_review_packet_artifact)
    if not candidate_review_packets and not blockers:
        blockers.append("exact_review_packet_missing")
    blockers.extend(_review_packet_blockers(candidate_review_packets))
    clear = not blockers
    review_packets = candidate_review_packets if clear else []
    return {
        "artifact_type": "accurate_intake_websearch_live_extract_preflight_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_live_extract_preflight_only",
        "claim_scope": "websearch_live_extract_diagnostic_preflight_without_live_call",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "live_websearch_used": False,
        "live_extract_used": False,
        "live_provider_used": False,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "readiness_claimed": False,
        "ready_for_live_extract_diagnostic": clear,
        "ready_for_runtime_truth": False,
        "source_artifacts": {
            "exact_review_packet_artifact_type": exact_review_packet_artifact.get("artifact_type"),
        },
        "diagnostic_contract": {
            "live_call_allowed_by_this_artifact": False,
            "requires_explicit_allow_live_flag": True,
            "max_search_attempts": 2,
            "max_search_results": MAX_SEARCH_RESULTS,
            "max_extract_urls_per_case": 1,
            "max_chunks_per_source": MAX_CHUNKS_PER_SOURCE,
            "cache_required": True,
            "raw_content_allowed_in_manager_context": False,
            "extract_result_role": "review_candidate_only",
            "ledger_mutation_allowed": False,
            "exact_card_creation_allowed": False,
        },
        "review_packet_refs": [
            {
                "packet_id": packet.get("packet_id"),
                "source_url": packet.get("source_url"),
                "canonical_name": packet.get("canonical_name"),
                "matched_name": packet.get("matched_name"),
                "packet_digest": _review_packet_digest(packet),
            }
            for packet in review_packets
        ],
        "summary": {
            "review_packet_count": len(review_packets),
            "ready_for_live_extract_diagnostic_count": len(review_packets) if clear else 0,
            "ready_for_runtime_truth_count": 0,
        },
        "next_required_slice": (
            "grokfast_websearch_packet_live_diagnostic"
            if clear
            else "inspect_websearch_live_extract_preflight_blockers"
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


def is_websearch_live_extract_preflight_clear(artifact: dict[str, Any]) -> bool:
    return (
        artifact.get("artifact_type") == "accurate_intake_websearch_live_extract_preflight_v1"
        and not _preflight_integrity_blockers(artifact)
    )


def _review_artifact_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "accurate_intake_websearch_exact_candidate_review_packet_v1":
        blockers.append("unsupported_exact_review_packet_artifact")
    if artifact.get("status") != "pass":
        blockers.append("exact_review_packet_artifact_not_pass")
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("exact_review_packet_artifact_changed_runtime_truth")
    if artifact.get("runtime_mutation_allowed") is not False:
        blockers.append("exact_review_packet_artifact_allowed_runtime_mutation")
    if artifact.get("live_websearch_used") is not False:
        blockers.append("exact_review_packet_artifact_used_live_websearch")
    if artifact.get("live_extract_used") is not False:
        blockers.append("exact_review_packet_artifact_used_live_extract")
    if artifact.get("live_provider_used") is not False:
        blockers.append("exact_review_packet_artifact_used_live_provider")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("exact_review_packet_artifact_claimed_readiness")
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    if int(summary.get("runtime_truth_allowed_count") or 0) != 0:
        blockers.append("exact_review_packet_artifact_summary_runtime_truth_allowed")
    if int(summary.get("exact_card_created_count") or 0) != 0:
        blockers.append("exact_review_packet_artifact_summary_exact_card_created")
    if int(summary.get("approval_allowed_count") or 0) != 0:
        blockers.append("exact_review_packet_artifact_summary_approval_allowed")
    return blockers


def _preflight_integrity_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("status") != "pass":
        blockers.append("preflight_status_not_pass")
    if artifact.get("ready_for_live_extract_diagnostic") is not True:
        blockers.append("preflight_not_ready_for_live_extract_diagnostic")
    if artifact.get("ready_for_runtime_truth") is not False:
        blockers.append("preflight_allowed_runtime_truth")
    if artifact.get("blockers"):
        blockers.append("preflight_has_blockers")
    if artifact.get("next_required_slice") != "grokfast_websearch_packet_live_diagnostic":
        blockers.append("preflight_next_slice_mismatch")
    for key, blocker in (
        ("live_websearch_used", "preflight_used_live_websearch"),
        ("live_extract_used", "preflight_used_live_extract"),
        ("live_provider_used", "preflight_used_live_provider"),
        ("runtime_truth_changed", "preflight_changed_runtime_truth"),
        ("runtime_mutation_allowed", "preflight_allowed_runtime_mutation"),
        ("manager_context_changed", "preflight_changed_manager_context"),
        ("packetizer_format_changed", "preflight_changed_packetizer_format"),
        ("readiness_claimed", "preflight_claimed_readiness"),
    ):
        if artifact.get(key) is not False:
            blockers.append(blocker)
    contract = artifact.get("diagnostic_contract") if isinstance(artifact.get("diagnostic_contract"), dict) else {}
    if contract.get("live_call_allowed_by_this_artifact") is not False:
        blockers.append("preflight_contract_allowed_live_call")
    if contract.get("requires_explicit_allow_live_flag") is not True:
        blockers.append("preflight_contract_missing_allow_live_flag")
    if contract.get("cache_required") is not True:
        blockers.append("preflight_contract_missing_cache")
    if contract.get("raw_content_allowed_in_manager_context") is not False:
        blockers.append("preflight_contract_allowed_raw_content_in_manager_context")
    if contract.get("ledger_mutation_allowed") is not False:
        blockers.append("preflight_contract_allowed_ledger_mutation")
    if contract.get("exact_card_creation_allowed") is not False:
        blockers.append("preflight_contract_allowed_exact_card_creation")
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    if int(summary.get("review_packet_count") or 0) <= 0:
        blockers.append("preflight_summary_review_packet_missing")
    if int(summary.get("ready_for_runtime_truth_count") or 0) != 0:
        blockers.append("preflight_summary_runtime_truth_ready")
    return blockers


def _review_packets(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        packet
        for packet in artifact.get("review_packets") or []
        if isinstance(packet, dict)
    ]


def _review_packet_blockers(packets: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for packet in packets:
        if not str(packet.get("packet_id") or "").strip():
            blockers.append("exact_review_packet_missing_packet_id")
        if not str(packet.get("source_url") or "").strip():
            blockers.append("exact_review_packet_missing_source_url")
        review_fields = packet.get("review_fields") if isinstance(packet.get("review_fields"), dict) else {}
        if _kcal_value(review_fields.get("kcal_value_candidate")) is None:
            blockers.append("exact_review_packet_missing_kcal_candidate")
        if review_fields.get("kcal_text_present") is not True:
            blockers.append("exact_review_packet_missing_kcal_text")
        if review_fields.get("identity_text_present") is not True:
            blockers.append("exact_review_packet_missing_identity_text")
        if not str(review_fields.get("serving_basis_candidate") or "").strip():
            blockers.append("exact_review_packet_missing_serving_basis")
        if packet.get("approval_allowed_by_this_packet") is not False:
            blockers.append("exact_review_packet_allowed_approval")
        if packet.get("runtime_truth_allowed") is not False:
            blockers.append("exact_review_packet_allowed_runtime_truth")
        if packet.get("packet_ready_truth_allowed") is not False:
            blockers.append("exact_review_packet_allowed_packet_ready_truth")
        if packet.get("promotion_allowed") is not False:
            blockers.append("exact_review_packet_allowed_promotion")
        if packet.get("exact_card_created") is not False:
            blockers.append("exact_review_packet_created_exact_card")
        if packet.get("runtime_mutation_allowed") is not False:
            blockers.append("exact_review_packet_allowed_runtime_mutation")
        if packet.get("raw_content_included") is not False:
            blockers.append("exact_review_packet_included_raw_content")
        if packet.get("raw_source_rows_included") is not False:
            blockers.append("exact_review_packet_included_raw_source_rows")
    return blockers


def _kcal_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _review_packet_digest(packet: dict[str, Any]) -> str:
    payload = json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "build_websearch_live_extract_preflight",
    "is_websearch_live_extract_preflight_clear",
]
