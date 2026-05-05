from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

REQUIRED_INPUTS = (
    "ui_same_truth_contract",
    "context_quality_pack",
    "short_term_context_runtime_replay",
    "context_coverage_matrix",
    "context_conditioned_intent_wall",
    "correction_removal_fixture_flow",
    "responder_input_contract_fake_smoke",
    "fixture_packet_emulator",
    "fake_provider_tool_loop_smoke",
    "review_eval_candidate_pipeline",
    "local_operator_data_hygiene_bundle",
    "mvp_gate_summary",
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
    "context_conditioned_intent_wall": "pass",
    "correction_removal_fixture_flow": "pass",
    "responder_input_contract_fake_smoke": "pass",
    "fixture_packet_emulator": "fixture_packet_emulator_ready",
    "fake_provider_tool_loop_smoke": "fake_provider_tool_loop_smoke_pass",
    "review_eval_candidate_pipeline": "review_eval_candidate_pipeline_ready",
    "local_operator_data_hygiene_bundle": "local_operator_data_hygiene_ready",
    "mvp_gate_summary": "pass",
}

EXPECTED_ARTIFACT_TYPES = {
    "ui_same_truth_contract": "accurate_intake_ui_same_truth_render_contract",
    "context_quality_pack": "accurate_intake_context_quality_pack",
    "short_term_context_runtime_replay": "accurate_intake_short_term_context_runtime_replay",
    "context_coverage_matrix": "accurate_intake_pl_ce_context_coverage_matrix",
    "context_conditioned_intent_wall": "accurate_intake_context_conditioned_intent_wall",
    "correction_removal_fixture_flow": "accurate_intake_correction_removal_fixture_flow",
    "responder_input_contract_fake_smoke": "accurate_intake_responder_input_contract_fake_smoke",
    "fixture_packet_emulator": "accurate_intake_fixture_evidence_packet_emulator",
    "fake_provider_tool_loop_smoke": "accurate_intake_fake_provider_tool_loop_smoke",
    "review_eval_candidate_pipeline": "accurate_intake_review_eval_candidate_pipeline",
    "local_operator_data_hygiene_bundle": "accurate_intake_local_operator_data_hygiene_bundle",
}

EXPECTED_GATE_IDS = {
    "mvp_gate_summary": "accurate_intake_mvp_deterministic_v1",
}

