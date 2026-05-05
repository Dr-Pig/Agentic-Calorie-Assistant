from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from typing import Any


_EXPECTED_NEXT_SLICE = "websearch_exact_card_candidate_approval_wall"
_PENDING_POLICY_BLOCKER = "exact_card_runtime_approval_policy_missing"

_FORBIDDEN_TRUE_FLAGS = {
    "runtime_truth_changed": "review_refresh_changed_runtime_truth",
    "mutation_changed": "review_refresh_changed_mutation",
    "runtime_mutation_allowed": "review_refresh_allowed_runtime_mutation",
    "websearch_runtime_truth_allowed": "review_refresh_allowed_websearch_runtime_truth",
    "runtime_web_activation_approved": "review_refresh_approved_runtime_web_activation",
    "runtime_web_activation_recommended": (
        "review_refresh_recommended_runtime_web_activation"
    ),
    "approval_allowed_by_this_packet": "review_refresh_allowed_approval",
    "approval_allowed_by_this_wall": "review_refresh_allowed_wall_approval",
    "packet_ready_truth_allowed": "review_refresh_allowed_packet_ready_truth",
    "promotion_allowed": "review_refresh_allowed_promotion",
    "ready_for_runtime_truth": "review_refresh_claimed_ready_for_runtime_truth",
    "ready_for_runtime_mutation": "review_refresh_claimed_ready_for_runtime_mutation",
    "readiness_claimed": "review_refresh_claimed_readiness",
    "shared_contract_changed": "review_refresh_changed_shared_contract",
    "manager_context_changed": "review_refresh_changed_manager_context",
    "manager_context_packet_changed": "review_refresh_changed_manager_context_packet",
    "manager_context_packet_schema_changed": (
        "review_refresh_changed_manager_context_packet_schema"
    ),
    "packetizer_format_changed": "review_refresh_changed_packetizer_format",
    "packetizer_changed": "review_refresh_changed_packetizer",
    "basket_semantics_changed": "review_refresh_changed_basket_semantics",
    "nutrition_evidence_store_port_changed": (
        "review_refresh_changed_nutrition_evidence_store_port"
    ),
    "live_provider_used": "review_refresh_used_live_provider",
    "live_websearch_used": "review_refresh_used_live_websearch",
    "source_live_websearch_used": "review_refresh_used_source_live_websearch",
    "exact_card_created": "review_refresh_created_exact_card",
    "product_loop_activated": "review_refresh_activated_product_loop",
    "product_loop_integration_claimed": (
        "review_refresh_claimed_product_loop_integration"
    ),
    "ce_activated": "review_refresh_activated_context_engineering",
    "context_engineering_changed": "review_refresh_changed_context_engineering",
    "webshell_activated": "review_refresh_activated_webshell",
    "webshell_changed": "review_refresh_changed_webshell",
    "raw_content_included": "review_refresh_included_raw_content",
    "raw_source_rows_included": "review_refresh_included_raw_source_rows",
}

_UNSAFE_NESTED_FLAGS = (
    "runtime_truth_allowed",
    "websearch_runtime_truth_allowed",
    "packet_ready_truth_allowed",
    "promotion_allowed",
    "approval_allowed_by_this_packet",
    "approval_allowed_by_this_wall",
    "exact_card_created",
    "runtime_mutation_allowed",
    "raw_content_included",
    "raw_source_rows_included",
    "shared_contract_changed",
    "manager_context_changed",
    "manager_context_packet_changed",
    "manager_context_packet_schema_changed",
    "packetizer_format_changed",
    "packetizer_changed",
    "basket_semantics_changed",
    "nutrition_evidence_store_port_changed",
)


