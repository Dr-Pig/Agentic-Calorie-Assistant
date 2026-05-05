from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from typing import Any


_EXPECTED_NEXT_SLICE = "websearch_exact_card_manifest_no_runtime_wall"
_DESIGN_BLOCKER = "exact_card_manifest_runtime_truth_not_allowed"

_FORBIDDEN_TRUE_FLAGS = {
    "runtime_truth_changed": "manifest_review_packet_changed_runtime_truth",
    "mutation_changed": "manifest_review_packet_changed_mutation",
    "runtime_mutation_allowed": "manifest_review_packet_allowed_runtime_mutation",
    "websearch_runtime_truth_allowed": (
        "manifest_review_packet_allowed_websearch_runtime_truth"
    ),
    "runtime_web_activation_approved": (
        "manifest_review_packet_approved_runtime_web_activation"
    ),
    "runtime_web_activation_recommended": (
        "manifest_review_packet_recommended_runtime_web_activation"
    ),
    "live_provider_used": "manifest_review_packet_used_live_provider",
    "live_websearch_used": "manifest_review_packet_used_live_websearch",
    "source_live_websearch_used": "manifest_review_packet_used_source_live_websearch",
    "exact_card_created": "manifest_review_packet_created_exact_card",
    "readiness_claimed": "manifest_review_packet_claimed_readiness",
    "ready_for_runtime_truth": "manifest_review_packet_claimed_ready_for_runtime_truth",
    "ready_for_runtime_mutation": (
        "manifest_review_packet_claimed_ready_for_runtime_mutation"
    ),
    "shared_contract_changed": "manifest_review_packet_changed_shared_contract",
    "manager_context_changed": "manifest_review_packet_changed_manager_context",
    "packetizer_format_changed": "manifest_review_packet_changed_packetizer_format",
    "raw_content_included": "manifest_review_packet_included_raw_content",
    "raw_source_rows_included": "manifest_review_packet_included_raw_source_rows",
}

_UNSAFE_NESTED_FLAGS = (
    "runtime_truth",
    "runtime_truth_changed",
    "runtime_truth_payload",
    "runtime_truth_record",
    "runtime_truth_records",
    "mutation_changed",
    "mutation",
    "mutation_payload",
    "ledger_mutation",
    "intake_ledger_mutation",
    "raw_content",
    "raw_payload",
    "raw_rows",
    "raw_source_rows",
    "raw_source_payload",
    "readiness_payload",
    "readiness",
    "readiness_claim",
    "packet_ready_truth",
    "runtime_truth_allowed",
    "websearch_runtime_truth_allowed",
    "packet_ready_truth_payload",
    "packet_ready_truth_allowed",
    "promotion",
    "promotion_payload",
    "promotion_record",
    "promotion_records",
    "promotion_allowed",
    "truth_promotion",
    "truth_promotion_payload",
    "approval_allowed_by_this_wall",
    "approval_allowed_by_this_packet",
    "promotion_allowed_by_this_artifact",
    "exact_card",
    "exact_cards",
    "exact_card_payload",
    "exact_card_record",
    "exact_card_records",
    "exact_card_truth",
    "runtime_exact_card",
    "exact_card_created",
    "runtime_mutation_allowed",
    "raw_content_included",
    "raw_source_rows_included",
    "runtime_web_activation_approved",
    "runtime_web_activation_recommended",
    "live",
    "live_payload",
    "live_provider_payload",
    "live_provider_response",
    "live_websearch_response",
    "live_websearch_used",
    "source_live_websearch_used",
    "live_provider_used",
    "ready_for_runtime_truth",
    "ready_for_runtime_mutation",
    "readiness_claimed",
    "shared_contract",
    "shared_contract_patch",
    "shared_contract_payload",
    "shared_contract_changes",
    "shared_contract_changed",
    "manager_context_changed",
    "manager_context_packet_changed",
    "manager_context_packet_schema_changed",
    "packetizer_format_changed",
    "packetizer_changed",
    "basket_semantics_changed",
    "nutrition_evidence_store_port_changed",
)


