from __future__ import annotations

from typing import Any

from .fooddb_websearch_no_runtime_wall_key_families import (
    approved_fooddb_common_serving_anchor,
    candidate_truth_key_forbidden,
    context_or_schema_change_key_forbidden,
    contract_or_format_change_key_forbidden,
    live_usage_key_forbidden,
    metadata_key_allowed,
    mutation_key_forbidden,
    path_is_candidate_lane,
    product_loop_key_forbidden,
    promotion_key_forbidden,
    readiness_key_forbidden,
    runtime_truth_key_forbidden,
    source_blocker_family_key,
)

FORBIDDEN_TRUE_KEYS = frozenset(
    {
        "approval_allowed_by_this_packet",
        "exact_card_created",
        "exact_card_creation_allowed",
        "live_extract_used",
        "live_provider_used",
        "live_websearch_used",
        "manager_context_changed",
        "manager_context_packet_changed",
        "mutation_changed",
        "packet_ready_truth_allowed",
        "packetizer_format_changed",
        "private_self_use_approved",
        "product_readiness_claimed",
        "production_selected",
        "promotion_allowed",
        "raw_content_allowed_in_manager_context",
        "raw_content_included",
        "raw_source_rows_included",
        "readiness_claimed",
        "runtime_mutation_allowed",
        "runtime_mutation_attempted",
        "runtime_truth_changed",
        "selected_extract_truth_allowed",
        "self_use_approved",
        "shared_contract_changed",
        "snippet_truth_allowed",
        "websearch_runtime_truth_allowed",
    }
)


def truthy_key_forbidden(
    key: str,
    path: str,
    *,
    artifact_type: str,
    parent: dict[str, Any],
) -> bool:
    lowered = key.lower()
    if lowered == "runtime_truth_allowed" and path.endswith(".approval_metadata.runtime_truth_allowed"):
        return path_is_candidate_lane(f"{artifact_type}.{path}")
    if metadata_key_allowed(lowered):
        return False
    if lowered in FORBIDDEN_TRUE_KEYS:
        return True
    if lowered == "runtime_truth_allowed":
        return not (
            approved_fooddb_common_serving_anchor(parent)
            and not path_is_candidate_lane(f"{artifact_type}.{path}")
        )
    candidate_context = path_is_candidate_lane(f"{artifact_type}.{path}")
    return (
        runtime_truth_key_forbidden(lowered)
        or candidate_truth_key_forbidden(lowered, path, candidate_context=candidate_context)
        or mutation_key_forbidden(lowered)
        or live_usage_key_forbidden(lowered)
        or promotion_key_forbidden(lowered)
        or readiness_key_forbidden(lowered)
        or context_or_schema_change_key_forbidden(lowered)
        or contract_or_format_change_key_forbidden(lowered)
        or product_loop_key_forbidden(lowered)
        or source_blocker_family_key(lowered)
    )


def count_key_forbidden(key: str, value: Any, path: str) -> bool:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return False
    if value <= 0:
        return False
    lowered = key.lower()
    if lowered == "runtime_truth_allowed_count":
        return path_is_candidate_lane(path)
    return any(
        marker in lowered
        for marker in (
            "exact_card_created",
            "blocker_count",
            "blockers_count",
            "invocation_count",
            "leak_count",
            "live_provider_used",
            "live_websearch_used",
            "mutation_allowed",
            "mutation_attempted",
            "promotion_allowed",
            "readiness_claimed",
            "ready_for_runtime_truth",
            "runtime_mutation",
            "runtime_truth",
            "runtime_truth_changed",
            "selected_extract_truth_allowed",
            "self_use_approved",
            "snippet_truth_allowed",
            "violation_count",
            "violations_count",
            "websearch_runtime_truth",
        )
    )


def value_is_claim_signal(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float) and not isinstance(value, bool):
        return value > 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized or normalized in {"0", "false", "no", "none", "null", "not_used"}:
            return False
        return not any(token in normalized for token in ("false", "no", "none", "not", "null"))
    if isinstance(value, list | dict):
        return bool(value)
    return False


def status_is_blocked(key: str, value: Any, path: str) -> bool:
    if key.lower() != "status" or path != "$.status":
        return False
    status = str(value).strip().lower()
    return bool(status and status not in {"pass", "passed"})


def blocker_list_is_non_empty(key: str, value: Any) -> bool:
    lowered = key.lower()
    if not (
        lowered == "blockers"
        or lowered == "violations"
        or "blocker" in lowered
        or "leak" in lowered
        or "violation" in lowered
        or lowered.endswith("_blockers")
        or lowered.endswith("_violations")
    ):
        return False
    return (
        (isinstance(value, list) and bool(value))
        or (isinstance(value, dict) and bool(value))
        or value_is_claim_signal(value)
    )


__all__ = [
    "FORBIDDEN_TRUE_KEYS",
    "blocker_list_is_non_empty",
    "count_key_forbidden",
    "status_is_blocked",
    "truthy_key_forbidden",
    "value_is_claim_signal",
]
