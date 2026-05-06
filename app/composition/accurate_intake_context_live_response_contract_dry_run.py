from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import REQUIRED_CASE_IDS
from app.composition.accurate_intake_context_live_provider_input_preflight import (
    REQUIRED_RESPONSE_FIELDS,
    RESPONSE_SCHEMA_NAME,
    build_context_live_provider_input_preflight_artifact,
)


FORBIDDEN_TRUTHY_FLAGS = (
    "live_llm_invoked",
    "live_provider_invoked",
    "fooddb_used",
    "web_tavily_used",
    "runtime_truth_changed",
    "mutation_changed",
    "manager_context_packet_schema_changed",
    "product_readiness_claimed",
    "private_self_use_approved",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return False


def _target_candidates(provider_input: dict[str, Any]) -> list[str]:
    prior_context = _object_dict(_object_dict(provider_input.get("manager_context_sidecar")).get("prior_context"))
    candidates = prior_context.get("target_candidates")
    if isinstance(candidates, list):
        return [str(candidate) for candidate in candidates if str(candidate)]
    return []


def _fixture_response_for_input(provider_input: dict[str, Any]) -> dict[str, Any]:
    expected = _object_dict(provider_input.get("expected_semantic_contract"))
    sidecar = _object_dict(provider_input.get("manager_context_sidecar"))
    candidates = _target_candidates(provider_input)
    if sidecar.get("ambiguity_expected") is True:
        target_resolution = {"status": "ambiguous", "candidate_ids": candidates}
        clarification_question = "fixture_requires_manager_clarification"
    elif sidecar.get("target_candidates_expected") is True:
        target_resolution = {"status": "candidates_available", "candidate_ids": candidates}
        clarification_question = None
    else:
        target_resolution = {"status": "not_applicable", "candidate_ids": []}
        clarification_question = None
    return _json_safe(
        {
            "case_id": provider_input.get("case_id"),
            "manager_intent": expected.get("manager_intent"),
            "workflow_effect": expected.get("workflow_effect"),
            "target_resolution": target_resolution,
            "mutation_request": {
                "requested": False,
                "reason": "context_live_response_contract_dry_run_never_mutates",
            },
            "clarification_question": clarification_question,
            "confidence_notes": "fixture manager decision used only to validate response contract shape",
        }
    )


def _preflight_blockers(preflight: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if preflight.get("artifact_type") != "accurate_intake_context_live_provider_input_preflight":
        blockers.append("provider_input_preflight.unexpected_artifact_type")
    if preflight.get("status") != "pass":
        blockers.append("provider_input_preflight.status_not_pass")
    if preflight.get("provider_call_ready") is not False:
        blockers.append("provider_input_preflight.provider_call_ready")
    if preflight.get("human_approval_required_before_live_provider") is not True:
        blockers.append("provider_input_preflight.human_approval_before_live_missing")
    if preflight.get("fixed_case_matrix_used") is not True:
        blockers.append("provider_input_preflight.fixed_case_matrix_not_used")
    if preflight.get("response_schema_name") != RESPONSE_SCHEMA_NAME:
        blockers.append("provider_input_preflight.response_schema_name_mismatch")
    if preflight.get("required_response_fields") != list(REQUIRED_RESPONSE_FIELDS):
        blockers.append("provider_input_preflight.required_response_fields_mismatch")
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if _claim_is_true(preflight.get(flag)):
            blockers.append(f"provider_input_preflight.{flag}")
    return blockers


def _response_blockers(
    provider_input: dict[str, Any],
    response: dict[str, Any],
) -> list[str]:
    case_id = str(provider_input.get("case_id") or response.get("case_id") or "unknown_case")
    blockers: list[str] = []
    required_fields = set(REQUIRED_RESPONSE_FIELDS)
    response_fields = set(response)
    missing = required_fields - response_fields
    extras = response_fields - required_fields
    for field in sorted(missing):
        blockers.append(f"{case_id}.response_missing_field:{field}")
    for field in sorted(extras):
        blockers.append(f"{case_id}.response_extra_field:{field}")
    if response.get("case_id") != provider_input.get("case_id"):
        blockers.append(f"{case_id}.case_id_mismatch")
    expected = _object_dict(provider_input.get("expected_semantic_contract"))
    if response.get("manager_intent") != expected.get("manager_intent"):
        blockers.append(f"{case_id}.manager_intent_mismatch")
    if response.get("workflow_effect") != expected.get("workflow_effect"):
        blockers.append(f"{case_id}.workflow_effect_mismatch")
    mutation_request = _object_dict(response.get("mutation_request"))
    mutation_fields = set(mutation_request)
    if mutation_fields != {"requested", "reason"}:
        for field in sorted({"requested", "reason"} - mutation_fields):
            blockers.append(f"{case_id}.mutation_request_missing_field:{field}")
        for field in sorted(mutation_fields - {"requested", "reason"}):
            blockers.append(f"{case_id}.mutation_request_extra_field:{field}")
    if not isinstance(mutation_request.get("requested"), bool):
        blockers.append(f"{case_id}.mutation_request_requested_not_boolean")
    if not isinstance(mutation_request.get("reason"), str):
        blockers.append(f"{case_id}.mutation_request_reason_not_string")
    if mutation_request.get("requested") is not False:
        blockers.append(f"{case_id}.mutation_requested")
    target_resolution = _object_dict(response.get("target_resolution"))
    target_fields = set(target_resolution)
    if target_fields != {"status", "candidate_ids"}:
        for field in sorted({"status", "candidate_ids"} - target_fields):
            blockers.append(f"{case_id}.target_resolution_missing_field:{field}")
        for field in sorted(target_fields - {"status", "candidate_ids"}):
            blockers.append(f"{case_id}.target_resolution_extra_field:{field}")
    if not isinstance(target_resolution.get("status"), str):
        blockers.append(f"{case_id}.target_resolution_status_not_string")
    sidecar = _object_dict(provider_input.get("manager_context_sidecar"))
    candidate_ids = [str(candidate) for candidate in _list_value(target_resolution.get("candidate_ids"))]
    if not isinstance(target_resolution.get("candidate_ids"), list):
        blockers.append(f"{case_id}.target_resolution_candidate_ids_not_array")
    elif any(not isinstance(candidate, str) for candidate in target_resolution.get("candidate_ids", [])):
        blockers.append(f"{case_id}.target_resolution_candidate_ids_not_strings")
    if sidecar.get("ambiguity_expected") is True:
        if target_resolution.get("status") != "ambiguous":
            blockers.append(f"{case_id}.ambiguity_not_preserved")
    elif sidecar.get("target_candidates_expected") is True:
        if target_resolution.get("status") not in {"candidates_available", "resolved"}:
            blockers.append(f"{case_id}.target_candidates_not_available")
        if not candidate_ids:
            blockers.append(f"{case_id}.target_candidate_ids_missing")
    elif candidate_ids:
        blockers.append(f"{case_id}.unexpected_target_candidate_ids")
    if not (isinstance(response.get("clarification_question"), str) or response.get("clarification_question") is None):
        blockers.append(f"{case_id}.clarification_question_not_string_or_null")
    if response.get("clarification_question") and sidecar.get("ambiguity_expected") is not True:
        blockers.append(f"{case_id}.unexpected_clarification_question")
    if not isinstance(response.get("confidence_notes"), str):
        blockers.append(f"{case_id}.confidence_notes_not_string")
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if _claim_is_true(response.get(flag)):
            blockers.append(f"{case_id}.{flag}")
    return blockers


def build_context_live_response_contract_dry_run_artifact(
    context_live_provider_input_preflight: dict[str, Any] | None = None,
    fixture_responses: list[dict[str, Any]] | None = None,
    require_full_matrix: bool = True,
) -> dict[str, Any]:
    preflight = _object_dict(context_live_provider_input_preflight or build_context_live_provider_input_preflight_artifact())
    provider_inputs = [_object_dict(row) for row in _list_value(preflight.get("provider_inputs"))]
    responses = (
        [_object_dict(row) for row in fixture_responses]
        if fixture_responses is not None
        else [_fixture_response_for_input(provider_input) for provider_input in provider_inputs]
    )
    blockers = _preflight_blockers(preflight)
    case_ids = [str(row.get("case_id") or "") for row in responses]
    if require_full_matrix and case_ids != list(REQUIRED_CASE_IDS):
        blockers.append("fixture_response_fixed_case_order_mismatch")
    response_summaries: list[dict[str, Any]] = []
    provider_by_case = {str(row.get("case_id") or ""): row for row in provider_inputs}
    for response in responses:
        case_id = str(response.get("case_id") or "unknown_case")
        provider_input = provider_by_case.get(case_id, {})
        row_blockers = _response_blockers(provider_input, response) if provider_input else [
            f"{case_id}.provider_input_missing"
        ]
        blockers.extend(row_blockers)
        response_summaries.append(
            {
                "case_id": case_id,
                "manager_intent": response.get("manager_intent"),
                "workflow_effect": response.get("workflow_effect"),
                "target_resolution_status": _object_dict(response.get("target_resolution")).get("status"),
                "mutation_requested": _object_dict(response.get("mutation_request")).get("requested"),
                "blockers": row_blockers,
            }
        )
    blockers = list(dict.fromkeys(blockers))
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_response_contract_dry_run",
            "status": "pass" if not blockers else "blocked",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pl_ce_context_live_response_contract_dry_run_only",
            "diagnostic_only": True,
            "plan_only": True,
            "local_only": True,
            "fixture_only": True,
            "provider_call_ready": False,
            "human_approval_required_before_live_provider": True,
            "full_matrix_required": require_full_matrix,
            "response_schema_name": RESPONSE_SCHEMA_NAME,
            "response_schema_strict": True,
            "semantic_owner": "fixture_manager_structured_decision_for_dry_run_only",
            "deterministic_role": "validate_provider_response_contract_not_select_intent",
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
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": blockers,
            "summary": {
                "case_count": len(responses),
                "validated_response_count": sum(1 for row in response_summaries if not row["blockers"]),
                "blocked_response_count": sum(1 for row in response_summaries if row["blockers"]),
                "target_candidate_response_count": sum(
                    1
                    for row in response_summaries
                    if row["target_resolution_status"] in {"candidates_available", "resolved"}
                ),
                "ambiguity_preserved_response_count": sum(
                    1 for row in response_summaries if row["target_resolution_status"] == "ambiguous"
                ),
                "mutation_request_count": sum(1 for row in response_summaries if row["mutation_requested"]),
            },
            "provider_input_preflight_status": preflight.get("status", "not_available"),
            "response_summaries": response_summaries,
            "fixture_responses": responses,
        }
    )


__all__ = ["build_context_live_response_contract_dry_run_artifact"]
