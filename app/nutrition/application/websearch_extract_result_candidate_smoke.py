from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from typing import Any, Mapping, Sequence


def build_websearch_extract_result_candidate_smoke(
    *,
    selected_extract_artifact: dict[str, Any],
    extract_result_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    blockers = _selected_extract_artifact_blockers(selected_extract_artifact)
    if not blockers:
        blockers.extend(_selected_extract_packet_blockers(selected_extract_artifact))
    selected_packets = [] if blockers else _selected_extract_packets(selected_extract_artifact)
    if not selected_packets and not blockers:
        blockers.append("selected_extract_packet_missing")
    rows = list(extract_result_rows) if extract_result_rows is not None else _default_rows(selected_packets)
    if not blockers:
        blockers.extend(_extract_row_blockers(rows))
    candidates = [] if blockers else _extract_result_candidates(selected_packets, rows)
    if not candidates and not blockers:
        blockers.append("extract_result_candidate_missing")
    blockers.extend(_candidate_blockers(candidates))
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_websearch_extract_result_candidate_smoke_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_extract_result_candidate_smoke_only",
        "claim_scope": "websearch_extract_result_review_candidate_without_exact_truth",
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
            "selected_extract_artifact_type": selected_extract_artifact.get("artifact_type"),
        },
        "extract_result_candidates": candidates,
        "summary": {
            "selected_extract_packet_count": len(selected_packets),
            "extract_result_candidate_count": len(candidates),
            "runtime_truth_allowed_count": sum(
                1 for candidate in candidates if candidate["runtime_truth_allowed"] is True
            ),
            "exact_card_created_count": sum(
                1 for candidate in candidates if candidate["exact_card_created"] is True
            ),
        },
        "next_required_slice": (
            "websearch_exact_candidate_review_packet"
            if clear
            else "inspect_websearch_extract_result_candidate_blockers"
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


def _selected_extract_artifact_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "accurate_intake_websearch_selected_extract_packet_smoke_v1":
        blockers.append("unsupported_selected_extract_artifact")
    if artifact.get("status") != "pass":
        blockers.append("selected_extract_artifact_not_pass")
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("selected_extract_artifact_changed_runtime_truth")
    if artifact.get("runtime_mutation_allowed") is not False:
        blockers.append("selected_extract_artifact_allowed_runtime_mutation")
    if artifact.get("live_websearch_used") is not False:
        blockers.append("selected_extract_artifact_used_live_websearch")
    if artifact.get("live_provider_used") is not False:
        blockers.append("selected_extract_artifact_used_live_provider")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("selected_extract_artifact_claimed_readiness")
    return blockers


def _selected_extract_packets(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    packets = []
    for packet in artifact.get("selected_extract_packets") or []:
        if not isinstance(packet, dict):
            continue
        packets.append(packet)
    return packets


def _selected_extract_packet_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for packet in artifact.get("selected_extract_packets") or []:
        if not isinstance(packet, dict):
            blockers.append("selected_extract_packet_malformed")
            continue
        if packet.get("runtime_truth_allowed") is not False:
            blockers.append("selected_extract_packet_allowed_runtime_truth")
        if packet.get("packet_ready_truth_allowed") is not False:
            blockers.append("selected_extract_packet_allowed_packet_ready_truth")
        if packet.get("promotion_allowed") is not False:
            blockers.append("selected_extract_packet_allowed_promotion")
        if packet.get("exact_card_created") is not False:
            blockers.append("selected_extract_packet_created_exact_card")
        if packet.get("runtime_mutation_allowed") is not False:
            blockers.append("selected_extract_packet_allowed_runtime_mutation")
        if packet.get("raw_content_included") is not False:
            blockers.append("selected_extract_packet_included_raw_content")
        if packet.get("raw_source_rows_included") is not False:
            blockers.append("selected_extract_packet_included_raw_source_rows")
        source_boundary = packet.get("source_boundary") if isinstance(packet.get("source_boundary"), dict) else {}
        if source_boundary.get("raw_content_included") is not False:
            blockers.append("selected_extract_packet_source_boundary_included_raw_content")
        if source_boundary.get("raw_source_rows_included") is True:
            blockers.append("selected_extract_packet_source_boundary_included_raw_source_rows")
        if source_boundary.get("selected_extract_is_truth") is not False:
            blockers.append("selected_extract_packet_source_boundary_claimed_truth")
        if source_boundary.get("selected_extract_can_mutate") is not False:
            blockers.append("selected_extract_packet_source_boundary_allowed_mutation")
    return blockers


def _default_rows(selected_packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for packet in selected_packets:
        rows.append(
            {
                "selected_extract_packet_id": packet.get("packet_id"),
                "source_url": packet.get("source_url"),
                "source_title": packet.get("source_title"),
                "canonical_name": packet.get("canonical_name"),
                "matched_name": packet.get("matched_name"),
                "serving_basis_candidate": packet.get("serving_basis_candidate"),
                "kcal_value_candidate": 400,
                "kcal_text_present": True,
                "identity_text_present": True,
                "raw_extract_ref": f"fixtures/websearch_extract/{packet.get('packet_id')}#0",
            }
        )
    return rows


def _extract_row_blockers(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for row in rows:
        if "raw_content" in row:
            blockers.append("extract_result_row_included_raw_content")
        if row.get("runtime_truth_allowed") is True:
            blockers.append("extract_result_row_allowed_runtime_truth")
        if not str(row.get("selected_extract_packet_id") or "").strip():
            blockers.append("extract_result_row_missing_selected_extract_packet_id")
        if not str(row.get("source_url") or "").strip():
            blockers.append("extract_result_row_missing_source_url")
        if _kcal_value(row.get("kcal_value_candidate")) is None:
            blockers.append("extract_result_row_missing_kcal_candidate")
        if row.get("kcal_text_present") is not True:
            blockers.append("extract_result_row_missing_kcal_text")
        if not str(row.get("serving_basis_candidate") or "").strip():
            blockers.append("extract_result_row_missing_serving_basis_candidate")
        if row.get("identity_text_present") is not True:
            blockers.append("extract_result_row_missing_identity_text")
    return blockers


def _extract_result_candidates(
    selected_packets: list[dict[str, Any]],
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    selected_by_id = {
        str(packet.get("packet_id") or ""): packet
        for packet in selected_packets
        if str(packet.get("packet_id") or "").strip()
    }
    candidates = []
    for row in rows:
        selected_packet = selected_by_id.get(str(row.get("selected_extract_packet_id") or ""))
        if selected_packet is None:
            continue
        candidates.append(_extract_result_candidate(selected_packet=selected_packet, row=row))
    return candidates


def _extract_result_candidate(
    *,
    selected_packet: dict[str, Any],
    row: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_id = _candidate_id(selected_packet, row)
    return {
        "candidate_id": candidate_id,
        "candidate_role": "websearch_extract_result_review_candidate",
        "promotion_status": "review_candidate_only",
        "source_selected_extract_packet_id": selected_packet.get("packet_id"),
        "source_exact_card_candidate_id": selected_packet.get("candidate_id"),
        "source_url": row.get("source_url"),
        "source_title": row.get("source_title") or selected_packet.get("source_title"),
        "canonical_name": row.get("canonical_name") or selected_packet.get("canonical_name"),
        "matched_name": row.get("matched_name") or selected_packet.get("matched_name"),
        "extracted_fields": {
            "kcal_value_candidate": _kcal_value(row.get("kcal_value_candidate")),
            "kcal_text_present": row.get("kcal_text_present") is True,
            "serving_basis_candidate": row.get("serving_basis_candidate"),
            "identity_text_present": row.get("identity_text_present") is True,
        },
        "source_provenance": {
            "raw_extract_ref": row.get("raw_extract_ref"),
            "selected_extract_packet_id": selected_packet.get("packet_id"),
            "source_url": row.get("source_url"),
        },
        "approval_metadata": {
            "approval_mode": "none",
            "approval_scope": "extract_result_review_candidate_only",
            "policy_version": "websearch_extract_result_candidate_smoke_v1",
            "runtime_truth_allowed": False,
        },
        "runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "promotion_allowed": False,
        "exact_card_created": False,
        "runtime_mutation_allowed": False,
        "raw_content_included": False,
        "raw_source_rows_included": False,
        "required_before_runtime_truth": [
            "serving_basis_confirmation",
            "identity_variant_confirmation",
            "explicit_exact_card_approval",
            "exact_card_record_creation",
        ],
    }


def _candidate_blockers(candidates: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for candidate in candidates:
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
    return blockers


def _kcal_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _candidate_id(selected_packet: Mapping[str, Any], row: Mapping[str, Any]) -> str:
    seed = "|".join(
        str(value or "")
        for value in (
            selected_packet.get("packet_id"),
            row.get("source_url"),
            row.get("raw_extract_ref"),
            row.get("kcal_value_candidate"),
        )
    )
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"web_extract_result_candidate:{digest}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_extract_result_candidate_smoke"]
