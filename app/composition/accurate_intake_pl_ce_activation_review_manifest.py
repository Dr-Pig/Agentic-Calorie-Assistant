from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_pl_ce_activation_manifest_contract import (
    EXPECTED_ARTIFACT_TYPES,
    EXPECTED_STATUSES,
    OPTIONAL_INPUTS,
    REQUIRED_INPUTS,
)
from app.composition.accurate_intake_pl_ce_activation_manifest_validation import (
    activation_manifest_blockers,
    artifact_statuses,
)
from app.composition.accurate_intake_pl_ce_context_live_manifest_checks import (
    context_live_gate_state,
    context_live_review_state,
)

def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _context_live_stage_summary(
    context_live_gate: dict[str, Any],
    context_live_review_pack: dict[str, Any],
) -> dict[str, Any]:
    if not context_live_gate:
        review_stage = _object_dict(context_live_review_pack.get("context_live_diagnostic_stage_summary"))
        if review_stage:
            live_stage = str(review_stage.get("live_stage") or "unknown")
            if live_stage == "full-matrix":
                stage_status = "review_pack_full_matrix_live_diagnostic_pass"
            elif live_stage == "single-case":
                stage_status = "review_pack_single_case_live_diagnostic_pass"
            elif live_stage == "not_invoked":
                stage_status = "review_pack_not_invoked"
            else:
                stage_status = "review_pack_stage_unknown"
            return {
                "live_stage": live_stage,
                "stage_gate_status": stage_status,
                "live_provider_output_count": _int_value(
                    review_stage.get("live_provider_output_count")
                ),
                "live_blocked_response_count": _int_value(
                    review_stage.get("live_blocked_response_count")
                ),
                "full_matrix_live_probe_completed": (
                    review_stage.get("full_matrix_live_probe_completed") is True
                ),
                "single_case_live_probe_completed": (
                    review_stage.get("single_case_live_probe_completed") is True
                ),
                "diagnostic_only_not_readiness": True,
            }
        return {
            "live_stage": "not_provided",
            "stage_gate_status": "not_provided",
            "live_provider_output_count": 0,
            "live_blocked_response_count": 0,
            "full_matrix_live_probe_completed": False,
            "single_case_live_probe_completed": False,
            "diagnostic_only_not_readiness": True,
        }
    if context_live_gate.get("live_provider_invoked") is not True:
        live_stage = "not_invoked"
    else:
        live_stage = str(context_live_gate.get("live_stage") or "unknown")
    summary = _object_dict(context_live_gate.get("summary"))
    stage_status = str(context_live_gate.get("stage_gate_status") or "not_applicable")
    return {
        "live_stage": live_stage,
        "stage_gate_status": stage_status,
        "live_provider_output_count": _int_value(summary.get("live_provider_output_count")),
        "live_blocked_response_count": _int_value(summary.get("live_blocked_response_count")),
        "full_matrix_live_probe_completed": stage_status == "context_live_full_matrix_probe_pass",
        "single_case_live_probe_completed": stage_status == "context_live_single_case_probe_pass",
        "diagnostic_only_not_readiness": True,
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
        blockers.extend(activation_manifest_blockers(group_id, payload))
    status = "pl_ce_activation_review_manifest_ready" if not blockers else "blocked"
    context_live_review_pack = optional_inputs.get("context_live_diagnostic_review_pack", {})
    context_live_gate = optional_inputs.get("context_live_diagnostic_gate", {})
    context_live_review_checkpoint, context_live_provider_status, context_live_review_live_invoked = (
        context_live_review_state(context_live_review_pack)
    )
    context_live_gate_checkpoint, context_live_gate_stop_status, context_live_gate_live_invoked = (
        context_live_gate_state(context_live_gate)
    )
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_activation_review_manifest",
            "status": status,
            "claim_scope": "pl_ce_activation_review_manifest_for_human_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "required_inputs": list(REQUIRED_INPUTS),
            "blockers": blockers,
            "included_artifact_statuses": artifact_statuses(inputs),
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
                "context_live_diagnostic_holdout_plan": (
                    "pass"
                    if inputs["context_live_diagnostic_holdout_plan"].get("status")
                    == EXPECTED_STATUSES["context_live_diagnostic_holdout_plan"]
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
                "context_live_holdout_plan_status": (
                    "passed_holdout_plan_only"
                    if inputs["context_live_diagnostic_holdout_plan"].get("status")
                    == EXPECTED_STATUSES["context_live_diagnostic_holdout_plan"]
                    else "blocked_before_live_diagnostic"
                ),
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
                "human_review_context_live_holdout_plan",
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
            "context_live_diagnostic_stage_summary": _context_live_stage_summary(
                context_live_gate,
                context_live_review_pack,
            ),
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
