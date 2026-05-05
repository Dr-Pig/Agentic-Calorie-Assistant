from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

FORBIDDEN_TRUE_CLAIMS = (
    "context_engineering_fault_claimed",
    "manager_context_packet_schema_changed",
    "deterministic_selected_target",
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "mutation_authority",
    "live_llm_invoked",
    "web_tavily_used",
    "fooddb_truth_updated",
    "real_fooddb_pass_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
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


def _overclaim_blockers(artifact_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{artifact_id}.{flag}"
        for flag in FORBIDDEN_TRUE_CLAIMS
        if payload.get(flag) is True
    ]


def _context_review_blockers(payload: dict[str, Any]) -> list[str]:
    blockers = []
    if _status(payload) != "generated":
        blockers.append("context_review.not_generated")
    summary = _object_dict(payload.get("summary"))
    if _int_value(summary.get("present_context_trace_count")) <= 0:
        blockers.append("context_review.no_present_context_trace")
    if _int_value(summary.get("forbidden_context_trace_count")) > 0:
        blockers.append("context_review.forbidden_context_detected")
    return blockers


def _target_eval_blockers(payload: dict[str, Any]) -> list[str]:
    blockers = []
    if _status(payload) != "generated":
        blockers.append("target_candidate_eval.not_generated")
    summary = _object_dict(payload.get("summary"))
    if _int_value(summary.get("scenario_count")) < 5:
        blockers.append("target_candidate_eval.scenario_count_too_low")
    if _int_value(summary.get("ambiguous_scenarios")) < 1:
        blockers.append("target_candidate_eval.ambiguous_scenarios_missing")
    return blockers


def _window_blockers(payload: dict[str, Any]) -> list[str]:
    blockers = []
    if _status(payload) != "generated":
        blockers.append("context_window.not_generated")
    if payload.get("pending_followup_hard_pinned") is not True:
        blockers.append("context_window.pending_followup_not_hard_pinned")
    if payload.get("pending_draft_hard_pinned") is not True:
        blockers.append("context_window.pending_draft_not_hard_pinned")
    if payload.get("long_term_memory_used") is not False:
        blockers.append("context_window.long_term_memory_used")
    if payload.get("proactive_or_rescue_used") is not False:
        blockers.append("context_window.proactive_or_rescue_used")
    return blockers


def _replay_blockers(payload: dict[str, Any]) -> list[str]:
    blockers = []
    if _status(payload) != "generated":
        blockers.append("context_replay.not_generated")
    if _int_value(payload.get("scenario_count")) < 12:
        blockers.append("context_replay.scenario_count_too_low")
    summary = _object_dict(payload.get("summary"))
    if _int_value(summary.get("pending_pin_scenarios")) < 3:
        blockers.append("context_replay.pending_pin_scenarios_too_low")
    if _int_value(summary.get("ambiguous_scenarios")) < 1:
        blockers.append("context_replay.ambiguous_scenarios_missing")
    if _int_value(summary.get("manager_semantic_required_scenarios")) < 1:
        blockers.append("context_replay.manager_semantic_required_missing")
    if _int_value(summary.get("outside_current_day_omitted_scenarios")) < 1:
        blockers.append("context_replay.outside_current_day_omitted_missing")
    return blockers


def _fake_provider_blockers(payload: dict[str, Any]) -> list[str]:
    blockers = []
    if _status(payload) != "pass":
        blockers.append("fake_provider_context_smoke.not_pass")
    if payload.get("final_semantic_decision_source") != "fixture_manager_structured_decision":
        blockers.append("fake_provider_context_smoke.semantic_source_not_fixture_manager")
    summary = _object_dict(payload.get("summary"))
    if payload.get("manager_handoff_matrix_checked") is not True:
        blockers.append("fake_provider_context_smoke.manager_handoff_matrix_missing")
    if _int_value(summary.get("manager_handoff_scenario_count")) < 6:
        blockers.append("fake_provider_context_smoke.manager_handoff_scenario_count_too_low")
    if _int_value(summary.get("ambiguous_back_reference_scenarios")) < 1:
        blockers.append("fake_provider_context_smoke.ambiguous_back_reference_missing")
    return blockers


def _runtime_replay_blockers(payload: dict[str, Any]) -> list[str]:
    blockers = []
    if not payload:
        blockers.append("short_term_context_runtime_replay.not_generated")
        return blockers
    if _status(payload) not in {"runtime_replay_diagnostic_pass", "diagnostic_has_known_context_gaps"}:
        blockers.append("short_term_context_runtime_replay.invalid_status")
    if payload.get("runtime_trace_backed") is not True:
        blockers.append("short_term_context_runtime_replay.not_runtime_trace_backed")
    if _int_value(payload.get("scenario_count")) < 7:
        blockers.append("short_term_context_runtime_replay.scenario_count_too_low")
    return blockers


def build_context_quality_pack_artifact(
    *,
    context_review: dict[str, Any],
    target_candidate_eval: dict[str, Any],
    context_window_diagnostic: dict[str, Any],
    context_replay: dict[str, Any],
    fake_provider_context_smoke: dict[str, Any],
    short_term_context_runtime_replay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inputs = {
        "context_review": _object_dict(context_review),
        "target_candidate_eval": _object_dict(target_candidate_eval),
        "context_window_diagnostic": _object_dict(context_window_diagnostic),
        "context_replay": _object_dict(context_replay),
        "fake_provider_context_smoke": _object_dict(fake_provider_context_smoke),
        "short_term_context_runtime_replay": _object_dict(short_term_context_runtime_replay),
    }
    blockers: list[str] = []
    for artifact_id, payload in inputs.items():
        blockers.extend(_overclaim_blockers(artifact_id, payload))
    blockers.extend(_context_review_blockers(inputs["context_review"]))
    blockers.extend(_target_eval_blockers(inputs["target_candidate_eval"]))
    blockers.extend(_window_blockers(inputs["context_window_diagnostic"]))
    blockers.extend(_replay_blockers(inputs["context_replay"]))
    blockers.extend(_fake_provider_blockers(inputs["fake_provider_context_smoke"]))
    blockers.extend(_runtime_replay_blockers(inputs["short_term_context_runtime_replay"]))

    target_summary = _object_dict(inputs["target_candidate_eval"].get("summary"))
    replay_summary = _object_dict(inputs["context_replay"].get("summary"))
    review_summary = _object_dict(inputs["context_review"].get("summary"))
    runtime_replay_summary = _object_dict(inputs["short_term_context_runtime_replay"].get("summary"))
    fake_provider_summary = _object_dict(inputs["fake_provider_context_smoke"].get("summary"))
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_quality_pack",
            "claim_scope": "pl_ce_context_quality_diagnostic",
            "status": "context_quality_diagnostic_pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "blockers": blockers,
            "summary": {
                "present_context_trace_count": _int_value(
                    review_summary.get("present_context_trace_count")
                ),
                "forbidden_context_trace_count": _int_value(
                    review_summary.get("forbidden_context_trace_count")
                ),
                "target_candidate_scenario_count": _int_value(
                    target_summary.get("scenario_count")
                ),
                "ambiguous_target_scenarios": _int_value(
                    target_summary.get("ambiguous_scenarios")
                ),
                "context_replay_scenario_count": _int_value(
                    replay_summary.get("scenario_count")
                ),
                "pending_pin_scenarios": _int_value(
                    replay_summary.get("pending_pin_scenarios")
                ),
                "manager_semantic_required_scenarios": _int_value(
                    replay_summary.get("manager_semantic_required_scenarios")
                ),
                "outside_current_day_omitted_scenarios": _int_value(
                    replay_summary.get("outside_current_day_omitted_scenarios")
                ),
                "short_term_runtime_replay_scenario_count": _int_value(
                    runtime_replay_summary.get("scenario_count")
                ),
                "short_term_runtime_replay_current_gap_scenarios": _int_value(
                    runtime_replay_summary.get("current_gap_scenarios")
                ),
                "fake_provider_handoff_scenario_count": _int_value(
                    fake_provider_summary.get("manager_handoff_scenario_count")
                ),
                "fake_provider_ambiguous_back_reference_scenarios": _int_value(
                    fake_provider_summary.get("ambiguous_back_reference_scenarios")
                ),
            },
            "local_only": True,
            "diagnostic_only": True,
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "short_term_context_runtime_replay_checked": bool(inputs["short_term_context_runtime_replay"]),
            "short_term_context_current_gap_scenarios": _int_value(
                runtime_replay_summary.get("current_gap_scenarios")
            ),
            "short_term_context_known_gap_signals": list(
                runtime_replay_summary.get("known_gap_signals") or []
            ),
            "fooddb_truth_updated": False,
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


__all__ = ["build_context_quality_pack_artifact"]
