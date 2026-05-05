from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


_EXPECTED_WALL_STATUS = "blocked_pending_exact_card_approval_policy"
_EXPECTED_WALL_BLOCKER = "exact_card_runtime_approval_policy_missing"
_EXPECTED_NEXT_SLICE = "define_exact_card_runtime_promotion_policy_or_stop"
_NEXT_SLICE = "websearch_exact_card_runtime_promotion_candidate_manifest"

_ELIGIBLE_SOURCE_CLASSES = ["official_brand_chain_page"]
_BLOCKED_SOURCE_CLASSES = [
    "open_food_facts",
    "usda_fallback",
    "old_base_db",
    "dogfood_user_correction",
    "generic_web_snippet",
]
_REQUIRED_CONFIRMATIONS = [
    "official_or_brand_owned_source",
    "exact_identity_variant_match",
    "serving_basis_confirmation",
    "kcal_value_confirmation",
    "source_license_confirmation",
    "explicit_item_or_batch_approval_id",
    "exact_card_runtime_gate",
]

_FORBIDDEN_TRUE_FLAGS = {
    "runtime_truth_changed": "approval_wall_changed_runtime_truth",
    "mutation_changed": "approval_wall_changed_mutation",
    "runtime_mutation_allowed": "approval_wall_allowed_runtime_mutation",
    "websearch_runtime_truth_allowed": "approval_wall_allowed_websearch_runtime_truth",
    "runtime_web_activation_approved": "approval_wall_approved_runtime_web_activation",
    "runtime_web_activation_recommended": (
        "approval_wall_recommended_runtime_web_activation"
    ),
    "approval_allowed_by_this_wall": "approval_wall_allowed_approval",
    "packet_ready_truth_allowed": "approval_wall_allowed_packet_ready_truth",
    "promotion_allowed": "approval_wall_allowed_promotion",
    "ready_for_runtime_truth": "approval_wall_claimed_ready_for_runtime_truth",
    "ready_for_runtime_mutation": "approval_wall_claimed_ready_for_runtime_mutation",
    "readiness_claimed": "approval_wall_claimed_readiness",
    "shared_contract_changed": "approval_wall_changed_shared_contract",
    "manager_context_changed": "approval_wall_changed_manager_context",
    "manager_context_packet_changed": "approval_wall_changed_manager_context_packet",
    "manager_context_packet_schema_changed": (
        "approval_wall_changed_manager_context_packet_schema"
    ),
    "packetizer_format_changed": "approval_wall_changed_packetizer_format",
    "packetizer_changed": "approval_wall_changed_packetizer",
    "basket_semantics_changed": "approval_wall_changed_basket_semantics",
    "nutrition_evidence_store_port_changed": (
        "approval_wall_changed_nutrition_evidence_store_port"
    ),
    "live_provider_used": "approval_wall_used_live_provider",
    "live_websearch_used": "approval_wall_used_live_websearch",
    "source_live_websearch_used": "approval_wall_used_source_live_websearch",
    "exact_card_created": "approval_wall_created_exact_card",
    "raw_content_included": "approval_wall_included_raw_content",
    "raw_source_rows_included": "approval_wall_included_raw_source_rows",
}