FORBIDDEN_TRUE_FLAGS = (
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "live_provider_called",
    "web_tavily_used",
    "web_tavily_invoked",
    "websearch_evidence_used",
    "fooddb_evidence_used",
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
        return value.strip().lower() not in {
            "",
            "0",
            "false",
            "no",
            "none",
            "null",
            "not_available",
            "not_checked",
        }
    return True


def _validate_input_artifacts(
    payloads: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    activation_gap_signals: list[str] = []
    for artifact_id in REQUIRED_INPUTS:
        payload = _object_dict(payloads.get(artifact_id))
        expected_status = EXPECTED_STATUSES[artifact_id]
        expected_statuses = expected_status if isinstance(expected_status, set) else {expected_status}
        if _status(payload) not in expected_statuses:
            blockers.append(f"{artifact_id}.unexpected_status:{_status(payload)}")
        expected_artifact_type = EXPECTED_ARTIFACT_TYPES.get(artifact_id)
        if expected_artifact_type and payload.get("artifact_type") != expected_artifact_type:
            blockers.append(
                f"{artifact_id}.unexpected_artifact_type:{payload.get('artifact_type')}"
            )
        expected_gate_id = EXPECTED_GATE_IDS.get(artifact_id)
        if expected_gate_id and payload.get("gate_id") != expected_gate_id:
            blockers.append(f"{artifact_id}.unexpected_gate_id:{payload.get('gate_id')}")
        if payload.get("blockers") not in (None, []):
            blockers.append(f"{artifact_id}.upstream_blockers_present")
        for flag in FORBIDDEN_TRUE_FLAGS:
            if _claim_is_true(payload.get(flag)):
                blockers.append(f"{artifact_id}.{flag}")

    optional_browser = _object_dict(payloads.get("optional_browser_evidence"))
    if optional_browser:
        if optional_browser.get("browser_executed") is not True:
            activation_gap_signals.append(
                "optional_browser_evidence.browser_execution_blocked_for_activation"
            )
        if optional_browser.get("status") == "pass" and optional_browser.get("browser_executed") is not True:
            blockers.append("optional_browser_evidence.pass_status_without_browser_execution")
    return blockers, activation_gap_signals


def _runtime_replay_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("runtime_trace_backed") is not True:
        blockers.append("short_term_context_runtime_replay.runtime_trace_backed_not_true")
    if _int_value(payload.get("scenario_count")) < 7:
        blockers.append("short_term_context_runtime_replay.scenario_count_too_low")
    summary = _object_dict(payload.get("summary"))
    if _int_value(summary.get("current_gap_scenarios")) > 0:
        blockers.append("short_term_context_runtime_replay.current_gap_scenarios_present")
    return blockers


def _artifact_statuses(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for artifact_id, payload in payloads.items():
        source = payload.get("_source_artifact_path") or payload.get("_source")
        statuses[artifact_id] = {
            "artifact_type": payload.get("artifact_type") or "unknown",
            "status": _status(payload),
            "present": bool(payload),
            "source_artifact_path": source,
        }
    return statuses


def build_pl_ce_local_mvp_candidate_bundle_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = {
        artifact_id: _object_dict(input_artifacts.get(artifact_id))
        for artifact_id in [*REQUIRED_INPUTS, "optional_browser_evidence"]
    }
    blockers, activation_gap_signals = _validate_input_artifacts(inputs)
    context_wall_summary = _object_dict(inputs["context_conditioned_intent_wall"].get("summary"))
    runtime_replay_summary = _object_dict(
        inputs["short_term_context_runtime_replay"].get("summary")
    )
    context_matrix_summary = _object_dict(inputs["context_coverage_matrix"].get("summary"))
    correction_summary = _object_dict(inputs["correction_removal_fixture_flow"].get("summary"))
    responder_summary = _object_dict(inputs["responder_input_contract_fake_smoke"].get("summary"))
    review_pipeline = inputs["review_eval_candidate_pipeline"]
    blockers.extend(_runtime_replay_blockers(inputs["short_term_context_runtime_replay"]))
    status = "pl_ce_local_mvp_candidate_ready_for_human_review" if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_local_mvp_candidate_bundle",
            "status": status,
            "activation_gate_status": "blocked_pending_human_and_browser_activation",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pl_ce_local_mvp_candidate_bundle",
            "required_inputs": list(REQUIRED_INPUTS),
            "blockers": blockers,
            "activation_gap_signals": activation_gap_signals,
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "aggregate_only": True,
            "self_generated_evidence_used": False,
            "context_engineering_fault_claimed": False,
            "review_required_before_provider_call": True,
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
            "browser_gate_policy": {
                "local_mvp_candidate_bundle": {
                    "can_include_blocked_optional_browser": True,
                    "blocked_browser_is_not_pass": True,
                },
                "activation_gate": {
                    "require_browser_execution": True,
                    "browser_executed_required": True,
                },
            },
            "fooddb_dependency": {
                "fooddb_artifact_status": "blocked_waiting_for_fdb_artifact",
                "ready_for_fdb_integration": False,
                "fixture_metadata_is_real_fooddb_artifact": False,
                "auto_fix_attempted": False,
            },
            "included_artifact_statuses": _artifact_statuses(inputs),
            "summary": {
                "context_wall_scenarios": int(context_wall_summary.get("scenario_count") or 0),
                "short_term_runtime_replay_scenarios": _int_value(
                    runtime_replay_summary.get("scenario_count")
                ),
                "short_term_runtime_replay_current_gap_count": _int_value(
                    runtime_replay_summary.get("current_gap_scenarios")
                ),
                "context_covered_capabilities": int(
                    context_matrix_summary.get("covered_capability_count") or 0
                ),
                "context_known_runtime_gap_count": int(
                    context_matrix_summary.get("known_runtime_gap_count") or 0
                ),
                "correction_removal_scenarios": int(
                    correction_summary.get("scenario_count") or 0
                ),
                "responder_fake_smoke_scenarios": int(
                    responder_summary.get("scenario_count") or 0
                ),
                "review_candidate_count": int(
                    review_pipeline.get("review_candidate_count") or 0
                ),
                "activation_browser_required": True,
                "human_review_required": True,
            },
        }
    )


__all__ = [
    "EXPECTED_ARTIFACT_TYPES",
    "EXPECTED_GATE_IDS",
    "EXPECTED_STATUSES",
    "FORBIDDEN_TRUE_FLAGS",
    "REQUIRED_INPUTS",
    "build_pl_ce_local_mvp_candidate_bundle_artifact",
]
