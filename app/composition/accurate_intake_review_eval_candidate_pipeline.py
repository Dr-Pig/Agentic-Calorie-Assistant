from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

EXPECTED_STATUSES = {
    "current_shell_fixture_e2e": "current_shell_fixture_e2e_diagnostic_pass",
    "ui_same_truth_contract": "pass",
    "context_quality_pack": "context_quality_diagnostic_pass",
    "contextual_interaction_matrix": "pass",
    "session_context_carryover_qa_bundle": "session_context_carryover_qa_ready_for_human_review",
    "fixture_packet_emulator": "fixture_packet_emulator_ready",
    "fake_provider_tool_loop_smoke": "fake_provider_tool_loop_smoke_pass",
}

FORBIDDEN_TRUE_CLAIMS = (
    "fooddb_truth_updated",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "product_readiness_claimed",
    "private_self_use_approved",
    "live_llm_invoked",
    "web_tavily_used",
    "ready_for_fdb_integration",
    "ready_for_live_diagnostic_decision",
    "manager_context_packet_schema_changed",
    "deterministic_selected_intent",
    "deterministic_selected_target",
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "frontend_semantic_owner",
    "mutation_authority",
    "runtime_truth_changed",
    "mutation_changed",
)

SUGGESTED_TAXONOMY = {
    "current_shell_fixture_e2e": "evidence_gap",
    "ui_same_truth_contract": "frontend_display_bug",
    "context_quality_pack": "manager_context_gap",
    "contextual_interaction_matrix": "context_conditioned_intent_gap",
    "session_context_carryover_qa_bundle": "session_context_carryover_gap",
    "fixture_packet_emulator": "evidence_gap",
    "fake_provider_tool_loop_smoke": "final_mapping_gap",
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _overclaim_blockers(artifact_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{artifact_id}.{flag}"
        for flag in FORBIDDEN_TRUE_CLAIMS
        if payload.get(flag) is True
    ]


def _review_candidate(artifact_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    artifact_type = str(payload.get("artifact_type") or artifact_id)
    return {
        "review_candidate_id": f"review:{artifact_type}",
        "source_artifact_id": artifact_id,
        "source_artifact_type": artifact_type,
        "source_status": _status(payload),
        "suggested_taxonomy": SUGGESTED_TAXONOMY[artifact_id],
        "raw_trace_is_truth": False,
        "raw_traces_review_input_only": True,
        "human_approval_required": True,
        "canonical_eval_promoted": False,
        "fooddb_truth_updated": False,
        "contains_personal_diet_logs": True,
        "do_not_commit": True,
    }


def build_review_eval_candidate_pipeline_artifact(
    *,
    current_shell_fixture_e2e: dict[str, Any],
    ui_same_truth_contract: dict[str, Any],
    context_quality_pack: dict[str, Any],
    contextual_interaction_matrix: dict[str, Any],
    session_context_carryover_qa_bundle: dict[str, Any],
    fixture_packet_emulator: dict[str, Any],
    fake_provider_tool_loop_smoke: dict[str, Any],
) -> dict[str, Any]:
    inputs = {
        "current_shell_fixture_e2e": _object_dict(current_shell_fixture_e2e),
        "ui_same_truth_contract": _object_dict(ui_same_truth_contract),
        "context_quality_pack": _object_dict(context_quality_pack),
        "contextual_interaction_matrix": _object_dict(contextual_interaction_matrix),
        "session_context_carryover_qa_bundle": _object_dict(
            session_context_carryover_qa_bundle
        ),
        "fixture_packet_emulator": _object_dict(fixture_packet_emulator),
        "fake_provider_tool_loop_smoke": _object_dict(fake_provider_tool_loop_smoke),
    }
    blockers: list[str] = []
    for artifact_id, payload in inputs.items():
        blockers.extend(_overclaim_blockers(artifact_id, payload))
        expected = EXPECTED_STATUSES[artifact_id]
        if _status(payload) != expected:
            blockers.append(f"{artifact_id}.unexpected_status:{_status(payload)}")

    candidates = [
        _review_candidate(artifact_id, payload)
        for artifact_id, payload in inputs.items()
    ]
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_review_eval_candidate_pipeline",
            "claim_scope": "local_review_to_eval_candidate_pipeline",
            "status": "review_eval_candidate_pipeline_ready" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "blockers": blockers,
            "local_only": True,
            "diagnostic_only": True,
            "raw_traces_review_input_only": True,
            "review_candidate_count": len(candidates),
            "review_candidates": candidates,
            "human_approval_required": True,
            "canonical_eval_promoted": False,
            "canonical_eval_promotion_allowed": False,
            "fooddb_truth_updated": False,
            "contains_personal_diet_logs": True,
            "do_not_commit": True,
            "ready_for_fdb_integration": False,
            "ready_for_live_diagnostic_decision": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "input_statuses": {
                artifact_id: {
                    "status": _status(payload),
                    "artifact_type": payload.get("artifact_type") or "unknown",
                }
                for artifact_id, payload in inputs.items()
            },
        }
    )


__all__ = ["build_review_eval_candidate_pipeline_artifact"]
