from __future__ import annotations

from copy import deepcopy
from typing import Any, Sequence

from .food_evidence_packet_builder import is_compact_food_evidence_packet

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

_SEARCH_CANDIDATE_TRUTH_FIELD_DENYLIST = frozenset(
    {
        "accepted_usage",
        "exactness_posture",
        "final_kcal",
        "final_truth",
        "kcal_range",
        "ledger_mutation_result",
        "likely_kcal",
        "primary_source",
        "runtime_truth_allowed",
    }
)

_ADAPTER_BACKEND_FIELD_DENYLIST = frozenset(
    {
        "adapter",
        "adapter_kind",
        "backend",
        "dependency_inversion",
        "external_search",
        "index_adapter",
        "local_json",
        "search_provider",
        "source_implementation",
        "storage_backend",
        "supabase",
    }
)

_SEARCH_CANDIDATE_MANAGER_VISIBLE_KEYS = frozenset(
    {
        "packet_id",
        "packet_type",
        "truth_level",
        "source_type",
        "source_quality_label",
        "source_class_hint",
        "raw_ref",
        "title",
        "truth_level",
        "url",
        "snippet",
        "tavily_score",
        "query",
        "officialness_hint",
        "license_status",
        "robots_status",
        "identity_confidence",
        "nutrition_fields_present",
        "matched_terms",
        "matched_name",
        "canonical_name",
        "match_type",
        "brand_match",
        "size_or_serving_match",
        "modifier_match",
        "serving_basis",
        "serving_basis_candidate",
        "sibling_variant_risk",
    }
)

_MANAGER_VISIBLE_TRACE_CONTEXT_KEYS = frozenset(
    {
        "live_provider_used",
        "live_websearch_used",
        "packet_artifact_type",
        "packet_claim_scope",
        "websearch_runtime_truth_allowed",
    }
)


