from __future__ import annotations

from typing import Any


REQUIRED_CURRENT_SHELL_FIXTURE_STEPS = (
    "target_update",
    "food_log",
    "listed_basket_commit",
    "correction",
    "removal",
    "remaining_query",
    "reload_continuity",
    "browser_render_same_truth",
    "context_replay",
    "fake_provider_context_smoke",
)

EXPECTED_STATUSES = {
    "ui_same_truth_contract": "pass",
    "context_quality_pack": "context_quality_diagnostic_pass",
    "short_term_context_runtime_replay": {
        "runtime_replay_diagnostic_pass",
        "diagnostic_has_known_context_gaps",
    },
    "context_coverage_matrix": {
        "context_coverage_matrix_ready_for_human_review",
        "context_coverage_matrix_ready_with_known_runtime_gaps",
    },
    "context_live_diagnostic_case_matrix": "pass",
    "context_live_diagnostic_anti_overfit_guard": "pass",
    "context_conditioned_intent_wall": "pass",
    "correction_removal_fixture_flow": "pass",
    "responder_input_contract_fake_smoke": "pass",
    "fixture_packet_emulator": "fixture_packet_emulator_ready",
    "fake_provider_tool_loop_smoke": "fake_provider_tool_loop_smoke_pass",
    "review_eval_candidate_pipeline": "review_eval_candidate_pipeline_ready",
    "local_operator_data_hygiene_bundle": "local_operator_data_hygiene_ready",
    "current_shell_fixture_e2e": "current_shell_fixture_e2e_diagnostic_pass",
    "mvp_gate_summary": "pass",
}

EXPECTED_ARTIFACT_TYPES = {
    "ui_same_truth_contract": "accurate_intake_ui_same_truth_render_contract",
    "context_quality_pack": "accurate_intake_context_quality_pack",
    "short_term_context_runtime_replay": "accurate_intake_short_term_context_runtime_replay",
    "context_coverage_matrix": "accurate_intake_pl_ce_context_coverage_matrix",
    "context_live_diagnostic_case_matrix": "accurate_intake_context_live_diagnostic_case_matrix",
    "context_live_diagnostic_anti_overfit_guard": "accurate_intake_context_live_diagnostic_anti_overfit_guard",
    "context_conditioned_intent_wall": "accurate_intake_context_conditioned_intent_wall",
    "correction_removal_fixture_flow": "accurate_intake_correction_removal_fixture_flow",
    "responder_input_contract_fake_smoke": "accurate_intake_responder_input_contract_fake_smoke",
    "fixture_packet_emulator": "accurate_intake_fixture_evidence_packet_emulator",
    "fake_provider_tool_loop_smoke": "accurate_intake_fake_provider_tool_loop_smoke",
    "review_eval_candidate_pipeline": "accurate_intake_review_eval_candidate_pipeline",
    "local_operator_data_hygiene_bundle": "accurate_intake_local_operator_data_hygiene_bundle",
    "current_shell_fixture_e2e": "accurate_intake_current_shell_fixture_e2e",
}

EXPECTED_GATE_IDS = {
    "mvp_gate_summary": "accurate_intake_mvp_deterministic_v1",
}

FORBIDDEN_TRUE_FLAGS = (
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "live_provider_called",
    "live_provider_invoked",
    "web_tavily_used",
    "web_tavily_invoked",
    "websearch_evidence_used",
    "fooddb_evidence_used",
    "fooddb_used",
    "fooddb_truth_updated",
    "context_engineering_fault_claimed",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "manager_context_packet_schema_changed",
    "mutation_authority",
    "runtime_truth_changed",
    "mutation_changed",
    "writes_performed",
    "import_allowed",
    "live_websearch_used",
    "canonical_eval_promoted",
    "canonical_eval_promotion_allowed",
    "deterministic_semantic_inference_used",
    "deterministic_selected_target",
    "raw_text_intent_router_used",
    "fixture_packet_truth",
    "evidence_packet_truth",
    "frontend_semantic_owner",
)


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
        return value.strip().lower() not in {"", "0", "false", "no", "none", "null", "not_available", "not_checked"}
    return True