def build_websearch_exact_card_manifest_no_runtime_wall(
    *,
    manifest_review_packet: dict[str, Any],
) -> dict[str, Any]:
    blockers = _manifest_review_packet_blockers(manifest_review_packet)
    review_packets = [] if blockers else _review_packets(manifest_review_packet)
    blockers.extend(_review_packet_blockers(review_packets))
    wall_records = [] if blockers else [_wall_record(packet) for packet in review_packets]
    blockers.extend(_wall_record_blockers(wall_records))
    if not wall_records and not blockers:
        blockers.append("manifest_no_runtime_wall_review_packet_missing")
    if wall_records and not blockers:
        blockers.append(_DESIGN_BLOCKER)
    design_blocked = blockers == [_DESIGN_BLOCKER]
    return {
        "artifact_type": "accurate_intake_websearch_exact_card_manifest_no_runtime_wall_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_exact_card_manifest_no_runtime_wall",
        "claim_scope": "websearch_exact_card_manifest_wall_without_runtime_truth",
        "status": "blocked_runtime_truth_by_design" if design_blocked else "blocked",
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
            "manifest_review_packet_type": _safe_artifact_type(manifest_review_packet),
        },
        "no_runtime_wall_records": wall_records,
        "summary": {
            "blocked_review_packet_count": len(wall_records),
            "runtime_truth_allowed_count": 0,
            "exact_card_created_count": 0,
            "promotion_allowed_count": 0,
        },
        "next_required_slice": (
            "websearch_exact_card_record_creation_contract_probe"
            if design_blocked
            else "inspect_websearch_exact_card_manifest_no_runtime_wall_blockers"
        ),
        "non_claims": [
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_readiness_claim",
        ],
    }


def _manifest_review_packet_blockers(artifact: dict[str, Any]) -> list[str]:
    if not isinstance(artifact, dict):
        return ["manifest_review_packet_not_dict"]
    if (
        str(artifact.get("artifact_type") or "")
        != "accurate_intake_websearch_exact_card_manifest_review_packet_v1"
    ):
        return ["unsupported_manifest_review_packet_artifact"]
    blockers: list[str] = []
    if artifact.get("status") != "pass_manifest_review_packet":
        blockers.append(f"manifest_review_packet_not_pass:{artifact.get('status')}")
    blockers.extend(
        blocker
        for key, blocker in _FORBIDDEN_TRUE_FLAGS.items()
        if _has_dirty_flag(artifact, key)
    )
    if artifact.get("next_required_slice") != _EXPECTED_NEXT_SLICE:
        blockers.append("manifest_review_packet_next_slice_not_no_runtime_wall")
    raw_summary = artifact.get("summary")
    if not isinstance(raw_summary, dict):
        blockers.append("manifest_review_packet_summary_malformed")
        summary: dict[str, Any] = {}
    else:
        summary = raw_summary
    blockers.extend(
        _count_blocker(
            summary,
            "runtime_truth_allowed_count",
            "manifest_review_packet_runtime_truth_allowed_count",
        )
    )
    blockers.extend(
        _count_blocker(
            summary,
            "exact_card_created_count",
            "manifest_review_packet_exact_card_created_count",
        )
    )
    blockers.extend(
        _count_blocker(
            summary,
            "promotion_allowed_count",
            "manifest_review_packet_promotion_allowed_count",
        )
    )
    raw_packets = artifact.get("review_packets")
    if not isinstance(raw_packets, list):
        blockers.append("review_packets_not_list")
    elif any(not isinstance(packet, dict) for packet in raw_packets):
        blockers.append("review_packet_malformed")
    metadata = {key: value for key, value in artifact.items() if key != "review_packets"}
    blockers.extend(
        _recursive_unsafe_blockers(metadata, prefix="manifest_review_packet_nested")
    )
    return blockers


def _review_packets(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        packet for packet in artifact.get("review_packets") or [] if isinstance(packet, dict)
    ]


