from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_local_candidate_bundle_validators import (
    EXPECTED_ARTIFACT_TYPES,
    EXPECTED_GATE_IDS,
    EXPECTED_STATUSES,
    FORBIDDEN_TRUE_FLAGS,
    REQUIRED_FIXTURE_FULL_PRODUCT_LOOP_STEPS,
    context_live_anti_overfit_blockers,
    context_live_matrix_blockers,
    fixture_full_product_loop_blockers,
    runtime_replay_blockers,
    validate_input_artifacts,
)
from app.composition import current_shell_compatibility_ids as cs_ids


REQUIRED_INPUTS = (
    "ui_same_truth_contract",
    "context_quality_pack",
    "short_term_context_runtime_replay",
    "context_coverage_matrix",
    "context_live_diagnostic_case_matrix",
    "context_live_diagnostic_anti_overfit_guard",
    "context_conditioned_intent_wall",
    "correction_removal_fixture_flow",
    "responder_input_contract_fake_smoke",
    "fixture_packet_emulator",
    "fake_provider_tool_loop_smoke",
    "review_eval_candidate_pipeline",
    "local_operator_data_hygiene_bundle",
    "fixture_full_product_loop_e2e",
    "mvp_gate_summary",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _validate_input_artifacts(
    payloads: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    return validate_input_artifacts(payloads, required_inputs=REQUIRED_INPUTS)


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
    context_live_matrix_summary = _object_dict(
        inputs["context_live_diagnostic_case_matrix"].get("summary")
    )
    context_live_anti_overfit_summary = _object_dict(
        inputs["context_live_diagnostic_anti_overfit_guard"].get("summary")
    )
    runtime_replay_summary = _object_dict(
        inputs["short_term_context_runtime_replay"].get("summary")
    )
    context_matrix_summary = _object_dict(inputs["context_coverage_matrix"].get("summary"))
    correction_summary = _object_dict(inputs["correction_removal_fixture_flow"].get("summary"))
    responder_summary = _object_dict(inputs["responder_input_contract_fake_smoke"].get("summary"))
    review_pipeline = inputs["review_eval_candidate_pipeline"]
    fixture_full_product_loop = inputs["fixture_full_product_loop_e2e"]
    blockers.extend(runtime_replay_blockers(inputs["short_term_context_runtime_replay"]))
    blockers.extend(context_live_matrix_blockers(inputs["context_live_diagnostic_case_matrix"]))
    blockers.extend(
        context_live_anti_overfit_blockers(
            inputs["context_live_diagnostic_anti_overfit_guard"]
        )
    )
    blockers.extend(fixture_full_product_loop_blockers(fixture_full_product_loop))
    status = (
        cs_ids.CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_READY_STATUS
        if not blockers
        else "blocked"
    )
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": cs_ids.CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_ARTIFACT_TYPE,
            "status": status,
            "activation_gate_status": "blocked_pending_human_and_browser_activation",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": cs_ids.CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_CLAIM_SCOPE,
            "legacy_artifact_type_aliases": list(cs_ids.LEGACY_LOCAL_MVP_ARTIFACT_TYPES),
            "legacy_status_aliases": list(cs_ids.LEGACY_LOCAL_MVP_READY_STATUSES),
            "legacy_claim_scope_aliases": list(cs_ids.LEGACY_LOCAL_MVP_CLAIM_SCOPES),
            "legacy_group_id_aliases": list(cs_ids.LEGACY_LOCAL_MVP_GROUP_IDS),
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
                "short_term_runtime_replay_scenarios": int(
                    runtime_replay_summary.get("scenario_count") or 0
                ),
                "short_term_runtime_replay_current_gap_count": int(
                    runtime_replay_summary.get("current_gap_scenarios") or 0
                ),
                "context_covered_capabilities": int(
                    context_matrix_summary.get("covered_capability_count") or 0
                ),
                "context_known_runtime_gap_count": int(
                    context_matrix_summary.get("known_runtime_gap_count") or 0
                ),
                "context_live_case_matrix_cases": int(
                    context_live_matrix_summary.get("case_count") or 0
                ),
                "context_live_case_matrix_compound_cases": int(
                    context_live_matrix_summary.get("compound_cases") or 0
                ),
                "context_live_anti_overfit_fixed_case_matrix_used": (
                    context_live_anti_overfit_summary.get("fixed_case_matrix_used") is True
                ),
                "context_live_anti_overfit_case_count": int(
                    context_live_anti_overfit_summary.get("case_count") or 0
                ),
                "context_live_anti_overfit_compound_cases": int(
                    context_live_anti_overfit_summary.get("compound_cases") or 0
                ),
                "context_live_anti_overfit_ambiguity_cases": int(
                    context_live_anti_overfit_summary.get("ambiguity_cases") or 0
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
                "fixture_full_product_loop_steps": len(
                    list(fixture_full_product_loop.get("completed_product_loop_steps") or [])
                ),
                "fixture_full_product_loop_browser_executed": fixture_full_product_loop.get("browser_executed") is True,
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
    "REQUIRED_FIXTURE_FULL_PRODUCT_LOOP_STEPS",
    "build_pl_ce_local_mvp_candidate_bundle_artifact",
]