def validate_input_artifacts(
    payloads: dict[str, dict[str, Any]],
    *,
    required_inputs: tuple[str, ...],
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    activation_gap_signals: list[str] = []
    for artifact_id in required_inputs:
        payload = dict(payloads.get(artifact_id) or {})
        expected_status = EXPECTED_STATUSES[artifact_id]
        expected_statuses = expected_status if isinstance(expected_status, set) else {expected_status}
        if _status(payload) not in expected_statuses:
            blockers.append(f"{artifact_id}.unexpected_status:{_status(payload)}")
        expected_artifact_type = EXPECTED_ARTIFACT_TYPES.get(artifact_id)
        if expected_artifact_type and payload.get("artifact_type") != expected_artifact_type:
            blockers.append(f"{artifact_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
        expected_gate_id = EXPECTED_GATE_IDS.get(artifact_id)
        if expected_gate_id and payload.get("gate_id") != expected_gate_id:
            blockers.append(f"{artifact_id}.unexpected_gate_id:{payload.get('gate_id')}")
        if payload.get("blockers") not in (None, []):
            blockers.append(f"{artifact_id}.upstream_blockers_present")
        for flag in FORBIDDEN_TRUE_FLAGS:
            if _claim_is_true(payload.get(flag)):
                blockers.append(f"{artifact_id}.{flag}")

    optional_browser = dict(payloads.get("optional_browser_evidence") or {})
    if optional_browser:
        if optional_browser.get("browser_executed") is not True:
            activation_gap_signals.append("optional_browser_evidence.browser_execution_blocked_for_activation")
        if optional_browser.get("status") == "pass" and optional_browser.get("browser_executed") is not True:
            blockers.append("optional_browser_evidence.pass_status_without_browser_execution")
    return blockers, activation_gap_signals


def runtime_replay_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("runtime_trace_backed") is not True:
        blockers.append("short_term_context_runtime_replay.runtime_trace_backed_not_true")
    if _int_value(payload.get("scenario_count")) < 7:
        blockers.append("short_term_context_runtime_replay.scenario_count_too_low")
    summary = dict(payload.get("summary") or {})
    if _int_value(summary.get("current_gap_scenarios")) > 0:
        blockers.append("short_term_context_runtime_replay.current_gap_scenarios_present")
    return blockers


def context_live_matrix_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("plan_only") is not True:
        blockers.append("context_live_diagnostic_case_matrix.plan_only_not_true")
    summary = dict(payload.get("summary") or {})
    if _int_value(summary.get("case_count")) < 10:
        blockers.append("context_live_diagnostic_case_matrix.case_count_too_low")
    if _int_value(summary.get("compound_cases")) < 1:
        blockers.append("context_live_diagnostic_case_matrix.compound_cases_missing")
    return blockers


def context_live_anti_overfit_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("plan_only") is not True:
        blockers.append("context_live_diagnostic_anti_overfit_guard.plan_only_not_true")
    summary = dict(payload.get("summary") or {})
    if summary.get("fixed_case_matrix_used") is not True:
        blockers.append("context_live_diagnostic_anti_overfit_guard.fixed_case_matrix_missing")
    if _int_value(summary.get("case_count")) < 10:
        blockers.append("context_live_diagnostic_anti_overfit_guard.case_count_too_low")
    if _int_value(summary.get("compound_cases")) < 1:
        blockers.append("context_live_diagnostic_anti_overfit_guard.compound_cases_missing")
    if _int_value(summary.get("ambiguity_cases")) < 1:
        blockers.append("context_live_diagnostic_anti_overfit_guard.ambiguity_cases_missing")
    return blockers


def current_shell_fixture_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    completed_steps = {str(step) for step in list(payload.get("completed_current_shell_steps") or []) if str(step).strip()}
    if not set(REQUIRED_CURRENT_SHELL_FIXTURE_STEPS).issubset(completed_steps):
        blockers.append("current_shell_fixture_e2e.completed_steps_missing")
    if payload.get("browser_executed") is not True:
        blockers.append("current_shell_fixture_e2e.browser_not_executed")
    if payload.get("fixture_evidence_used") is not True:
        blockers.append("current_shell_fixture_e2e.fixture_evidence_missing")
    return blockers