def _review_packet_blockers(packets: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for packet in packets:
        if packet.get("packet_type") != "ExactCardManifestReviewPacket":
            blockers.append("review_packet_type_not_manifest_review")
        if packet.get("packet_role") != "review_only_exact_card_manifest_candidate":
            blockers.append("review_packet_role_not_review_only")
        if packet.get("truth_level") != "review_candidate":
            blockers.append("review_packet_truth_level_not_candidate")
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
        blockers.extend(
            _recursive_unsafe_blockers(packet, prefix="review_packet_nested")
        )
    return sorted(set(blockers))


def _wall_record(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "wall_record_id": _record_id(packet),
        "wall_role": "manifest_candidate_runtime_truth_stop",
        "source_review_packet_id": packet.get("packet_id"),
        "source_manifest_candidate_id": packet.get("source_manifest_candidate_id"),
        "source_request_candidate_id": packet.get("source_request_candidate_id"),
        "runtime_truth_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "promotion_allowed": False,
        "exact_card_created": False,
        "runtime_mutation_allowed": False,
        "raw_content_included": False,
        "raw_source_rows_included": False,
        "manager_visible_role": "no_runtime_wall_only_not_manager_truth",
        "required_before_runtime_truth": [
            "exact_card_record_creation_contract_probe",
            "exact_card_record_creation_slice",
            "exact_card_runtime_gate",
            "packetizer_contract_review",
        ],
    }


def _wall_record_blockers(records: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for record in records:
        if record.get("runtime_truth_allowed") is not False:
            blockers.append("wall_record_allowed_runtime_truth")
        if record.get("websearch_runtime_truth_allowed") is not False:
            blockers.append("wall_record_allowed_websearch_runtime_truth")
        if record.get("packet_ready_truth_allowed") is not False:
            blockers.append("wall_record_allowed_packet_ready_truth")
        if record.get("promotion_allowed") is not False:
            blockers.append("wall_record_allowed_promotion")
        if record.get("exact_card_created") is not False:
            blockers.append("wall_record_created_exact_card")
        if record.get("runtime_mutation_allowed") is not False:
            blockers.append("wall_record_allowed_runtime_mutation")
        if record.get("raw_content_included") is not False:
            blockers.append("wall_record_included_raw_content")
        if record.get("raw_source_rows_included") is not False:
            blockers.append("wall_record_included_raw_source_rows")
    return sorted(set(blockers))


def _has_dirty_flag(container: dict[str, Any], key: str) -> bool:
    return key in container and container.get(key) is not False


def _count_blocker(summary: dict[str, Any], key: str, blocker_prefix: str) -> list[str]:
    if key not in summary:
        return [f"{blocker_prefix}_malformed"]
    count = summary[key]
    if isinstance(count, bool) or not isinstance(count, int):
        return [f"{blocker_prefix}_malformed"]
    if count != 0:
        return [f"{blocker_prefix}_nonzero"]
    return []


def _recursive_unsafe_blockers(value: object, *, prefix: str) -> list[str]:
    blockers: list[str] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if key in _UNSAFE_NESTED_FLAGS and nested_value is not False:
                blockers.append(f"{prefix}_{key}")
            blockers.extend(_recursive_unsafe_blockers(nested_value, prefix=prefix))
    elif isinstance(value, list):
        for item in value:
            blockers.extend(_recursive_unsafe_blockers(item, prefix=prefix))
    return blockers


def _safe_artifact_type(artifact: object) -> str:
    if not isinstance(artifact, dict):
        return "<non_dict>"
    value = artifact.get("artifact_type")
    if isinstance(value, str):
        return value
    return "<non_scalar>"


def _record_id(packet: dict[str, Any]) -> str:
    seed = "|".join(
        str(packet.get(key) or "")
        for key in ("packet_id", "source_manifest_candidate_id", "source_request_candidate_id")
    )
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"wall_exact_card_manifest_no_runtime_{digest}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_exact_card_manifest_no_runtime_wall"]
