from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_pl_ce_browser_activation_evidence_gate import (
    BROWSER_ARTIFACTS,
    EXPECTED_STATUSES as BROWSER_GATE_EXPECTED_STATUSES,
    REQUIRED_INPUTS as BROWSER_GATE_REQUIRED_INPUTS,
)
from app.composition.accurate_intake_pl_ce_local_mvp_candidate_bundle import (
    EXPECTED_STATUSES as LOCAL_MVP_EXPECTED_STATUSES,
    REQUIRED_INPUTS as LOCAL_MVP_REQUIRED_INPUTS,
)
from app.composition.accurate_intake_pl_ce_ui_context_alignment_pack import (
    REQUIRED_INPUTS as UI_CONTEXT_REQUIRED_INPUTS,
)
from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS as CONTEXT_LIVE_REQUIRED_CASE_IDS,
)


REQUIRED_INPUTS = (
    "pl_ce_local_mvp_candidate_bundle",
    "pl_ce_browser_activation_evidence_gate",
    "pl_ce_ui_context_alignment_pack",
    "context_live_diagnostic_dry_run_evaluator",
    "context_live_response_contract_dry_run",
)

OPTIONAL_INPUTS = (
    "context_live_diagnostic_review_pack",
    "context_live_diagnostic_gate",
)

EXPECTED_STATUSES = {
    "pl_ce_local_mvp_candidate_bundle": "pl_ce_local_mvp_candidate_ready_for_human_review",
    "pl_ce_browser_activation_evidence_gate": "browser_activation_evidence_ready_for_human_review",
    "pl_ce_ui_context_alignment_pack": "ui_context_alignment_ready_for_human_review",
    "context_live_diagnostic_dry_run_evaluator": "pass",
    "context_live_response_contract_dry_run": "pass",
    "context_live_diagnostic_review_pack": {
        "context_live_diagnostic_review_ready_with_live_canary",
        "context_live_diagnostic_review_ready_without_live_canary",
    },
    "context_live_diagnostic_gate": {
        "context_live_diagnostic_gate_ready_with_live_canary",
        "context_live_diagnostic_gate_ready_without_live_canary",
    },
}

EXPECTED_ARTIFACT_TYPES = {
    "pl_ce_local_mvp_candidate_bundle": "accurate_intake_pl_ce_local_mvp_candidate_bundle",
    "pl_ce_browser_activation_evidence_gate": "accurate_intake_pl_ce_browser_activation_evidence_gate",
    "pl_ce_ui_context_alignment_pack": "accurate_intake_pl_ce_ui_context_alignment_pack",
    "context_live_diagnostic_dry_run_evaluator": (
        "accurate_intake_context_live_diagnostic_dry_run_evaluator"
    ),
    "context_live_response_contract_dry_run": (
        "accurate_intake_context_live_response_contract_dry_run"
    ),
    "context_live_diagnostic_review_pack": "accurate_intake_context_live_diagnostic_review_pack",
    "context_live_diagnostic_gate": "accurate_intake_context_live_diagnostic_gate",
}

EXPECTED_UPSTREAM_REQUIRED_INPUTS = {
    "pl_ce_local_mvp_candidate_bundle": tuple(LOCAL_MVP_REQUIRED_INPUTS),
    "pl_ce_browser_activation_evidence_gate": tuple(BROWSER_GATE_REQUIRED_INPUTS),
    "pl_ce_ui_context_alignment_pack": tuple(UI_CONTEXT_REQUIRED_INPUTS),
}

EXPECTED_NESTED_STATUSES = {
    "pl_ce_local_mvp_candidate_bundle": dict(LOCAL_MVP_EXPECTED_STATUSES),
    "pl_ce_browser_activation_evidence_gate": dict(BROWSER_GATE_EXPECTED_STATUSES),
    "pl_ce_ui_context_alignment_pack": {
        "ui_same_truth_contract": "pass",
        "product_pages_renderer_source_map": "product_pages_renderer_source_map_ready_for_human_review",
        "context_coverage_matrix": {
            "context_coverage_matrix_ready_for_human_review",
            "context_coverage_matrix_ready_with_known_runtime_gaps",
        },
        "product_pages_browser_smoke": "pass",
        "product_pages_seven_day_diary_smoke": "pass",
        "product_pages_short_term_context_smoke": "pass",
        "product_pages_visual_qa": "pass",
    },
}