_UNSAFE_NESTED_FLAGS = (
    "runtime_truth_changed",
    "mutation_changed",
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


def build_websearch_exact_card_runtime_promotion_policy(
    *,
    exact_card_approval_wall: dict[str, Any],
) -> dict[str, Any]:
    blockers = _approval_wall_blockers(exact_card_approval_wall)
    wall_records = [] if blockers else _wall_records(exact_card_approval_wall)
    blockers.extend(_wall_record_blockers(wall_records))
    if not wall_records and not blockers:
        blockers.append("exact_card_approval_wall_record_missing")
    clear = not blockers
    return {
        "artifact_type": (
            "accurate_intake_websearch_exact_card_runtime_promotion_policy_v1"
        ),
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_exact_card_runtime_promotion_policy_only",
        "claim_scope": "websearch_exact_card_runtime_promotion_policy_without_truth",
        "status": "policy_defined_no_runtime_truth" if clear else "blocked",
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
        "promotion_allowed_by_this_artifact": False,
        "source_artifacts": {
            "exact_card_approval_wall_type": exact_card_approval_wall.get(
                "artifact_type"
            ),
        },
        "runtime_promotion_policy": _runtime_promotion_policy(),
        "summary": {
            "approval_wall_record_count": len(wall_records),
            "runtime_truth_allowed_count": 0,
            "exact_card_created_count": 0,
            "promotion_allowed_count": 0,
        },
        "next_required_slice": (
            _NEXT_SLICE
            if clear
            else "inspect_exact_card_runtime_promotion_policy_blockers"
        ),
        "non_claims": [
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_runtime_web_activation",
            "no_readiness_claim",
        ],
    }


def evaluate_websearch_exact_card_runtime_promotion_request(
    *,
    policy_artifact: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    if (
        policy_artifact.get("artifact_type")
        != "accurate_intake_websearch_exact_card_runtime_promotion_policy_v1"
    ):
        blockers.append("unsupported_policy_artifact")
    if policy_artifact.get("status") != "policy_defined_no_runtime_truth":
        blockers.append(f"policy_not_defined:{policy_artifact.get('status')}")
    if policy_artifact.get("promotion_allowed_by_this_artifact") is not False:
        blockers.append("policy_artifact_allowed_promotion")
    if policy_artifact.get("exact_card_created") is not False:
        blockers.append("policy_artifact_created_exact_card")
    if policy_artifact.get("runtime_truth_changed") is not False:
        blockers.append("policy_artifact_changed_runtime_truth")
    blockers.extend(_policy_artifact_dirty_blockers(policy_artifact))
    blockers.extend(_request_dirty_blockers(request))

    requested_transition = str(request.get("requested_transition") or "")
    if requested_transition != "review_packet_to_exact_card_manifest_candidate":
        blockers.append("unsupported_transition_for_policy_artifact")

    source_class = str(request.get("source_class") or "")
    if source_class not in _ELIGIBLE_SOURCE_CLASSES:
        blockers.append("source_class_not_allowed_for_exact_card_runtime_policy")
    if source_class in _BLOCKED_SOURCE_CLASSES:
        blockers.append("source_class_explicitly_blocked_for_exact_card_runtime_policy")

    required_flags = {
        "official_or_brand_owned_source": "official_or_brand_owned_source_required",
        "exact_identity_variant_match": "exact_identity_variant_match_required",
        "serving_basis_confirmed": "serving_basis_confirmation_required",
        "kcal_value_confirmed": "kcal_value_confirmation_required",
        "source_license_confirmed": "source_license_confirmation_required",
    }
    for key, blocker in required_flags.items():
        if request.get(key) is not True:
            blockers.append(blocker)
    if not str(request.get("approval_id") or "").strip():
        blockers.append("explicit_item_or_batch_approval_id_required")

    return {
        "candidate_id": request.get("candidate_id"),
        "requested_transition": requested_transition,
        "source_class": source_class,
        "policy_allows_future_manifest_entry": not blockers,
        "promotion_allowed_by_policy_artifact": False,
        "runtime_truth_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "exact_card_created": False,
        "runtime_mutation_allowed": False,
        "blockers": sorted(set(blockers)),
        "next_required_slice": (
            "websearch_exact_card_runtime_promotion_candidate_manifest"
            if not blockers
            else "inspect_exact_card_runtime_promotion_request_blockers"
        ),
    }


def _policy_artifact_dirty_blockers(policy_artifact: dict[str, Any]) -> list[str]:
    key_blockers = {
        "runtime_truth_changed": "policy_artifact_changed_runtime_truth",
        "mutation_changed": "policy_artifact_changed_mutation",
        "runtime_mutation_allowed": "policy_artifact_allowed_runtime_mutation",
        "websearch_runtime_truth_allowed": "policy_artifact_allowed_websearch_runtime_truth",
        "runtime_web_activation_approved": (
            "policy_artifact_approved_runtime_web_activation"
        ),
        "runtime_web_activation_recommended": (
            "policy_artifact_recommended_runtime_web_activation"
        ),
        "live_websearch_used": "policy_artifact_used_live_websearch",
        "source_live_websearch_used": "policy_artifact_used_source_live_websearch",
        "live_provider_used": "policy_artifact_used_live_provider",
        "ready_for_runtime_truth": "policy_artifact_claimed_ready_for_runtime_truth",
        "ready_for_runtime_mutation": (
            "policy_artifact_claimed_ready_for_runtime_mutation"
        ),
        "readiness_claimed": "policy_artifact_claimed_readiness",
        "shared_contract_changed": "policy_artifact_changed_shared_contract",
        "manager_context_changed": "policy_artifact_changed_manager_context",
        "packetizer_format_changed": "policy_artifact_changed_packetizer_format",
        "raw_content_included": "policy_artifact_included_raw_content",
        "raw_source_rows_included": "policy_artifact_included_raw_source_rows",
    }
    blockers = [
        blocker
        for key, blocker in key_blockers.items()
        if _has_dirty_flag(policy_artifact, key)
    ]
    blockers.extend(
        _recursive_unsafe_blockers(
            policy_artifact,
            prefix="policy_artifact_nested",
        )
    )
    return blockers


def _request_dirty_blockers(request: dict[str, Any]) -> list[str]:
    key_blockers = {
        "runtime_truth_changed": "request_changed_runtime_truth",
        "mutation_changed": "request_changed_mutation",
        "runtime_truth_allowed": "request_allowed_runtime_truth",
        "websearch_runtime_truth_allowed": "request_allowed_websearch_runtime_truth",
        "packet_ready_truth_allowed": "request_allowed_packet_ready_truth",
        "promotion_allowed": "request_allowed_promotion",
        "promotion_allowed_by_this_artifact": "request_allowed_artifact_promotion",
        "approval_allowed_by_this_wall": "request_allowed_wall_approval",
        "approval_allowed_by_this_packet": "request_allowed_packet_approval",
        "exact_card_created": "request_created_exact_card",
        "runtime_mutation_allowed": "request_allowed_runtime_mutation",
        "runtime_web_activation_approved": "request_approved_runtime_web_activation",
        "runtime_web_activation_recommended": (
            "request_recommended_runtime_web_activation"
        ),
        "live_websearch_used": "request_used_live_websearch",
        "source_live_websearch_used": "request_used_source_live_websearch",
        "live_provider_used": "request_used_live_provider",
        "ready_for_runtime_truth": "request_claimed_ready_for_runtime_truth",
        "ready_for_runtime_mutation": "request_claimed_ready_for_runtime_mutation",
        "readiness_claimed": "request_claimed_readiness",
        "raw_content_included": "request_included_raw_content",
        "raw_source_rows_included": "request_included_raw_source_rows",
        "shared_contract_changed": "request_changed_shared_contract",
        "manager_context_changed": "request_changed_manager_context",
        "packetizer_format_changed": "request_changed_packetizer_format",
    }
    blockers = [
        blocker for key, blocker in key_blockers.items() if _has_dirty_flag(request, key)
    ]
    blockers.extend(_recursive_unsafe_blockers(request, prefix="request_nested"))
    return blockers


def _approval_wall_blockers(wall: dict[str, Any]) -> list[str]:
    if (
        str(wall.get("artifact_type") or "")
        != "accurate_intake_websearch_exact_card_candidate_approval_wall_v1"
    ):
        raise ValueError("unsupported_exact_card_runtime_policy_approval_wall")
    blockers: list[str] = []
    if wall.get("status") != _EXPECTED_WALL_STATUS:
        blockers.append(f"approval_wall_not_pending_policy:{wall.get('status')}")
    if _EXPECTED_WALL_BLOCKER not in list(wall.get("blockers") or []):
        blockers.append("approval_wall_missing_policy_blocker")
    blockers.extend(
        blocker
        for key, blocker in _FORBIDDEN_TRUE_FLAGS.items()
        if _has_dirty_flag(wall, key)
    )
    if wall.get("next_required_slice") != _EXPECTED_NEXT_SLICE:
        blockers.append("approval_wall_next_slice_not_policy_definition")
    summary = wall.get("summary") if isinstance(wall.get("summary"), dict) else {}
    if int(summary.get("runtime_truth_allowed_count") or 0) != 0:
        blockers.append("approval_wall_runtime_truth_allowed_count_nonzero")
    if int(summary.get("exact_card_created_count") or 0) != 0:
        blockers.append("approval_wall_exact_card_created_count_nonzero")
    if int(summary.get("promotion_allowed_count") or 0) != 0:
        blockers.append("approval_wall_promotion_allowed_count_nonzero")
    records = wall.get("approval_wall_records")
    if not isinstance(records, list):
        blockers.append("approval_wall_records_not_list")
    elif any(not isinstance(record, dict) for record in records):
        blockers.append("approval_wall_record_malformed")
    wall_metadata = {
        key: value for key, value in wall.items() if key != "approval_wall_records"
    }
    blockers.extend(
        _recursive_unsafe_blockers(
            wall_metadata,
            prefix="approval_wall_nested",
        )
    )
    return blockers


def _wall_records(wall: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        record
        for record in wall.get("approval_wall_records") or []
        if isinstance(record, dict)
    ]


def _wall_record_blockers(records: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for record in records:
        if record.get("approval_wall_role") != "exact_card_runtime_truth_stop_gate":
            blockers.append("approval_wall_record_role_not_runtime_truth_stop_gate")
        if record.get("approval_status") != _EXPECTED_WALL_STATUS:
            blockers.append("approval_wall_record_status_not_pending_policy")
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
        blockers.extend(
            _recursive_unsafe_blockers(
                record,
                prefix="approval_wall_record_nested",
            )
        )
    return sorted(set(blockers))


def _runtime_promotion_policy() -> dict[str, Any]:
    return {
        "policy_status": "defined_for_future_manifest_candidates_only",
        "eligible_source_classes": list(_ELIGIBLE_SOURCE_CLASSES),
        "blocked_source_classes": list(_BLOCKED_SOURCE_CLASSES),
        "required_confirmations": list(_REQUIRED_CONFIRMATIONS),
        "allowed_transition": "review_packet_to_exact_card_manifest_candidate",
        "forbidden_transition": "direct_exact_card_runtime_truth_creation",
        "this_artifact_can_create_exact_card": False,
        "this_artifact_can_create_runtime_truth": False,
        "this_artifact_can_mutate_ledger": False,
    }


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


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "build_websearch_exact_card_runtime_promotion_policy",
    "evaluate_websearch_exact_card_runtime_promotion_request",
]
