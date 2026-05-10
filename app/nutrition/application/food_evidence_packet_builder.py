from __future__ import annotations

from typing import Any


_COMPACT_PACKET_FORBIDDEN_KEYS = frozenset(
    {
        "candidate_only_records",
        "full_fooddb",
        "full_fooddb_dump",
        "raw_payload",
        "raw_row",
        "raw_row_hash",
        "raw_rows",
        "raw_source_payload",
        "raw_source_record",
        "raw_source_records",
        "raw_source_row",
        "raw_source_rows",
        "row_index",
        "source_record",
    }
)


def build_food_evidence_recall_packet(
    *,
    packet_id: str,
    raw_user_input: str,
    retrieval_result: dict[str, Any],
    manager_expected_behavior: str | None = None,
    packet_type: str = "food_evidence_recall_packet_v1",
) -> dict[str, Any]:
    evidence_items = [
        _compact_candidate(item) for item in retrieval_result.get("accepted_candidates") or []
    ]
    packet = {
        "packet_type": packet_type,
        "packet_id": packet_id,
        "raw_user_input": raw_user_input,
        "retrieval_scope": retrieval_result.get("retrieval_scope"),
        "retrieval_boundary": retrieval_result.get("retrieval_boundary"),
        "runtime_mutation_allowed": False,
        "truth_selection_forbidden": True,
        "raw_source_rows_included": False,
        "candidate_only_records_included": False,
        "full_fooddb_included": False,
        "modifier_hints": (retrieval_result.get("normalized_query") or {}).get("modifier_hints") or {},
        "candidate_terms": (retrieval_result.get("normalized_query") or {}).get("candidate_terms") or [],
        "evidence_items": evidence_items,
        "rejected_candidate_count": len(retrieval_result.get("rejected_candidates") or []),
        "ambiguity_reason": retrieval_result.get("ambiguity_reason"),
        "followup_hints": list(retrieval_result.get("followup_hints") or []),
        "vector_search_policy": retrieval_result.get("vector_search_policy"),
        "ranking_policy": retrieval_result.get("ranking_policy"),
        "manager_may_use_for": [
            "grounded_food_evidence",
            "macro_visibility_honesty",
            "followup_or_uncertainty_decision",
            "disambiguation",
        ],
        "manager_must_not_use_for": [
            "runtime_mutation",
            "creating_fooddb_truth",
            "inventing_source",
            "inventing_macro",
        ],
    }
    if manager_expected_behavior is not None:
        packet["manager_expected_behavior"] = manager_expected_behavior
    return packet


def is_compact_food_evidence_packet(packet: dict[str, Any]) -> bool:
    return (
        packet.get("raw_source_rows_included") is False
        and packet.get("candidate_only_records_included") is False
        and packet.get("full_fooddb_included") is False
        and not _contains_forbidden_compact_key(packet)
    )


def _compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "anchor_id": candidate.get("anchor_id"),
        "canonical_name": candidate.get("canonical_name"),
        "query_component": candidate.get("query_component"),
        "match_path": candidate.get("match_path"),
        "confidence": candidate.get("confidence"),
        "requires_manager_disambiguation": candidate.get("requires_manager_disambiguation"),
        "runtime_role": candidate.get("runtime_role"),
        "source_lane": candidate.get("source_lane"),
        "runtime_truth_allowed": candidate.get("runtime_truth_allowed"),
        "kcal_point": candidate.get("kcal_point"),
        "kcal_range": candidate.get("kcal_range"),
        "protein_g": candidate.get("protein_g"),
        "carbs_g": candidate.get("carbs_g"),
        "fat_g": candidate.get("fat_g"),
        "macro_visibility_status": candidate.get("macro_visibility_status"),
        "macro_source_basis": candidate.get("macro_source_basis"),
        "macro_confidence": candidate.get("macro_confidence"),
        "serving_basis": candidate.get("serving_basis"),
        "portion_basis": candidate.get("portion_basis"),
        "runtime_usage_boundary": candidate.get("runtime_usage_boundary"),
        "followup_hints": list(candidate.get("followup_hints") or []),
        "source_provenance": _compact_source_provenance(candidate.get("source_provenance")),
        "approval_metadata": _compact_approval_metadata(candidate.get("approval_metadata")),
        "modifier_compatibility": dict(candidate.get("modifier_compatibility") or {}),
        "ranking_reasons": list(candidate.get("ranking_reasons") or []),
    }


def _compact_source_provenance(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    allowed_keys = ("source_id", "source_file", "source_url")
    return {key: source.get(key) for key in allowed_keys if source.get(key) is not None}


def _compact_approval_metadata(value: Any) -> dict[str, Any]:
    approval = value if isinstance(value, dict) else {}
    allowed_keys = (
        "approval_mode",
        "approval_scope",
        "policy_version",
        "runtime_truth_allowed",
    )
    return {key: approval.get(key) for key in allowed_keys if key in approval}


def _contains_forbidden_compact_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key in _COMPACT_PACKET_FORBIDDEN_KEYS or _contains_forbidden_compact_key(child)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_compact_key(item) for item in value)
    return False


__all__ = [
    "build_food_evidence_recall_packet",
    "is_compact_food_evidence_packet",
]