def build_websearch_exact_card_candidate_approval_wall(
    *,
    exact_card_review_packet_refresh: dict[str, Any],
) -> dict[str, Any]:
    blockers = _review_refresh_blockers(exact_card_review_packet_refresh)
    review_packets = [] if blockers else _review_packets(exact_card_review_packet_refresh)
    blockers.extend(_review_packet_blockers(review_packets))
    wall_records = [] if blockers else [_wall_record(packet) for packet in review_packets]
    blockers.extend(_wall_record_blockers(wall_records))
    if not wall_records and not blockers:
        blockers.append("approval_wall_review_packet_missing")
    if wall_records and not blockers:
        blockers.append(_PENDING_POLICY_BLOCKER)
    pending_policy = blockers == [_PENDING_POLICY_BLOCKER]
    return {
        "artifact_type": (
            "accurate_intake_websearch_exact_card_candidate_approval_wall_v1"
        ),
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_exact_card_approval_wall_only",
        "claim_scope": "websearch_exact_card_approval_wall_without_truth_promotion",
        "status": (
            "blocked_pending_exact_card_approval_policy"
            if pending_policy
            else "blocked"
        ),
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
        "approval_allowed_by_this_wall": False,
        "source_artifacts": {
            "exact_card_review_packet_refresh_type": (
                exact_card_review_packet_refresh.get("artifact_type")
            ),
        },
        "approval_wall_records": wall_records,
        "summary": {
            "review_packet_count": len(review_packets),
            "approval_wall_record_count": len(wall_records),
            "runtime_truth_allowed_count": sum(
                1 for record in wall_records if record["runtime_truth_allowed"] is True
            ),
            "exact_card_created_count": sum(
                1 for record in wall_records if record["exact_card_created"] is True
            ),
            "promotion_allowed_count": sum(
                1 for record in wall_records if record["promotion_allowed"] is True
            ),
        },
        "approval_boundary": {
            "approval_wall_can_create_exact_card": False,
            "approval_wall_can_create_runtime_truth": False,
            "approval_wall_can_mutate_ledger": False,
            "required_before_runtime_truth": (
                "explicit_exact_card_runtime_promotion_policy"
            ),
        },
        "next_required_slice": (
            "define_exact_card_runtime_promotion_policy_or_stop"
            if pending_policy
            else "inspect_exact_card_approval_wall_blockers"
        ),
        "non_claims": [
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_runtime_web_activation",
            "no_readiness_claim",
        ],
    }


def _review_refresh_blockers(refresh: dict[str, Any]) -> list[str]:
    if (
        str(refresh.get("artifact_type") or "")
        != "accurate_intake_websearch_exact_card_review_packet_refresh_v1"
    ):
        raise ValueError("unsupported_exact_card_approval_wall_review_refresh")
    blockers: list[str] = []
    if refresh.get("status") != "pass":
        blockers.append(f"review_packet_refresh_not_pass:{refresh.get('status')}")
    blockers.extend(
        blocker
        for key, blocker in _FORBIDDEN_TRUE_FLAGS.items()
        if _has_dirty_flag(refresh, key)
    )
    if refresh.get("next_required_slice") != _EXPECTED_NEXT_SLICE:
        blockers.append("review_refresh_next_slice_not_approval_wall")
    summary = refresh.get("summary") if isinstance(refresh.get("summary"), dict) else {}
    if int(summary.get("runtime_truth_allowed_count") or 0) != 0:
        blockers.append("review_refresh_runtime_truth_allowed_count_nonzero")
    if int(summary.get("exact_card_created_count") or 0) != 0:
        blockers.append("review_refresh_exact_card_created_count_nonzero")
    if int(summary.get("approval_allowed_count") or 0) != 0:
        blockers.append("review_refresh_approval_allowed_count_nonzero")
    if int(summary.get("promotion_allowed_count") or 0) != 0:
        blockers.append("review_refresh_promotion_allowed_count_nonzero")
    raw_packets = refresh.get("review_packets")
    if not isinstance(raw_packets, list):
        blockers.append("review_refresh_review_packets_not_list")
    elif any(not isinstance(packet, dict) for packet in raw_packets):
        blockers.append("review_refresh_review_packet_malformed")
    refresh_metadata = {key: value for key, value in refresh.items() if key != "review_packets"}
    blockers.extend(
        _recursive_unsafe_blockers(
            refresh_metadata,
            prefix="review_refresh_nested",
        )
    )
    return blockers


def _review_packets(refresh: dict[str, Any]) -> list[dict[str, Any]]:
    return [packet for packet in refresh.get("review_packets") or [] if isinstance(packet, dict)]


