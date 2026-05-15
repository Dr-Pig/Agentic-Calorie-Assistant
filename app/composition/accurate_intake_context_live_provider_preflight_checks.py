from __future__ import annotations

from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import REQUIRED_CASE_IDS
from app.composition.accurate_intake_context_live_provider_contract import (
    FORBIDDEN_INPUT_KEYS,
    FORBIDDEN_TRUTHY_FLAGS,
    REQUIRED_RESPONSE_FIELDS,
    RESPONSE_SCHEMA_NAME,
    claim_is_true,
    list_value,
    object_dict,
)


def matrix_blockers(matrix: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if matrix.get("artifact_type") != "accurate_intake_context_live_diagnostic_case_matrix":
        blockers.append("matrix.unexpected_artifact_type")
    if matrix.get("status") != "pass":
        blockers.append("matrix.status_not_pass")
    if [str(object_dict(case).get("case_id") or "") for case in list_value(matrix.get("cases"))] != list(
        REQUIRED_CASE_IDS
    ):
        blockers.append("matrix.fixed_case_order_mismatch")
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if claim_is_true(matrix.get(flag)):
            blockers.append(f"matrix.{flag}")
    return blockers


def anti_overfit_blockers(anti_overfit_guard: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if anti_overfit_guard.get("artifact_type") != "accurate_intake_context_live_diagnostic_anti_overfit_guard":
        blockers.append("anti_overfit_guard.unexpected_artifact_type")
    if anti_overfit_guard.get("status") != "pass":
        blockers.append("anti_overfit_guard.status_not_pass")
    summary = object_dict(anti_overfit_guard.get("summary"))
    if summary.get("fixed_case_matrix_used") is not True:
        blockers.append("anti_overfit_guard.fixed_case_matrix_not_used")
    if int(summary.get("distinct_intent_count") or 0) < 8:
        blockers.append("anti_overfit_guard.intent_diversity_too_low")
    if int(summary.get("distinct_workflow_effect_count") or 0) < 8:
        blockers.append("anti_overfit_guard.workflow_effect_diversity_too_low")
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if claim_is_true(anti_overfit_guard.get(flag)):
            blockers.append(f"anti_overfit_guard.{flag}")
    return blockers


def provider_input_blockers(provider_input: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    case_id = str(provider_input.get("case_id") or "unknown_case")
    if provider_input.get("provider_input_mode") != "context_contract_preflight_no_provider_call":
        blockers.append(f"{case_id}.provider_input_mode_not_preflight")
    schema = object_dict(provider_input.get("response_schema"))
    if schema.get("name") != RESPONSE_SCHEMA_NAME:
        blockers.append(f"{case_id}.response_schema_name_mismatch")
    if schema.get("strict") is not True:
        blockers.append(f"{case_id}.response_schema_not_strict")
    if tuple(schema.get("required") or ()) != REQUIRED_RESPONSE_FIELDS:
        blockers.append(f"{case_id}.response_schema_required_fields_mismatch")
    context = object_dict(provider_input.get("manager_context_sidecar"))
    if context.get("context_policy_version") != "manager_context_policy_v1":
        blockers.append(f"{case_id}.context_policy_version_missing")
    loaded = [str(field) for field in list_value(context.get("loaded_context_summary"))]
    if "context_policy_version" not in loaded:
        blockers.append(f"{case_id}.loaded_context_summary_missing_policy")
    omitted = set(str(field) for field in list_value(context.get("omitted_context_summary")))
    for forbidden_key in FORBIDDEN_INPUT_KEYS:
        if forbidden_key not in omitted:
            blockers.append(f"{case_id}.forbidden_key_not_omitted:{forbidden_key}")
    tool_policy = object_dict(provider_input.get("tool_policy"))
    if tool_policy.get("tools_available") != []:
        blockers.append(f"{case_id}.tools_available_not_empty")
    if tool_policy.get("tool_outputs_as_truth") is not False:
        blockers.append(f"{case_id}.tool_outputs_as_truth")
    expected = object_dict(provider_input.get("expected_semantic_contract"))
    if expected.get("mutation_allowed") is not False:
        blockers.append(f"{case_id}.mutation_allowed")
    if "deterministic_selected_intent" not in list_value(expected.get("must_not_happen")):
        blockers.append(f"{case_id}.deterministic_intent_guard_missing")
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if claim_is_true(provider_input.get(flag)):
            blockers.append(f"{case_id}.{flag}")
    return blockers


__all__ = ["anti_overfit_blockers", "matrix_blockers", "provider_input_blockers"]