FORBIDDEN_TRUTHY_FLAGS = (
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "live_provider_called",
    "web_tavily_used",
    "web_tavily_invoked",
    "websearch_evidence_used",
    "fooddb_evidence_used",
    "fooddb_truth_updated",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "manager_context_packet_schema_changed",
    "runtime_truth_changed",
    "mutation_changed",
    "mutation_authority",
    "frontend_semantic_owner",
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "canonical_eval_promoted",
    "live_provider_invoked",
    "fooddb_used",
    "fooddb_truth_used",
    "readiness_claimed",
    "deterministic_selected_intent",
    "deterministic_selected_target",
    "raw_text_intent_router_used",
)

OPTIONAL_LIVE_EVIDENCE_ALLOWED_FLAGS = {
    "context_live_diagnostic_review_pack": {
        "live_llm_invoked",
        "live_provider_invoked",
    },
    "context_live_diagnostic_gate": {
        "live_llm_invoked",
        "live_provider_invoked",
    }
}

CONTEXT_LIVE_GATE_REQUIRED_ARTIFACT_PATHS = (
    "context_live_diagnostic_case_matrix",
    "context_live_diagnostic_anti_overfit_guard",
    "context_live_provider_input_preflight",
    "context_live_response_contract_dry_run",
    "context_live_diagnostic_canary",
    "context_live_diagnostic_review_pack",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


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


def _allowed_statuses(expected_status: Any) -> set[str]:
    if isinstance(expected_status, str):
        return {expected_status}
    if isinstance(expected_status, set | frozenset | tuple | list):
        return {str(status) for status in expected_status}
    return {str(expected_status)}


def _identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _status(payload) not in _allowed_statuses(EXPECTED_STATUSES[group_id]):
        blockers.append(f"{group_id}.unexpected_status:{_status(payload)}")
    if payload.get("artifact_type") != EXPECTED_ARTIFACT_TYPES[group_id]:
        blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    return blockers


def _claim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    allowed_flags = OPTIONAL_LIVE_EVIDENCE_ALLOWED_FLAGS.get(group_id, set())
    return [
        f"{group_id}.{flag}"
        for flag in FORBIDDEN_TRUTHY_FLAGS
        if flag not in allowed_flags
        if _claim_is_true(payload.get(flag))
    ]


def _list_contains_all(value: Any, expected_values: tuple[str, ...]) -> bool:
    if not isinstance(value, list):
        return False
    return set(expected_values).issubset(set(str(item) for item in value))


def _structural_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("artifact_schema_version") != "1.0":
        blockers.append(f"{group_id}.missing_artifact_schema_version")

    upstream_blockers = payload.get("blockers")
    if upstream_blockers != []:
        suffix = "upstream_blockers_present" if upstream_blockers else "upstream_blockers_missing"
        blockers.append(f"{group_id}.{suffix}")

    if group_id in {
        "context_live_diagnostic_dry_run_evaluator",
        "context_live_response_contract_dry_run",
        "context_live_diagnostic_review_pack",
        "context_live_diagnostic_gate",
    }:
        return blockers

    if not _list_contains_all(
        payload.get("required_inputs"),
        EXPECTED_UPSTREAM_REQUIRED_INPUTS[group_id],
    ):
        blockers.append(f"{group_id}.required_inputs_incomplete")

    included_statuses = payload.get("included_artifact_statuses")
    if not isinstance(included_statuses, dict) or not included_statuses:
        blockers.append(f"{group_id}.included_artifact_statuses_missing")
    elif not set(EXPECTED_UPSTREAM_REQUIRED_INPUTS[group_id]).issubset(included_statuses):
        blockers.append(f"{group_id}.included_artifact_statuses_incomplete")
    else:
        for input_id, expected_status in EXPECTED_NESTED_STATUSES[group_id].items():
            nested_status = _object_dict(included_statuses.get(input_id))
            nested_status_value = str(nested_status.get("status") or "")
            if nested_status_value not in _allowed_statuses(expected_status):
                blockers.append(
                    f"{group_id}.included_artifact_statuses."
                    f"{input_id}.unexpected_status:{nested_status.get('status')}"
                )
            if group_id == "pl_ce_browser_activation_evidence_gate" and input_id in BROWSER_ARTIFACTS:
                if nested_status.get("browser_executed") is not True:
                    blockers.append(
                        f"{group_id}.included_artifact_statuses."
                        f"{input_id}.browser_not_executed"
                    )
            if group_id == "pl_ce_ui_context_alignment_pack" and input_id.startswith(
                "product_pages_"
            ) and input_id != "product_pages_renderer_source_map":
                if nested_status.get("browser_executed") is not True:
                    blockers.append(
                        f"{group_id}.included_artifact_statuses."
                        f"{input_id}.browser_not_executed"
                    )

    if payload.get("aggregate_only") is not True:
        blockers.append(f"{group_id}.aggregate_only_not_true")
    if payload.get("self_generated_evidence_used") is not False:
        blockers.append(f"{group_id}.self_generated_evidence_not_false")
    if payload.get("review_required_before_provider_call") is not True:
        blockers.append(f"{group_id}.review_required_before_provider_call_not_true")
    return blockers


def _group_specific_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if group_id == "pl_ce_local_mvp_candidate_bundle":
        if payload.get("activation_gate_status") != "blocked_pending_human_and_browser_activation":
            blockers.append("pl_ce_local_mvp_candidate_bundle.unexpected_activation_gate_status")
        fooddb_dependency = _object_dict(payload.get("fooddb_dependency"))
        if fooddb_dependency.get("fooddb_artifact_status") != "blocked_waiting_for_fdb_artifact":
            blockers.append("pl_ce_local_mvp_candidate_bundle.fooddb_stop_gate_missing")
        if fooddb_dependency.get("ready_for_fdb_integration") is not False:
            blockers.append("pl_ce_local_mvp_candidate_bundle.fooddb_integration_not_blocked")
        activation_policy = _object_dict(
            _object_dict(payload.get("browser_gate_policy")).get("activation_gate")
        )
        if activation_policy.get("require_browser_execution") is not True:
            blockers.append("pl_ce_local_mvp_candidate_bundle.activation_browser_not_required")
        if activation_policy.get("browser_executed_required") is not True:
            blockers.append(
                "pl_ce_local_mvp_candidate_bundle.activation_browser_execution_not_required"
            )
    if group_id == "pl_ce_browser_activation_evidence_gate":
        if payload.get("all_required_browser_artifacts_executed") is not True:
            blockers.append(
                "pl_ce_browser_activation_evidence_gate.browser_artifacts_not_all_executed"
            )
        if payload.get("browser_executed_required") is not True:
            blockers.append("pl_ce_browser_activation_evidence_gate.browser_not_required")
        if not _list_contains_all(payload.get("browser_required_inputs"), tuple(BROWSER_ARTIFACTS)):
            blockers.append("pl_ce_browser_activation_evidence_gate.browser_inputs_incomplete")
        summary = _object_dict(payload.get("summary"))
        if summary.get("browser_artifact_count") != len(BROWSER_ARTIFACTS):
            blockers.append("pl_ce_browser_activation_evidence_gate.browser_artifact_count_mismatch")
        if summary.get("browser_executed_count") != len(BROWSER_ARTIFACTS):
            blockers.append("pl_ce_browser_activation_evidence_gate.browser_executed_count_mismatch")
        for flag in (
            "requires_three_distinct_pages",
            "requires_seven_day_today_diary",
            "requires_short_term_context_render",
            "requires_target_candidate_ui",
            "requires_fixture_full_product_loop_e2e",
            "requires_visual_qa",
            "requires_no_debug_trace_leak",
        ):
            if summary.get(flag) is not True:
                blockers.append(f"pl_ce_browser_activation_evidence_gate.{flag}_not_true")
        if _int_value(summary.get("fixture_product_loop_step_count")) < 10:
            blockers.append(
                "pl_ce_browser_activation_evidence_gate.fixture_product_loop_step_count_too_low"
            )
    if group_id == "pl_ce_ui_context_alignment_pack":
        summary = _object_dict(payload.get("summary"))
        if summary.get("pages_verified") != ["chat", "today", "body"]:
            blockers.append("pl_ce_ui_context_alignment_pack.pages_verified_mismatch")
        if summary.get("seven_day_diary_checked") is not True:
            blockers.append("pl_ce_ui_context_alignment_pack.seven_day_diary_not_checked")
        if summary.get("chat_context_reload_checked") is not True:
            blockers.append("pl_ce_ui_context_alignment_pack.chat_context_reload_not_checked")
        if summary.get("body_read_model_checked") is not True:
            blockers.append("pl_ce_ui_context_alignment_pack.body_read_model_not_checked")
        if _int_value(summary.get("context_covered_capabilities")) < 9:
            blockers.append("pl_ce_ui_context_alignment_pack.context_capabilities_not_covered")
        if summary.get("renderer_source_map_page_count") != 3:
            blockers.append("pl_ce_ui_context_alignment_pack.renderer_source_map_page_count_mismatch")
        if _int_value(summary.get("renderer_source_map_selector_count")) < 30:
            blockers.append("pl_ce_ui_context_alignment_pack.renderer_source_map_selector_count_too_low")
        if _int_value(summary.get("renderer_source_map_endpoint_count")) < 7:
            blockers.append("pl_ce_ui_context_alignment_pack.renderer_source_map_endpoint_count_too_low")
    if group_id == "context_live_diagnostic_dry_run_evaluator":
        summary = _object_dict(payload.get("summary"))
        if payload.get("diagnostic_only") is not True:
            blockers.append("context_live_diagnostic_dry_run_evaluator.diagnostic_only_not_true")
        if payload.get("fixture_only") is not True:
            blockers.append("context_live_diagnostic_dry_run_evaluator.fixture_only_not_true")
        if payload.get("plan_only") is not True:
            blockers.append("context_live_diagnostic_dry_run_evaluator.plan_only_not_true")
        if payload.get("fixed_case_matrix_used") is not True:
            blockers.append("context_live_diagnostic_dry_run_evaluator.fixed_case_matrix_not_used")
        if payload.get("semantic_owner") != "fixture_manager_structured_decision":
            blockers.append("context_live_diagnostic_dry_run_evaluator.semantic_owner_not_fixture_manager")
        if _int_value(summary.get("case_count")) != len(CONTEXT_LIVE_REQUIRED_CASE_IDS):
            blockers.append("context_live_diagnostic_dry_run_evaluator.case_count_mismatch")
        if _int_value(summary.get("evaluated_case_count")) != len(CONTEXT_LIVE_REQUIRED_CASE_IDS):
            blockers.append("context_live_diagnostic_dry_run_evaluator.evaluated_case_count_mismatch")
        if _int_value(summary.get("blocked_case_count")) != 0:
            blockers.append("context_live_diagnostic_dry_run_evaluator.blocked_case_count_nonzero")
        if _int_value(summary.get("target_candidate_cases")) < 1:
            blockers.append("context_live_diagnostic_dry_run_evaluator.target_candidate_cases_missing")
        if _int_value(summary.get("pending_pin_cases")) < 1:
            blockers.append("context_live_diagnostic_dry_run_evaluator.pending_pin_cases_missing")
        if _int_value(summary.get("ambiguity_cases")) < 1:
            blockers.append("context_live_diagnostic_dry_run_evaluator.ambiguity_cases_missing")
    if group_id == "context_live_response_contract_dry_run":
        summary = _object_dict(payload.get("summary"))
        if payload.get("diagnostic_only") is not True:
            blockers.append("context_live_response_contract_dry_run.diagnostic_only_not_true")
        if payload.get("fixture_only") is not True:
            blockers.append("context_live_response_contract_dry_run.fixture_only_not_true")
        if payload.get("plan_only") is not True:
            blockers.append("context_live_response_contract_dry_run.plan_only_not_true")
        if payload.get("provider_call_ready") is not False:
            blockers.append("context_live_response_contract_dry_run.provider_call_ready")
        if payload.get("human_approval_required_before_live_provider") is not True:
            blockers.append(
                "context_live_response_contract_dry_run.human_approval_before_live_missing"
            )
        if payload.get("full_matrix_required") is not True:
            blockers.append("context_live_response_contract_dry_run.full_matrix_not_required")
        if _int_value(summary.get("case_count")) != len(CONTEXT_LIVE_REQUIRED_CASE_IDS):
            blockers.append("context_live_response_contract_dry_run.case_count_mismatch")
        if _int_value(summary.get("validated_response_count")) != len(
            CONTEXT_LIVE_REQUIRED_CASE_IDS
        ):
            blockers.append(
                "context_live_response_contract_dry_run.validated_response_count_mismatch"
            )
        if _int_value(summary.get("blocked_response_count")) != 0:
            blockers.append("context_live_response_contract_dry_run.blocked_response_count_nonzero")
        if _int_value(summary.get("target_candidate_response_count")) < 1:
            blockers.append("context_live_response_contract_dry_run.target_candidate_response_missing")
        if _int_value(summary.get("ambiguity_preserved_response_count")) < 1:
            blockers.append("context_live_response_contract_dry_run.ambiguity_response_missing")
    if group_id == "context_live_diagnostic_review_pack":
        summary = _object_dict(payload.get("summary"))
        status = _status(payload)
        if payload.get("diagnostic_only") is not True:
            blockers.append("context_live_diagnostic_review_pack.diagnostic_only_not_true")
        if payload.get("aggregate_only") is not True:
            blockers.append("context_live_diagnostic_review_pack.aggregate_only_not_true")
        if payload.get("human_review_required") is not True:
            blockers.append("context_live_diagnostic_review_pack.human_review_required_missing")
        if payload.get("fixed_case_matrix_used") is not True:
            blockers.append("context_live_diagnostic_review_pack.fixed_case_matrix_not_used")
        if _int_value(summary.get("fixed_case_count")) != len(CONTEXT_LIVE_REQUIRED_CASE_IDS):
            blockers.append("context_live_diagnostic_review_pack.fixed_case_count_mismatch")
        if _int_value(summary.get("dry_run_validated_response_count")) != len(
            CONTEXT_LIVE_REQUIRED_CASE_IDS
        ):
            blockers.append(
                "context_live_diagnostic_review_pack.dry_run_validated_response_count_mismatch"
            )
        if _int_value(summary.get("dry_run_blocked_response_count")) != 0:
            blockers.append("context_live_diagnostic_review_pack.dry_run_blocked_response_count_nonzero")
        if status == "context_live_diagnostic_review_ready_with_live_canary":
            if payload.get("live_llm_invoked") is not True:
                blockers.append("context_live_diagnostic_review_pack.live_llm_invoked_not_true")
            if payload.get("live_provider_invoked") is not True:
                blockers.append("context_live_diagnostic_review_pack.live_provider_invoked_not_true")
            if payload.get("live_canary_status") != "live_diagnostic_pass":
                blockers.append("context_live_diagnostic_review_pack.live_canary_status_not_pass")
            if _int_value(summary.get("live_provider_output_count")) != len(
                CONTEXT_LIVE_REQUIRED_CASE_IDS
            ):
                blockers.append(
                    "context_live_diagnostic_review_pack.live_provider_output_count_mismatch"
                )
            if _int_value(summary.get("live_blocked_response_count")) != 0:
                blockers.append("context_live_diagnostic_review_pack.live_blocked_response_count_nonzero")
            if _int_value(summary.get("live_target_candidate_response_count")) < 1:
                blockers.append(
                    "context_live_diagnostic_review_pack.live_target_candidate_response_missing"
                )
            if _int_value(summary.get("live_ambiguity_preserved_response_count")) < 1:
                blockers.append(
                    "context_live_diagnostic_review_pack.live_ambiguity_response_missing"
                )
        else:
            if payload.get("live_llm_invoked") is not False:
                blockers.append("context_live_diagnostic_review_pack.unexpected_live_llm_invoked")
            if payload.get("live_provider_invoked") is not False:
                blockers.append("context_live_diagnostic_review_pack.unexpected_live_provider_invoked")
    if group_id == "context_live_diagnostic_gate":
        summary = _object_dict(payload.get("summary"))
        artifact_paths = _object_dict(payload.get("artifact_paths"))
        status = _status(payload)
        if payload.get("diagnostic_only") is not True:
            blockers.append("context_live_diagnostic_gate.diagnostic_only_not_true")
        if payload.get("local_only") is not True:
            blockers.append("context_live_diagnostic_gate.local_only_not_true")
        if payload.get("fixed_case_matrix_used") is not True:
            blockers.append("context_live_diagnostic_gate.fixed_case_matrix_not_used")
        if payload.get("full_matrix_live_probe_required") is not True:
            blockers.append("context_live_diagnostic_gate.full_matrix_live_probe_not_required")
        if payload.get("ad_hoc_live_case_selection_allowed") is not False:
            blockers.append("context_live_diagnostic_gate.ad_hoc_live_case_selection_allowed")
        if payload.get("anti_overfit_guard_required") is not True:
            blockers.append("context_live_diagnostic_gate.anti_overfit_guard_not_required")
        if payload.get("response_contract_dry_run_required") is not True:
            blockers.append("context_live_diagnostic_gate.response_contract_dry_run_not_required")
        for path_id in CONTEXT_LIVE_GATE_REQUIRED_ARTIFACT_PATHS:
            if not artifact_paths.get(path_id):
                blockers.append(f"context_live_diagnostic_gate.artifact_paths.{path_id}_missing")
        if _int_value(summary.get("fixed_case_count")) != len(CONTEXT_LIVE_REQUIRED_CASE_IDS):
            blockers.append("context_live_diagnostic_gate.fixed_case_count_mismatch")
        if _int_value(summary.get("dry_run_validated_response_count")) != len(
            CONTEXT_LIVE_REQUIRED_CASE_IDS
        ):
            blockers.append("context_live_diagnostic_gate.dry_run_validated_response_count_mismatch")
        if status == "context_live_diagnostic_gate_ready_with_live_canary":
            if payload.get("review_pack_status") != "context_live_diagnostic_review_ready_with_live_canary":
                blockers.append("context_live_diagnostic_gate.review_pack_status_not_live_ready")
            if payload.get("canary_status") != "live_diagnostic_pass":
                blockers.append("context_live_diagnostic_gate.canary_status_not_pass")
            if payload.get("live_llm_invoked") is not True:
                blockers.append("context_live_diagnostic_gate.live_llm_invoked_not_true")
            if payload.get("live_provider_invoked") is not True:
                blockers.append("context_live_diagnostic_gate.live_provider_invoked_not_true")
            if _int_value(summary.get("live_provider_output_count")) != len(
                CONTEXT_LIVE_REQUIRED_CASE_IDS
            ):
                blockers.append("context_live_diagnostic_gate.live_provider_output_count_mismatch")
            if _int_value(summary.get("live_blocked_response_count")) != 0:
                blockers.append("context_live_diagnostic_gate.live_blocked_response_count_nonzero")
        else:
            if payload.get("review_pack_status") != "context_live_diagnostic_review_ready_without_live_canary":
                blockers.append("context_live_diagnostic_gate.review_pack_status_not_non_live_ready")
            if payload.get("live_llm_invoked") is not False:
                blockers.append("context_live_diagnostic_gate.unexpected_live_llm_invoked")
            if payload.get("live_provider_invoked") is not False:
                blockers.append("context_live_diagnostic_gate.unexpected_live_provider_invoked")
    return blockers


def _artifact_statuses(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "status": _status(payload),
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in payloads.items()
    }


def build_pl_ce_activation_review_manifest_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    required_inputs = {
        group_id: _object_dict(input_artifacts.get(group_id))
        for group_id in REQUIRED_INPUTS
    }
    optional_inputs = {
        group_id: _object_dict(input_artifacts.get(group_id))
        for group_id in OPTIONAL_INPUTS
        if _object_dict(input_artifacts.get(group_id))
    }
    inputs = {**required_inputs, **optional_inputs}
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_identity_blockers(group_id, payload))
        blockers.extend(_claim_blockers(group_id, payload))
        blockers.extend(_structural_blockers(group_id, payload))
        blockers.extend(_group_specific_blockers(group_id, payload))
    status = "pl_ce_activation_review_manifest_ready" if not blockers else "blocked"
    context_live_review_pack = optional_inputs.get("context_live_diagnostic_review_pack", {})
    context_live_review_status = _status(context_live_review_pack)
    context_live_review_live_invoked = context_live_review_pack.get("live_llm_invoked") is True
    context_live_gate = optional_inputs.get("context_live_diagnostic_gate", {})
    context_live_gate_status = _status(context_live_gate)
    context_live_gate_live_invoked = context_live_gate.get("live_llm_invoked") is True
    if context_live_review_status == "context_live_diagnostic_review_ready_with_live_canary":
        context_live_review_checkpoint = "live_canary_passed"
        context_live_provider_status = "context_only_live_diagnostic_passed_not_full_e2e"
    elif context_live_review_status == "context_live_diagnostic_review_ready_without_live_canary":
        context_live_review_checkpoint = "ready_without_live_canary"
        context_live_provider_status = "context_live_review_ready_without_live_canary"
    else:
        context_live_review_checkpoint = "not_provided"
        context_live_provider_status = "not_provided"
    if context_live_gate_status == "context_live_diagnostic_gate_ready_with_live_canary":
        context_live_gate_checkpoint = "gate_live_canary_passed"
        context_live_gate_stop_status = "context_only_live_diagnostic_gate_passed_not_full_e2e"
    elif context_live_gate_status == "context_live_diagnostic_gate_ready_without_live_canary":
        context_live_gate_checkpoint = "gate_ready_without_live_canary"
        context_live_gate_stop_status = "context_live_gate_ready_without_live_canary"
    else:
        context_live_gate_checkpoint = "not_provided"
        context_live_gate_stop_status = "not_provided"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_activation_review_manifest",
            "status": status,
            "claim_scope": "pl_ce_activation_review_manifest_for_human_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "required_inputs": list(REQUIRED_INPUTS),
            "blockers": blockers,
            "included_artifact_statuses": _artifact_statuses(inputs),
            "review_checkpoints": {
                "local_mvp_candidate_bundle": (
                    "ready_for_human_review"
                    if inputs["pl_ce_local_mvp_candidate_bundle"].get("status")
                    == EXPECTED_STATUSES["pl_ce_local_mvp_candidate_bundle"]
                    else "blocked_or_missing"
                ),
                "browser_activation_evidence_gate": (
                    "ready_for_human_review"
                    if inputs["pl_ce_browser_activation_evidence_gate"].get("status")
                    == EXPECTED_STATUSES["pl_ce_browser_activation_evidence_gate"]
                    else "blocked_or_missing"
                ),
                "ui_context_alignment_pack": (
                    "ready_for_human_review"
                    if inputs["pl_ce_ui_context_alignment_pack"].get("status")
                    == EXPECTED_STATUSES["pl_ce_ui_context_alignment_pack"]
                    else "blocked_or_missing"
                ),
                "context_live_diagnostic_dry_run_evaluator": (
                    "pass"
                    if inputs["context_live_diagnostic_dry_run_evaluator"].get("status")
                    == EXPECTED_STATUSES["context_live_diagnostic_dry_run_evaluator"]
                    else "blocked_or_missing"
                ),
                "context_live_response_contract_dry_run": (
                    "pass"
                    if inputs["context_live_response_contract_dry_run"].get("status")
                    == EXPECTED_STATUSES["context_live_response_contract_dry_run"]
                    else "blocked_or_missing"
                ),
                "context_live_diagnostic_review_pack": context_live_review_checkpoint,
                "context_live_diagnostic_gate": context_live_gate_checkpoint,
            },
            "remaining_stop_gates": {
                "fooddb_artifact_status": "blocked_waiting_for_fdb_artifact",
                "live_provider_status": "blocked_pending_human_approval",
                "context_live_provider_status": context_live_provider_status,
                "context_live_gate_status": context_live_gate_stop_status,
                "context_live_dry_run_status": (
                    "passed_fixture_dry_run_only"
                    if inputs["context_live_diagnostic_dry_run_evaluator"].get("status")
                    == EXPECTED_STATUSES["context_live_diagnostic_dry_run_evaluator"]
                    else "blocked_before_live_diagnostic"
                ),
                "context_live_response_contract_status": (
                    "passed_fixture_response_contract_only"
                    if inputs["context_live_response_contract_dry_run"].get("status")
                    == EXPECTED_STATUSES["context_live_response_contract_dry_run"]
                    else "blocked_before_live_diagnostic"
                ),
                "websearch_runtime_status": "blocked_out_of_scope_for_pl_ce",
                "readiness_claim_status": "blocked_not_requested",
                "mutation_status": "blocked_no_mutation_authority",
            },
            "next_allowed_actions": [
                "human_review_local_candidate_bundle",
                "human_review_browser_activation_evidence",
                "human_review_context_live_diagnostic_dry_run",
                "prepare_limited_live_diagnostic_plan_only_after_human_approval",
            ],
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "aggregate_only": True,
            "self_generated_evidence_used": False,
            "human_review_required": True,
            "live_diagnostic_human_approval_required": True,
            "live_diagnostic_evidence_present": bool(context_live_review_pack),
            "upstream_live_llm_invoked": context_live_review_live_invoked,
            "context_live_gate_evidence_present": bool(context_live_gate),
            "upstream_context_live_gate_llm_invoked": context_live_gate_live_invoked,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "shared_contract_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "live_provider_called": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "fooddb_evidence_used": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
            "manager_context_packet_schema_changed": False,
            "mutation_authority": False,
        }
    )


__all__ = [
    "EXPECTED_ARTIFACT_TYPES",
    "EXPECTED_STATUSES",
    "OPTIONAL_INPUTS",
    "REQUIRED_INPUTS",
    "build_pl_ce_activation_review_manifest_artifact",
]
