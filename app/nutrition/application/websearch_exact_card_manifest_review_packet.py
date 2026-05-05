from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from typing import Any


_EXPECTED_NEXT_SLICE = "websearch_exact_card_manifest_candidate_review_packet"

_FORBIDDEN_TRUE_FLAGS = {
    "runtime_truth_changed": "manifest_diagnostic_changed_runtime_truth",
    "mutation_changed": "manifest_diagnostic_changed_mutation",
    "runtime_mutation_allowed": "manifest_diagnostic_allowed_runtime_mutation",
    "websearch_runtime_truth_allowed": (
        "manifest_diagnostic_allowed_websearch_runtime_truth"
    ),
    "runtime_web_activation_approved": (
        "manifest_diagnostic_approved_runtime_web_activation"
    ),
    "runtime_web_activation_recommended": (
        "manifest_diagnostic_recommended_runtime_web_activation"
    ),
    "live_provider_used": "manifest_diagnostic_used_live_provider",
    "live_websearch_used": "manifest_diagnostic_used_live_websearch",
    "source_live_websearch_used": "manifest_diagnostic_used_source_live_websearch",
    "exact_card_created": "manifest_diagnostic_created_exact_card",
    "readiness_claimed": "manifest_diagnostic_claimed_readiness",
    "ready_for_runtime_truth": "manifest_diagnostic_claimed_ready_for_runtime_truth",
    "ready_for_runtime_mutation": (
        "manifest_diagnostic_claimed_ready_for_runtime_mutation"
    ),
    "shared_contract_changed": "manifest_diagnostic_changed_shared_contract",
    "manager_context_changed": "manifest_diagnostic_changed_manager_context",
    "packetizer_format_changed": "manifest_diagnostic_changed_packetizer_format",
    "raw_content_included": "manifest_diagnostic_included_raw_content",
    "raw_source_rows_included": "manifest_diagnostic_included_raw_source_rows",
}

_UNSAFE_NESTED_FLAGS = (
    "runtime_truth_changed",
    "mutation_changed",
    "raw_content",
    "raw_source_rows",
    "readiness_payload",
    "readiness",
    "runtime_truth_allowed",
    "websearch_runtime_truth_allowed",
    "packet_ready_truth_allowed",
    "promotion_allowed",
    "approval_allowed_by_this_wall",
    "approval_allowed_by_this_packet",
    "promotion_allowed_by_this_artifact",
    "exact_card_created",
    "runtime_mutation_allowed",
    "raw_content_included",
    "raw_source_rows_included",
    "runtime_web_activation_approved",
    "runtime_web_activation_recommended",
    "live_websearch_used",
    "source_live_websearch_used",
    "live_provider_used",
    "ready_for_runtime_truth",
    "ready_for_runtime_mutation",
    "readiness_claimed",
    "shared_contract_changed",
    "manager_context_changed",
    "manager_context_packet_changed",
    "manager_context_packet_schema_changed",
    "packetizer_format_changed",
    "packetizer_changed",
    "basket_semantics_changed",
    "nutrition_evidence_store_port_changed",
)


