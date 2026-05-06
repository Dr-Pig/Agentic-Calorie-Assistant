from __future__ import annotations

from typing import Any

from .tool_evidence_result import build_tool_evidence_result


def build_compact_fooddb_live_projection(*, packet_case: dict[str, Any]) -> dict[str, Any]:
    packet = dict(packet_case.get("manager_evidence_packet") or {})
    compact_packet = _compact_fooddb_packet(packet)
    allowed_refs = sorted(_allowed_refs_for_packet_case(packet_case=packet_case, packet=compact_packet))
    tool_result = _compact_tool_evidence_result(
        packet_case=packet_case,
        compact_packet=compact_packet,
        original_tool_result=packet_case.get("tool_evidence_result"),
    )
    return {
        "fooddb_evidence_packet": compact_packet,
        "tool_evidence_result": tool_result,
        "tool_results": [
            {
                "tool_name": tool_result.get("tool_name") or "lookup_food_evidence",
                "tool_call_id": tool_result.get("tool_call_id"),
                "result_boundary": tool_result.get("result_boundary"),
                "runtime_mutation_allowed": tool_result.get("runtime_mutation_allowed") is True,
                "truth_level": "read_only_food_evidence_result",
                "output_ref": "tool_evidence_result",
            }
        ],
        "allowed_evidence_refs": allowed_refs,
    }


def _compact_fooddb_packet(packet: dict[str, Any]) -> dict[str, Any]:
    evidence_items = packet.get("evidence_items") if isinstance(packet.get("evidence_items"), list) else []
    return {
        "packet_type": packet.get("packet_type"),
        "packet_id": packet.get("packet_id"),
        "case_id": packet.get("case_id"),
        "raw_user_input": packet.get("raw_user_input"),
        "retrieval_scope": packet.get("retrieval_scope"),
        "retrieval_boundary": packet.get("retrieval_boundary"),
        "runtime_mutation_allowed": False,
        "truth_selection_forbidden": True,
        "raw_source_rows_included": False,
        "candidate_only_records_included": False,
        "full_fooddb_included": False,
        "modifier_hints": dict(packet.get("modifier_hints") or {}),
        "followup_hints": list(packet.get("followup_hints") or []),
        "ambiguity_reason": packet.get("ambiguity_reason"),
        "manager_expected_behavior": packet.get("manager_expected_behavior"),
        "manager_may_use_for": list(packet.get("manager_may_use_for") or []),
        "manager_must_not_use_for": list(packet.get("manager_must_not_use_for") or []),
        "evidence_items": [_compact_evidence_item(item) for item in evidence_items if isinstance(item, dict)],
    }


def _compact_evidence_item(item: dict[str, Any]) -> dict[str, Any]:
    portion_basis = item.get("portion_basis") if isinstance(item.get("portion_basis"), dict) else {}
    source = item.get("source_provenance") if isinstance(item.get("source_provenance"), dict) else {}
    approval = item.get("approval_metadata") if isinstance(item.get("approval_metadata"), dict) else {}
    compact_item = {
        "anchor_id": item.get("anchor_id"),
        "canonical_name": item.get("canonical_name"),
        "confidence": item.get("confidence"),
        "runtime_truth_allowed": item.get("runtime_truth_allowed") is True,
        "kcal_point": item.get("kcal_point"),
        "kcal_range": item.get("kcal_range"),
        "serving_basis": item.get("serving_basis"),
        "portion_basis": {
            "portion_unit": portion_basis.get("portion_unit"),
            "portion_quantity": portion_basis.get("portion_quantity"),
            "label": portion_basis.get("label"),
        },
        "runtime_usage_boundary": item.get("runtime_usage_boundary"),
        "followup_hints": list(item.get("followup_hints") or []),
        "modifier_compatibility": dict(item.get("modifier_compatibility") or {}),
        "source_provenance": {
            "source_id": source.get("source_id"),
        },
        "approval_metadata": {
            "runtime_truth_allowed": approval.get("runtime_truth_allowed") is True,
        },
    }
    if compact_item["modifier_compatibility"] or _has_packet_adjusted_values(item):
        compact_item["packet_adjustment_available"] = _has_packet_adjusted_values(item)
    modifier_adjustment_authority = str(item.get("modifier_adjustment_authority") or "").strip()
    if modifier_adjustment_authority:
        compact_item["modifier_adjustment_authority"] = modifier_adjustment_authority
    if item.get("adjusted_kcal_point") is not None:
        compact_item["adjusted_kcal_point"] = item.get("adjusted_kcal_point")
    if item.get("adjusted_kcal_range") is not None:
        compact_item["adjusted_kcal_range"] = item.get("adjusted_kcal_range")
    return {key: value for key, value in compact_item.items() if value not in (None, {}, [])}


def _has_packet_adjusted_values(item: dict[str, Any]) -> bool:
    return item.get("adjusted_kcal_point") is not None or item.get("adjusted_kcal_range") is not None


def _compact_tool_evidence_result(
    *,
    packet_case: dict[str, Any],
    compact_packet: dict[str, Any],
    original_tool_result: Any,
) -> dict[str, Any]:
    tool_name = "lookup_food_evidence"
    tool_call_id = f"fooddb-packet-{packet_case.get('case_id')}"
    trace_context: dict[str, Any] | None = None
    if isinstance(original_tool_result, dict):
        tool_name = str(original_tool_result.get("tool_name") or tool_name)
        tool_call_id = str(original_tool_result.get("tool_call_id") or tool_call_id)
        trace_context = dict(original_tool_result.get("trace") or {})
    return build_tool_evidence_result(
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        evidence_packets=[compact_packet],
        trace_context=trace_context,
    )


def _allowed_refs_for_packet_case(*, packet_case: dict[str, Any], packet: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    case_id = str(packet_case.get("case_id") or packet.get("case_id") or "").strip()
    if case_id:
        refs.add(case_id)
        refs.add(f"fooddb_packet case_id {case_id}")
    for item in packet.get("evidence_items") or []:
        if not isinstance(item, dict):
            continue
        for key in ("anchor_id", "canonical_name"):
            value = str(item.get(key) or "").strip()
            if value:
                refs.add(value)
    return refs


def build_diagnostic_allowed_evidence_refs(*, packet_case: dict[str, Any], evidence_items: list[Any]) -> set[str]:
    refs: set[str] = set()
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        for key in ("anchor_id", "canonical_name"):
            value = str(item.get(key) or "").strip()
            if value:
                refs.add(value)
        source = item.get("source_provenance") if isinstance(item.get("source_provenance"), dict) else {}
        source_id = str(source.get("source_id") or "").strip()
        if source_id:
            refs.add(source_id)
        source_file = str(source.get("source_file") or "").strip()
        if source_file:
            refs.add(source_file)
        approval = item.get("approval_metadata") if isinstance(item.get("approval_metadata"), dict) else {}
        policy_version = str(approval.get("policy_version") or "").strip()
        if policy_version:
            refs.add(policy_version)
        portion_basis = item.get("portion_basis") if isinstance(item.get("portion_basis"), dict) else {}
        for ref in portion_basis.get("derived_from") or []:
            value = str(ref or "").strip()
            if value:
                refs.add(value)
    case_id = str(packet_case.get("case_id") or "").strip()
    if case_id:
        refs.add(case_id)
        refs.add(f"fooddb_packet case_id {case_id}")
    return refs


__all__ = ["build_compact_fooddb_live_projection", "build_diagnostic_allowed_evidence_refs"]
