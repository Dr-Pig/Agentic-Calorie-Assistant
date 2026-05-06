from __future__ import annotations

from typing import Any


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
                "truth_level": "read_only_food_evidence_result",
                "output": tool_result,
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
        "runtime_mutation_allowed": False,
        "truth_selection_forbidden": True,
        "modifier_hints": dict(packet.get("modifier_hints") or {}),
        "followup_hints": list(packet.get("followup_hints") or []),
        "ambiguity_reason": packet.get("ambiguity_reason"),
        "manager_expected_behavior": packet.get("manager_expected_behavior"),
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
        "modifier_compatibility": _project_modifier_compatibility(item),
        "source_provenance": {
            "source_id": source.get("source_id"),
        },
        "approval_metadata": {
            "runtime_truth_allowed": approval.get("runtime_truth_allowed") is True,
        },
    }
    modifier_adjustment_authority = _project_modifier_adjustment_authority(item)
    if modifier_adjustment_authority:
        compact_item["modifier_adjustment_authority"] = modifier_adjustment_authority
    if item.get("adjusted_kcal_point") is not None:
        compact_item["adjusted_kcal_point"] = item.get("adjusted_kcal_point")
    if item.get("adjusted_kcal_range") is not None:
        compact_item["adjusted_kcal_range"] = item.get("adjusted_kcal_range")
    return {key: value for key, value in compact_item.items() if value not in (None, {}, [])}


def _project_modifier_compatibility(item: dict[str, Any]) -> dict[str, Any]:
    compatibility = item.get("modifier_compatibility")
    if not isinstance(compatibility, dict) or not compatibility:
        return {}
    if _has_packet_adjusted_values(item):
        return dict(compatibility)
    return {
        str(key): "followup_only_no_kcal_adjustment"
        for key, value in compatibility.items()
        if str(key).strip() and value is not None
    }


def _project_modifier_adjustment_authority(item: dict[str, Any]) -> str | None:
    if _has_packet_adjusted_values(item):
        return str(item.get("modifier_adjustment_authority") or "packet_authorized").strip() or None
    compatibility = item.get("modifier_compatibility")
    if isinstance(compatibility, dict) and compatibility:
        return "packet_adjustment_absent_followup_only"
    return None


def _has_packet_adjusted_values(item: dict[str, Any]) -> bool:
    return item.get("adjusted_kcal_point") is not None or item.get("adjusted_kcal_range") is not None


def _compact_tool_evidence_result(
    *,
    packet_case: dict[str, Any],
    compact_packet: dict[str, Any],
    original_tool_result: Any,
) -> dict[str, Any]:
    if isinstance(original_tool_result, dict):
        trace = dict(original_tool_result.get("trace") or {})
        trace["packet_count"] = 1
        trace["compact_packet_pass_count"] = 1
        compact = {
            "result_type": original_tool_result.get("result_type") or "tool_evidence_result_v1",
            "tool_name": original_tool_result.get("tool_name") or "lookup_food_evidence",
            "tool_call_id": original_tool_result.get("tool_call_id")
            or f"fooddb-packet-{packet_case.get('case_id')}",
            "result_boundary": original_tool_result.get("result_boundary")
            or "read_only_evidence_packet_result",
            "runtime_mutation_allowed": False,
            "runtime_truth_changed": False,
            "manager_context_changed": False,
            "read_model_only": True,
            "source_implementation_visible": False,
            "evidence_packets": [compact_packet],
            "trace": trace,
        }
        return compact
    return {
        "result_type": "tool_evidence_result_v1",
        "tool_name": "lookup_food_evidence",
        "tool_call_id": f"fooddb-packet-{packet_case.get('case_id')}",
        "result_boundary": "read_only_evidence_packet_result",
        "runtime_mutation_allowed": False,
        "runtime_truth_changed": False,
        "manager_context_changed": False,
        "read_model_only": True,
        "source_implementation_visible": False,
        "evidence_packets": [compact_packet],
        "trace": {
            "packet_count": 1,
            "compact_packet_pass_count": 1,
            "source_implementation_manager_visible": False,
        },
    }


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