def build_websearch_exact_card_manifest_review_packet(
    *,
    manifest_diagnostic: dict[str, Any],
) -> dict[str, Any]:
    blockers = _manifest_diagnostic_blockers(manifest_diagnostic)
    candidates = [] if blockers else _manifest_candidates(manifest_diagnostic)
    blockers.extend(_manifest_candidate_blockers(candidates))
    review_packets = [] if blockers else [_review_packet(candidate) for candidate in candidates]
    blockers.extend(_review_packet_blockers(review_packets))
    if not review_packets and not blockers:
        blockers.append("manifest_review_packet_candidate_missing")
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_websearch_exact_card_manifest_review_packet_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_exact_card_manifest_review_packet_only",
        "claim_scope": "websearch_exact_card_manifest_review_packet_without_truth",
        "status": "pass_manifest_review_packet" if clear else "blocked",
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
            "manifest_diagnostic_type": _safe_artifact_type(manifest_diagnostic),
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
            "promotion_allowed_count": sum(
                1 for packet in review_packets if packet["promotion_allowed"] is True
            ),
        },
        "next_required_slice": (
            "websearch_exact_card_manifest_no_runtime_wall"
            if clear
            else "inspect_websearch_exact_card_manifest_review_packet_blockers"
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


def _manifest_diagnostic_blockers(manifest: dict[str, Any]) -> list[str]:
    if not isinstance(manifest, dict):
        return ["manifest_diagnostic_not_dict"]
    if (
        str(manifest.get("artifact_type") or "")
        != "accurate_intake_websearch_exact_card_candidate_manifest_diagnostic_v1"
    ):
        return ["unsupported_manifest_diagnostic_artifact"]
    blockers: list[str] = []
    if manifest.get("status") != "pass_candidate_manifest_diagnostic":
        blockers.append(f"manifest_diagnostic_not_pass:{manifest.get('status')}")
    blockers.extend(
        blocker
        for key, blocker in _FORBIDDEN_TRUE_FLAGS.items()
        if _has_dirty_flag(manifest, key)
    )
    if manifest.get("next_required_slice") != _EXPECTED_NEXT_SLICE:
        blockers.append("manifest_diagnostic_next_slice_not_review_packet")
    summary = manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {}
    blockers.extend(
        _count_blocker(
            summary,
            "runtime_truth_allowed_count",
            "manifest_diagnostic_runtime_truth_allowed_count",
        )
    )
    blockers.extend(
        _count_blocker(
            summary,
            "exact_card_created_count",
            "manifest_diagnostic_exact_card_created_count",
        )
    )
    blockers.extend(
        _count_blocker(
            summary,
            "promotion_allowed_count",
            "manifest_diagnostic_promotion_allowed_count",
        )
    )
    raw_candidates = manifest.get("manifest_candidates")
    if not isinstance(raw_candidates, list):
        blockers.append("manifest_candidates_not_list")
    elif any(not isinstance(candidate, dict) for candidate in raw_candidates):
        blockers.append("manifest_candidate_malformed")
    metadata = {
        key: value for key, value in manifest.items() if key != "manifest_candidates"
    }
    blockers.extend(
        _recursive_unsafe_blockers(metadata, prefix="manifest_diagnostic_nested")
    )
    return blockers


def _manifest_candidates(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        candidate
        for candidate in manifest.get("manifest_candidates") or []
        if isinstance(candidate, dict)
    ]


def _manifest_candidate_blockers(candidates: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for candidate in candidates:
        if candidate.get("candidate_role") != "exact_card_manifest_candidate_only":
            blockers.append("manifest_candidate_role_not_candidate_only")
        if candidate.get("truth_level") != "manifest_candidate":
            blockers.append("manifest_candidate_truth_level_not_manifest_candidate")
        if candidate.get("runtime_truth_allowed") is not False:
            blockers.append("manifest_candidate_allowed_runtime_truth")
        if candidate.get("websearch_runtime_truth_allowed") is not False:
            blockers.append("manifest_candidate_allowed_websearch_runtime_truth")
        if candidate.get("packet_ready_truth_allowed") is not False:
            blockers.append("manifest_candidate_allowed_packet_ready_truth")
        if candidate.get("promotion_allowed") is not False:
            blockers.append("manifest_candidate_allowed_promotion")
        if candidate.get("exact_card_created") is not False:
            blockers.append("manifest_candidate_created_exact_card")
        if candidate.get("runtime_mutation_allowed") is not False:
            blockers.append("manifest_candidate_allowed_runtime_mutation")
        if candidate.get("raw_content_included") is not False:
            blockers.append("manifest_candidate_included_raw_content")
        if candidate.get("raw_source_rows_included") is not False:
            blockers.append("manifest_candidate_included_raw_source_rows")
        blockers.extend(
            _recursive_unsafe_blockers(
                candidate,
                prefix="manifest_candidate_nested",
            )
        )
    return sorted(set(blockers))


def _safe_artifact_type(manifest: object) -> str:
    if not isinstance(manifest, dict):
        return "<non_dict>"
    value = manifest.get("artifact_type")
    if isinstance(value, str):
        return value
    return "<non_scalar>"


def _review_packet(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_id": _packet_id(candidate),
        "packet_type": "ExactCardManifestReviewPacket",
        "packet_role": "review_only_exact_card_manifest_candidate",
        "truth_level": "review_candidate",
        "source_type": "websearch_exact_card_manifest_candidate",
        "source_manifest_candidate_id": candidate.get("manifest_candidate_id"),
        "source_request_candidate_id": candidate.get("source_request_candidate_id"),
        "source_class": candidate.get("source_class"),
        "approval_id": candidate.get("approval_id"),
        "approval_checklist": {
            "exact_card_record_creation_slice_required": True,
            "exact_card_runtime_gate_required": True,
            "packetizer_contract_review_required": True,
        },
        "runtime_truth_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "promotion_allowed": False,
        "exact_card_created": False,
        "runtime_mutation_allowed": False,
        "raw_content_included": False,
        "raw_source_rows_included": False,
        "manager_visible_role": "manifest_review_packet_only_not_manager_truth",
    }


def _review_packet_blockers(packets: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for packet in packets:
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
    return sorted(set(blockers))


def _has_dirty_flag(container: dict[str, Any], key: str) -> bool:
    return key in container and container.get(key) is not False


def _count_blocker(summary: dict[str, Any], key: str, blocker_prefix: str) -> list[str]:
    try:
        count = int(summary.get(key) or 0)
    except (TypeError, ValueError):
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


def _packet_id(candidate: dict[str, Any]) -> str:
    seed = "|".join(
        str(candidate.get(key) or "")
        for key in ("manifest_candidate_id", "source_request_candidate_id", "approval_id")
    )
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"pkt_exact_card_manifest_review_{digest}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_exact_card_manifest_review_packet"]
