from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_anti_overfit_guard import (
    build_context_live_diagnostic_anti_overfit_guard_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
    build_context_live_diagnostic_case_matrix_artifact,
)
from app.composition.accurate_intake_context_live_provider_contract import (
    REQUIRED_RESPONSE_FIELDS,
    RESPONSE_SCHEMA_NAME,
    json_safe,
    list_value,
    object_dict,
    provider_input_for_case,
)
from app.composition.accurate_intake_context_live_provider_preflight_checks import (
    anti_overfit_blockers,
    matrix_blockers,
    provider_input_blockers,
)


def build_context_live_provider_input_preflight_artifact(
    context_live_diagnostic_case_matrix: dict[str, Any] | None = None,
    context_live_diagnostic_anti_overfit_guard: dict[str, Any] | None = None,
    provider_inputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    matrix = object_dict(
        context_live_diagnostic_case_matrix or build_context_live_diagnostic_case_matrix_artifact()
    )
    anti_overfit_guard = object_dict(
        context_live_diagnostic_anti_overfit_guard
        or build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)
    )
    cases = [object_dict(case) for case in list_value(matrix.get("cases"))]
    inputs = provider_inputs if provider_inputs is not None else [provider_input_for_case(case) for case in cases]
    blockers = [
        *matrix_blockers(matrix),
        *anti_overfit_blockers(anti_overfit_guard),
    ]
    case_input_rows: list[dict[str, Any]] = []
    for provider_input in inputs:
        row = object_dict(provider_input)
        input_blockers = provider_input_blockers(row)
        blockers.extend(input_blockers)
        case_input_rows.append(
            {
                "case_id": row.get("case_id"),
                "provider_input_mode": row.get("provider_input_mode"),
                "response_schema": object_dict(row.get("response_schema")).get("name"),
                "strict_schema": object_dict(row.get("response_schema")).get("strict") is True,
                "blockers": input_blockers,
            }
        )
    if [str(row.get("case_id") or "") for row in case_input_rows] != list(REQUIRED_CASE_IDS):
        blockers.append("provider_input_fixed_case_order_mismatch")
    blockers = list(dict.fromkeys(blockers))
    return json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_provider_input_preflight",
            "status": "pass" if not blockers else "blocked",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "current_shell_compatibility_context_live_provider_input_contract_preflight",
            "diagnostic_only": True,
            "plan_only": True,
            "local_only": True,
            "fixture_only": True,
            "provider_call_ready": False,
            "human_approval_required_before_live_provider": True,
            "fixed_case_matrix_used": [str(row.get("case_id") or "") for row in case_input_rows]
            == list(REQUIRED_CASE_IDS),
            "response_schema_name": RESPONSE_SCHEMA_NAME,
            "response_schema_strict": True,
            "required_response_fields": list(REQUIRED_RESPONSE_FIELDS),
            "semantic_owner": "future_live_manager_provider_when_human_approved",
            "deterministic_role": "validate_provider_input_contract_not_select_intent",
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "raw_text_intent_router_used": False,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "blockers": blockers,
            "summary": {
                "case_count": len(case_input_rows),
                "provider_input_count": len(inputs),
                "blocked_input_count": sum(1 for row in case_input_rows if row["blockers"]),
                "strict_schema_input_count": sum(1 for row in case_input_rows if row["strict_schema"]),
                "target_candidate_inputs": sum(
                    1
                    for provider_input in inputs
                    if object_dict(provider_input.get("manager_context_sidecar")).get(
                        "target_candidates_expected"
                    )
                    is True
                ),
                "pending_pin_inputs": sum(
                    1
                    for provider_input in inputs
                    if object_dict(provider_input.get("manager_context_sidecar")).get(
                        "pending_pin_expected"
                    )
                    is True
                ),
            },
            "provider_input_summaries": case_input_rows,
            "provider_inputs": inputs,
            "best_practice_basis": {
                "openai_function_calling": "use schema-defined tool/function interfaces when connecting models to app data or actions",
                "openai_structured_outputs": "strict schema adherence is preferred for structured response contracts",
                "anthropic_tool_use": "tool definitions should provide clear descriptions and input schemas; context should be explicit and bounded",
            },
        }
    )


__all__ = [
    "REQUIRED_RESPONSE_FIELDS",
    "RESPONSE_SCHEMA_NAME",
    "build_context_live_provider_input_preflight_artifact",
]
