from __future__ import annotations

from typing import Any

from .websearch_candidate_lane_handoff_proof import (
    handoff_probe_case_count,
    safe_count_map,
    safe_non_negative_int,
)
from .websearch_candidate_lane_source_artifact_guard import (
    source_artifact_boundary_blockers,
)


def source_chain_blockers(
    *,
    live_diagnostic_report: dict[str, Any],
    contract_probe_artifact: dict[str, Any],
    repair_pack_artifact: dict[str, Any],
    preflight_artifact: dict[str, Any],
    manager_contract_handoff_artifact: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    blockers.extend(
        source_artifact_boundary_blockers(
            live_diagnostic_report=live_diagnostic_report,
            contract_probe_artifact=contract_probe_artifact,
            repair_pack_artifact=repair_pack_artifact,
            preflight_artifact=preflight_artifact,
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
        if "failure_families" not in case or case.get("failure_families") is None:
            blockers.append("manager_contract_handoff_probe_case_failure_families_missing")
        elif case.get("failure_families") != []:
            blockers.append("manager_contract_handoff_probe_case_failure_present")
        if not str(case.get("case_id") or "").strip():
            blockers.append("manager_contract_handoff_probe_case_id_missing")
        missing_fields = case.get("missing_required_fields")
        if missing_fields != []:
            blockers.append("manager_contract_handoff_probe_case_missing_required_fields_missing")
        shape_patterns = case.get("shape_patterns")
        if shape_patterns != []:
            blockers.append("manager_contract_handoff_probe_case_shape_patterns_missing")
        observed_keys = case.get("observed_keys")
        if not isinstance(observed_keys, list) or not observed_keys:
            blockers.append("manager_contract_handoff_probe_case_observed_keys_missing")
        if "validation_error_family" not in case:
            blockers.append("manager_contract_handoff_probe_case_validation_family_missing")
        elif case.get("validation_error_family") is not None:
            blockers.append("manager_contract_handoff_probe_case_validation_family_present")
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
    if "aggregate_missing_required_fields" not in summary or not isinstance(
        summary.get("aggregate_missing_required_fields"), dict
    ):
        blockers.append("repair_pack_missing_clean_missing_field_map_for_unblocked_handoff")
    elif safe_count_map(summary.get("aggregate_missing_required_fields")):
        blockers.append("repair_pack_non_empty_missing_field_map_for_unblocked_handoff")
    if "alias_hint_counts" not in summary or not isinstance(
        summary.get("alias_hint_counts"), dict
    ):
        blockers.append("repair_pack_missing_clean_alias_hint_map_for_unblocked_handoff")
    elif safe_count_map(summary.get("alias_hint_counts")):
        blockers.append("repair_pack_non_empty_alias_hint_map_for_unblocked_handoff")
    if "shape_pattern_counts" not in summary or not isinstance(
        summary.get("shape_pattern_counts"), dict
    ):
        blockers.append("repair_pack_missing_clean_shape_pattern_map_for_unblocked_handoff")
    elif safe_count_map(summary.get("shape_pattern_counts")):
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
    cases = repair_pack_artifact.get("cases")
    if not isinstance(cases, list):
        return ["repair_pack_cases_missing_for_unblocked_handoff"]
    if case_count == 0 and cases:
        return ["repair_pack_case_count_mismatch_for_unblocked_handoff"]
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
