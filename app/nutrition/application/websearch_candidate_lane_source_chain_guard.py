from __future__ import annotations

from typing import Any

from .websearch_candidate_lane_handoff_proof import (
    handoff_probe_case_count,
    safe_count_map,
    safe_non_negative_int,
)


def source_chain_blockers(
    *,
    contract_probe_artifact: dict[str, Any],
    repair_pack_artifact: dict[str, Any],
    manager_contract_handoff_artifact: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    blockers.extend(
        _source_artifact_boundary_blockers(
            artifact=contract_probe_artifact,
            prefix="contract_probe",
        )
    )
    blockers.extend(
        _source_artifact_boundary_blockers(
            artifact=repair_pack_artifact,
            prefix="repair_pack",
        )
    )
    blockers.extend(
        _unblocked_repair_pack_summary_blockers(
            repair_pack_artifact=repair_pack_artifact,
        )
    )
    blockers.extend(
        _probe_case_evidence_blockers(
            contract_probe_artifact=contract_probe_artifact,
            expected_case_count=handoff_probe_case_count(manager_contract_handoff_artifact),
        )
    )
    blockers.extend(
        _repair_pack_case_evidence_blockers(
            repair_pack_artifact=repair_pack_artifact,
        )
    )
    return blockers


def _source_artifact_boundary_blockers(
    *,
    artifact: dict[str, Any],
    prefix: str,
) -> list[str]:
    blockers: list[str] = []
    for key, suffix in (
        ("readiness_claimed", "claimed_readiness"),
        ("runtime_truth_changed", "changed_runtime_truth"),
        ("runtime_mutation_attempted", "attempted_runtime_mutation"),
        ("mutation_changed", "changed_mutation"),
        ("prompt_changed", "changed_prompt"),
        ("schema_changed", "changed_schema"),
        ("manager_contract_changed", "changed_manager_contract"),
        ("shared_contract_changed", "changed_shared_contract"),
        ("manager_context_changed", "changed_manager_context"),
        ("packetizer_format_changed", "changed_packetizer_format"),
        ("live_provider_used", "used_live_provider"),
        ("live_websearch_used", "used_live_websearch"),
        ("self_use_approved", "claimed_self_use"),
        ("private_self_use_approved", "claimed_private_self_use"),
        ("production_selected", "claimed_production_selection"),
        ("product_readiness_claimed", "claimed_product_readiness"),
    ):
        if key in artifact and artifact.get(key) is not False:
            blockers.append(f"{prefix}_{suffix}")
    return blockers


def _probe_case_evidence_blockers(
    *,
    contract_probe_artifact: dict[str, Any],
    expected_case_count: int,
) -> list[str]:
    cases = contract_probe_artifact.get("cases")
    if not isinstance(cases, list) or not cases:
        return ["manager_contract_handoff_probe_cases_missing"]
    blockers: list[str] = []
    if len(cases) != expected_case_count:
        blockers.append("manager_contract_handoff_probe_case_count_mismatch")
    for case in cases:
        if not isinstance(case, dict):
            blockers.append("manager_contract_handoff_probe_case_not_object")
            continue
        if case.get("status") != "pass":
            blockers.append("manager_contract_handoff_probe_case_not_pass")
        if case.get("failure_families") not in ([], None):
            blockers.append("manager_contract_handoff_probe_case_failure_present")
        if case.get("raw_manager_output_included") is not False:
            blockers.append("manager_contract_handoff_probe_case_raw_output_included")
        if case.get("provider_trace_included") is not False:
            blockers.append("manager_contract_handoff_probe_case_provider_trace_included")
    return blockers


def _unblocked_repair_pack_summary_blockers(
    *,
    repair_pack_artifact: dict[str, Any],
) -> list[str]:
    summary = repair_pack_artifact.get("summary")
    if not isinstance(summary, dict):
        return ["repair_pack_summary_missing_for_unblocked_handoff"]
    blockers: list[str] = []
    if safe_count_map(summary.get("aggregate_missing_required_fields")):
        blockers.append("repair_pack_non_empty_missing_field_map_for_unblocked_handoff")
    if safe_count_map(summary.get("alias_hint_counts")):
        blockers.append("repair_pack_non_empty_alias_hint_map_for_unblocked_handoff")
    if safe_count_map(summary.get("shape_pattern_counts")):
        blockers.append("repair_pack_non_empty_shape_pattern_map_for_unblocked_handoff")
    return blockers


def _repair_pack_case_evidence_blockers(
    *,
    repair_pack_artifact: dict[str, Any],
) -> list[str]:
    summary = repair_pack_artifact.get("summary")
    if not isinstance(summary, dict):
        return []
    case_count = safe_non_negative_int(summary.get("case_count"))
    if case_count == 0:
        return []
    cases = repair_pack_artifact.get("cases")
    if not isinstance(cases, list) or len(cases) != case_count:
        return ["repair_pack_case_count_mismatch_for_unblocked_handoff"]
    blockers: list[str] = []
    for case in cases:
        if not isinstance(case, dict):
            blockers.append("repair_pack_case_not_object_for_unblocked_handoff")
            continue
        if case.get("status") != "pass":
            blockers.append("repair_pack_non_pass_case_for_unblocked_handoff")
        if case.get("failure_families") not in ([], None):
            blockers.append("repair_pack_failure_case_for_unblocked_handoff")
        if case.get("missing_required_fields") not in ([], None):
            blockers.append("repair_pack_missing_fields_for_unblocked_handoff")
        if case.get("shape_patterns") not in ([], None):
            blockers.append("repair_pack_shape_patterns_for_unblocked_handoff")
    return blockers


__all__ = ["source_chain_blockers"]