def _review_packet_blockers(packets: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for packet in packets:
        if packet.get("packet_type") != "ExactCardReviewPacketRefresh":
            blockers.append("review_packet_type_not_refresh")
        if packet.get("packet_role") != "review_only_exact_card_candidate":
            blockers.append("review_packet_role_not_review_only")
        if packet.get("truth_level") != "review_candidate":
            blockers.append("review_packet_truth_level_not_candidate")
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
        if not str(packet.get("packet_id") or "").strip():
            blockers.append("review_packet_missing_packet_id")
        if not isinstance(packet.get("approval_checklist"), dict):
            blockers.append("review_packet_missing_approval_checklist")
        if not isinstance(packet.get("review_fields"), dict):
            blockers.append("review_packet_missing_review_fields")
        blockers.extend(_nested_blockers(packet))
        blockers.extend(_recursive_unsafe_blockers(packet, prefix="review_packet_nested"))
    return sorted(set(blockers))


def _nested_blockers(packet: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    nested_prefixes = {
        "approval_metadata": "review_packet_approval",
        "approval_checklist": "review_packet_checklist",
        "review_fields": "review_packet_review_fields",
        "evidence_basis": "review_packet_evidence_basis",
    }
    for section, prefix in nested_prefixes.items():
        value = packet.get(section) if isinstance(packet.get(section), dict) else {}
        if section == "approval_metadata" and value.get("runtime_truth_allowed") is not False:
            blockers.append("review_packet_approval_allowed_runtime_truth")
        for key in _UNSAFE_NESTED_FLAGS:
            if _has_dirty_flag(value, key):
                blockers.append(f"{prefix}_{key}")
    return blockers


def _has_dirty_flag(container: dict[str, Any], key: str) -> bool:
    return key in container and container.get(key) is not False


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


def _wall_record(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "approval_wall_record_id": _record_id(packet),
        "approval_wall_role": "exact_card_runtime_truth_stop_gate",
        "approval_status": "blocked_pending_exact_card_approval_policy",
        "source_review_packet_id": packet.get("packet_id"),
        "source_plan_candidate_id": packet.get("source_plan_candidate_id"),
        "source_post_extract_status": packet.get("source_post_extract_status"),
        "source_extract_report_status": packet.get("source_extract_report_status"),
        "review_fields_required": {
            "exact_identity_variant_match_required": True,
            "serving_basis_confirmation_required": True,
            "kcal_value_confirmation_required": True,
            "source_license_confirmation_required": True,
        },
        "approval_metadata": {
            "approval_mode": "none",
            "approval_scope": "exact_card_candidate_approval_wall_only",
            "policy_version": "websearch_exact_card_candidate_approval_wall_v1",
            "runtime_truth_allowed": False,
        },
        "runtime_truth_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "promotion_allowed": False,
        "approval_allowed_by_this_wall": False,
        "exact_card_created": False,
        "runtime_mutation_allowed": False,
        "raw_content_included": False,
        "raw_source_rows_included": False,
        "manager_visible_role": "approval_wall_only_not_manager_truth",
        "required_before_runtime_truth": [
            "exact_identity_variant_match",
            "serving_basis_confirmation",
            "kcal_value_confirmation",
            "source_license_confirmation",
            "explicit_exact_card_runtime_promotion_policy",
            "exact_card_runtime_gate",
        ],
    }


def _wall_record_blockers(records: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for record in records:
        if record.get("runtime_truth_allowed") is not False:
            blockers.append("approval_wall_record_allowed_runtime_truth")
        if record.get("websearch_runtime_truth_allowed") is not False:
            blockers.append("approval_wall_record_allowed_websearch_runtime_truth")
        if record.get("packet_ready_truth_allowed") is not False:
            blockers.append("approval_wall_record_allowed_packet_ready_truth")
        if record.get("promotion_allowed") is not False:
            blockers.append("approval_wall_record_allowed_promotion")
        if record.get("approval_allowed_by_this_wall") is not False:
            blockers.append("approval_wall_record_allowed_approval")
        if record.get("exact_card_created") is not False:
            blockers.append("approval_wall_record_created_exact_card")
        if record.get("runtime_mutation_allowed") is not False:
            blockers.append("approval_wall_record_allowed_runtime_mutation")
        if record.get("raw_content_included") is not False:
            blockers.append("approval_wall_record_included_raw_content")
        if record.get("raw_source_rows_included") is not False:
            blockers.append("approval_wall_record_included_raw_source_rows")
    return sorted(set(blockers))


def _record_id(packet: dict[str, Any]) -> str:
    seed = str(packet.get("packet_id") or "")
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"wall_exact_card_approval_{digest}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_exact_card_candidate_approval_wall"]
