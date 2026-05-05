from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
)


FORBIDDEN_OUTPUT_FLAGS = (
    "deterministic_selected_intent",
    "deterministic_selected_target",
    "frontend_raw_text_semantic_router",
    "frontend_selected_target",
    "mutation_without_guard",
    "fooddb_truth_used",
    "readiness_claimed",
    "meal_logged",
    "claim_fooddb_exact_truth",
    "new_unrelated_meal",
    "delete_without_manager_decision",
    "remove_latest_item_by_default",
    "ledger_mutation",
    "treat_as_meal_kcal_estimate",
    "daily_target_update",
    "drop_one_intent_silently",
    "commit_pending_draft",
    "choose_first_target",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _case_id(case: dict[str, Any]) -> str:
    return str(case.get("case_id") or "")


def _fixture_output_for_case(case: dict[str, Any]) -> dict[str, Any]:
    expected_fields = [str(field) for field in _list_value(case.get("expected_context_fields"))]
    return _json_safe(
        {
            "case_id": _case_id(case),
            "provider_mode": "fixture_manager_dry_run",
            "semantic_source": "fixture_manager_structured_decision",
            "manager_intent": case.get("expected_manager_intent"),
            "workflow_effect": case.get("expected_workflow_effect"),
            "context_fields_seen": expected_fields,
            "target_candidates_seen": case.get("target_candidates_expected") is True,
            "pending_pin_seen": case.get("pending_pin_expected") is True,
            "ambiguity_preserved": case.get("ambiguity_expected") is True,
            "mutation_allowed": case.get("mutation_allowed") is True,
            "forbidden_events": [],
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
        }
    )


def _fixture_outputs(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_fixture_output_for_case(case) for case in cases]


def _matrix_blockers(matrix: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if matrix.get("artifact_type") != "accurate_intake_context_live_diagnostic_case_matrix":
        blockers.append("matrix.unexpected_artifact_type")
    if matrix.get("status") != "pass":
        blockers.append("matrix.status_not_pass")
    if matrix.get("plan_only") is not True:
        blockers.append("matrix.plan_only_not_true")
    for flag in (
        "live_llm_invoked",
        "live_provider_invoked",
        "fooddb_used",
        "web_tavily_used",
        "runtime_truth_changed",
        "mutation_changed",
        "manager_context_packet_schema_changed",
        "product_readiness_claimed",
        "private_self_use_approved",
    ):
        if matrix.get(flag) is True:
            blockers.append(f"matrix.{flag}")
    cases = [_object_dict(case) for case in _list_value(matrix.get("cases"))]
    case_ids = [_case_id(case) for case in cases]
    if case_ids != list(REQUIRED_CASE_IDS):
        blockers.append("matrix.fixed_case_order_mismatch")
    return blockers


def _output_blockers(case: dict[str, Any], output: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    case_id = _case_id(case) or "unknown_case"
    if output.get("semantic_source") != "fixture_manager_structured_decision":
        blockers.append(f"{case_id}.semantic_source_not_fixture_manager")
    if output.get("manager_intent") != case.get("expected_manager_intent"):
        blockers.append(f"{case_id}.manager_intent_mismatch")
    if output.get("workflow_effect") != case.get("expected_workflow_effect"):
        blockers.append(f"{case_id}.workflow_effect_mismatch")
    context_fields_seen = set(str(field) for field in _list_value(output.get("context_fields_seen")))
    for field in _list_value(case.get("expected_context_fields")):
        if str(field) not in context_fields_seen:
            blockers.append(f"{case_id}.missing_context_field:{field}")
    if case.get("target_candidates_expected") is True and output.get("target_candidates_seen") is not True:
        blockers.append(f"{case_id}.target_candidates_missing")
    if case.get("pending_pin_expected") is True and output.get("pending_pin_seen") is not True:
        blockers.append(f"{case_id}.pending_pin_missing")
    if case.get("ambiguity_expected") is True and output.get("ambiguity_preserved") is not True:
        blockers.append(f"{case_id}.ambiguity_not_preserved")
    if output.get("mutation_allowed") is not False:
        blockers.append(f"{case_id}.mutation_allowed")
    forbidden_events = [str(event) for event in _list_value(output.get("forbidden_events"))]
    for event in forbidden_events:
        if event in FORBIDDEN_OUTPUT_FLAGS or event in _list_value(case.get("must_not_happen")):
            blockers.append(f"{case_id}.forbidden_event:{event}")
    for flag in (
        "live_llm_invoked",
        "live_provider_invoked",
        "fooddb_used",
        "web_tavily_used",
        "runtime_truth_changed",
        "mutation_changed",
        "manager_context_packet_schema_changed",
    ):
        if output.get(flag) is True:
            blockers.append(f"{case_id}.{flag}")
    return blockers


def build_context_live_diagnostic_dry_run_evaluator_artifact(
    context_live_diagnostic_case_matrix: dict[str, Any],
    fixture_outputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    matrix = _object_dict(context_live_diagnostic_case_matrix)
    cases = [_object_dict(case) for case in _list_value(matrix.get("cases"))]
    outputs = fixture_outputs if fixture_outputs is not None else _fixture_outputs(cases)
    output_by_id = {
        str(output.get("case_id") or ""): _object_dict(output)
        for output in outputs
        if isinstance(output, dict)
    }
    blockers = _matrix_blockers(matrix)
    evaluated_cases: list[dict[str, Any]] = []
    for case in cases:
        case_id = _case_id(case)
        output = output_by_id.get(case_id)
        if output is None:
            blockers.append(f"{case_id}.fixture_output_missing")
            continue
        case_blockers = _output_blockers(case, output)
        blockers.extend(case_blockers)
        evaluated_cases.append(
            {
                "case_id": case_id,
                "expected_manager_intent": case.get("expected_manager_intent"),
                "expected_workflow_effect": case.get("expected_workflow_effect"),
                "fixture_manager_intent": output.get("manager_intent"),
                "fixture_workflow_effect": output.get("workflow_effect"),
                "blockers": case_blockers,
            }
        )
    blockers = list(dict.fromkeys(blockers))
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_dry_run_evaluator",
            "status": "pass" if not blockers else "blocked",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pl_ce_context_live_diagnostic_fixture_evaluator",
            "diagnostic_only": True,
            "fixture_only": True,
            "plan_only": True,
            "local_only": True,
            "fixed_case_matrix_used": [_case_id(case) for case in cases]
            == list(REQUIRED_CASE_IDS),
            "semantic_owner": "fixture_manager_structured_decision",
            "deterministic_role": "evaluate_structured_fixture_outputs_against_fixed_case_matrix",
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
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
                "case_count": len(cases),
                "evaluated_case_count": len(evaluated_cases),
                "blocked_case_count": sum(1 for row in evaluated_cases if row["blockers"]),
                "target_candidate_cases": sum(
                    1 for case in cases if case.get("target_candidates_expected") is True
                ),
                "pending_pin_cases": sum(
                    1 for case in cases if case.get("pending_pin_expected") is True
                ),
                "ambiguity_cases": sum(
                    1 for case in cases if case.get("ambiguity_expected") is True
                ),
            },
            "evaluated_cases": evaluated_cases,
        }
    )


__all__ = [
    "FORBIDDEN_OUTPUT_FLAGS",
    "build_context_live_diagnostic_dry_run_evaluator_artifact",
]