def build_tool_evidence_result(
    *,
    tool_name: str,
    tool_call_id: str,
    evidence_packets: Sequence[dict[str, Any]],
    index_adapter: dict[str, Any] | None = None,
    trace_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packets = [deepcopy(packet) for packet in evidence_packets]
    _raise_if_non_compact(packets)
    manager_visible_packets = [_manager_visible_packet(packet) for packet in packets]

    return {
        "result_type": "tool_evidence_result_v1",
        "tool_name": tool_name,
        "tool_call_id": tool_call_id,
        "result_boundary": "read_only_evidence_packet_result",
        "runtime_mutation_allowed": False,
        "runtime_truth_changed": False,
        "manager_context_changed": False,
        "read_model_only": True,
        "source_implementation_visible": False,
        "evidence_packets": manager_visible_packets,
        "trace": {
            **_manager_visible_trace_context(trace_context),
            "packet_count": len(packets),
            "compact_packet_pass_count": len(packets),
            "raw_source_rows_included": False,
            "candidate_only_records_included": False,
            "full_fooddb_included": False,
            "source_implementation_manager_visible": False,
        },
        "manager_may_use_for": [
            "grounded_food_evidence",
            "followup_or_uncertainty_decision",
            "disambiguation",
        ],
        "manager_must_not_use_for": [
            "runtime_mutation",
            "creating_fooddb_truth",
            "inventing_source",
            "inferring_source_implementation",
        ],
    }


def _raise_if_non_compact(packets: Sequence[dict[str, Any]]) -> None:
    for index, packet in enumerate(packets):
        if not _has_required_packet_shape(packet):
            packet_id = str(packet.get("packet_id") or packet.get("case_id") or index)
            raise ValueError(f"malformed_evidence_packet:{packet_id}")
        if not _is_compact_packet(packet):
            packet_id = str(packet.get("packet_id") or packet.get("case_id") or index)
            raise ValueError(f"non_compact_evidence_packet:{packet_id}")


def _has_required_packet_shape(packet: dict[str, Any]) -> bool:
    packet_type = str(packet.get("packet_type") or "").strip()
    if packet_type == "SearchCandidatePacket":
        return _has_required_search_candidate_shape(packet)

    packet_id = str(packet.get("packet_id") or packet.get("case_id") or "").strip()
    evidence_items = packet.get("evidence_items")
    required_fields = (
        "raw_user_input",
        "retrieval_scope",
        "retrieval_boundary",
        "runtime_mutation_allowed",
        "truth_selection_forbidden",
        "raw_source_rows_included",
        "candidate_only_records_included",
        "full_fooddb_included",
        "manager_may_use_for",
        "manager_must_not_use_for",
    )
    has_required_fields = all(key in packet for key in required_fields)
    return (
        packet_type in {"food_evidence_recall_packet_v1", "fooddb_manager_evidence_packet_v1"}
        and bool(packet_id)
        and isinstance(evidence_items, list)
        and has_required_fields
        and packet.get("runtime_mutation_allowed") is False
        and packet.get("truth_selection_forbidden") is True
    )


def _has_required_search_candidate_shape(packet: dict[str, Any]) -> bool:
    packet_id = str(packet.get("packet_id") or "").strip()
    truth_level = str(packet.get("truth_level") or "").strip()
    source_type = str(packet.get("source_type") or "").strip()
    required_fields = (
        "packet_id",
        "raw_ref",
        "source_quality_label",
        "title",
        "url",
        "snippet",
        "query",
        "matched_name",
        "canonical_name",
        "match_type",
        "brand_match",
        "size_or_serving_match",
        "modifier_match",
        "serving_basis",
        "sibling_variant_risk",
    )
    return (
        bool(packet_id)
        and truth_level == "candidate"
        and source_type == "web_search"
        and all(key in packet for key in required_fields)
        and set(packet).issubset(_SEARCH_CANDIDATE_MANAGER_VISIBLE_KEYS)
        and not _contains_forbidden_manager_visible_content(packet)
    )


def _manager_visible_packet(packet: dict[str, Any]) -> dict[str, Any]:
    if str(packet.get("packet_type") or "").strip() == "SearchCandidatePacket":
        return {key: deepcopy(packet[key]) for key in _SEARCH_CANDIDATE_MANAGER_VISIBLE_KEYS if key in packet}
    return deepcopy(packet)


def _manager_visible_trace_context(trace_context: dict[str, Any] | None) -> dict[str, Any]:
    trace = dict(trace_context or {})
    if _contains_forbidden_manager_visible_content(trace):
        raise ValueError("forbidden_trace_context")
    return {key: deepcopy(trace[key]) for key in _MANAGER_VISIBLE_TRACE_CONTEXT_KEYS if key in trace}


def _is_compact_packet(packet: dict[str, Any]) -> bool:
    packet_type = str(packet.get("packet_type") or "").strip()
    if packet_type == "SearchCandidatePacket":
        return not _contains_forbidden_manager_visible_content(packet)
    return is_compact_food_evidence_packet(packet)


def _contains_forbidden_manager_visible_content(value: Any) -> bool:
    forbidden_keys = (
        _COMPACT_PACKET_FORBIDDEN_KEYS
        | _SEARCH_CANDIDATE_TRUTH_FIELD_DENYLIST
        | _ADAPTER_BACKEND_FIELD_DENYLIST
    )
    return _contains_forbidden_content(value, forbidden_keys=forbidden_keys)


def _contains_forbidden_content(value: Any, *, forbidden_keys: frozenset[str]) -> bool:
    return _contains_forbidden_content_at_depth(value, forbidden_keys=forbidden_keys, depth=0)


def _contains_forbidden_content_at_depth(
    value: Any,
    *,
    forbidden_keys: frozenset[str],
    depth: int,
) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden_keys:
                return True
            # SearchCandidatePacket owns a single top-level truth_level=candidate.
            # Nested truth_level fields are truth assertions, not evidence metadata.
            if key == "truth_level" and (depth > 0 or child != "candidate"):
                return True
            if _contains_forbidden_content_at_depth(
                child,
                forbidden_keys=forbidden_keys,
                depth=depth + 1,
            ):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(
            _contains_forbidden_content_at_depth(item, forbidden_keys=forbidden_keys, depth=depth)
            for item in value
        )
    if isinstance(value, str):
        normalized = value.strip().lower()
        return any(token in normalized for token in forbidden_keys)
    return False


def _contains_forbidden_compact_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key in _COMPACT_PACKET_FORBIDDEN_KEYS or _contains_forbidden_compact_key(child)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_compact_key(item) for item in value)
    return False


__all__ = ["build_tool_evidence_result"]
