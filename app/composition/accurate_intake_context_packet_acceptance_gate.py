from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_context_packet_acceptance_fixture_data import (
    DEFAULT_CURRENT_BUDGET,
    SCENARIO_INPUTS,
)
from app.intake.application.context_injection_policy import build_manager_context_pack
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.workflow_routing import build_workflow_routing_decision
from app.runtime.contracts.phase_a import InteractionEvent


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


class _ResolvedState:
    def __init__(self, *, injected_context: dict[str, Any] | None = None, onboarding_ready: bool = True) -> None:
        self.local_date = "2026-05-07"
        self.injected_context = dict(injected_context or {})
        self.conversation_state = None
        self.onboarding_ready = onboarding_ready


def _interaction_event(*, source: str, target_object_type: str, target_object_id: str) -> InteractionEvent:
    return InteractionEvent(
        source=source,
        surface_mode="ui_anchored_action" if source == "ui" else "chat_freeform",
        event_type="tap_meal" if source == "ui" else "user_message",
        raw_text="",
        action_id="edit_meal" if source == "ui" else None,
        target_object_type=target_object_type,
        target_object_id=target_object_id,
    )


def _build_scenario(
    *,
    scenario_id: str,
    raw_user_input: str,
    injected_context: dict[str, Any],
    interaction_event: InteractionEvent | None = None,
) -> dict[str, Any]:
    runtime_context = {
        "CURRENT_BUDGET": dict(DEFAULT_CURRENT_BUDGET),
        **dict(injected_context),
    }
    resolved_state = _ResolvedState(injected_context=runtime_context)
    current_turn_context = build_current_turn_context_v1(
        raw_user_input=raw_user_input,
        resolved_state=resolved_state,
        interaction_event=interaction_event,
    )
    manager_context_pack = build_manager_context_pack(current_turn_context=current_turn_context)
    routing = build_workflow_routing_decision(
        raw_user_input=raw_user_input,
        current_turn_context=current_turn_context,
        resolved_state=resolved_state,
    )
    attachment = routing.attachment_decision
    return _json_safe(
        {
            "scenario_id": scenario_id,
            "raw_user_input": raw_user_input,
            "target_workflow_family": routing.target_workflow_family,
            "disposition": routing.disposition,
            "routing_confidence": routing.routing_confidence,
            "attachment_reason": attachment.reason if attachment is not None else None,
            "attachment_disposition": attachment.disposition if attachment is not None else None,
            "candidate_attachment_target_count": len(current_turn_context.candidate_attachment_targets),
            "open_workflow_type": current_turn_context.open_workflow_type,
            "phase_a_trace_present": bool(routing.phase_a_trace),
            "pending_followup_present": current_turn_context.pending_followup is not None,
            "current_budget_snapshot_present": current_turn_context.current_budget_snapshot is not None,
            "candidate_attachment_targets_read_only": all(
                bool(candidate.get("mutation_authority") is False)
                for candidate in current_turn_context.candidate_attachment_targets
            ),
            "interaction_source": current_turn_context.current_interaction_event.source,
            "target_resolution_source": current_turn_context.target_resolution_posture.get("target_resolution_source"),
            "target_resolution_posture_read_only": current_turn_context.target_resolution_posture.get("read_only") is True,
            "manager_context_pack_present": manager_context_pack is not None,
            "manager_context_keys": sorted(manager_context_pack.manager_context.keys()),
            "available_if_needed_keys": sorted(manager_context_pack.available_if_needed.keys()),
            "policy_must_inject": list(manager_context_pack.policy.must_inject),
            "manager_context_current_budget_snapshot_read_only": (
                manager_context_pack.manager_context.get("current_budget_snapshot", {}).get("read_only") is True
            ),
            "manager_context_recent_chat_turns_read_only": all(
                bool(turn.get("read_only") is True and turn.get("mutation_authority") is False)
                for turn in list(manager_context_pack.manager_context.get("recent_chat_turns") or [])
            ),
            "manager_context_promoted_target_resolution_posture": (
                "target_resolution_posture" in manager_context_pack.manager_context
            ),
            "manager_context_promoted_recent_item_targets": "recent_item_targets" in manager_context_pack.manager_context,
            "promotion_reasons": list(manager_context_pack.promotion_reasons),
        }
    )


def _scenarios() -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    for scenario in SCENARIO_INPUTS:
        materialized = deepcopy(scenario)
        interaction_event = materialized.get("interaction_event") or None
        scenarios.append(
            _build_scenario(
                scenario_id=str(materialized["scenario_id"]),
                raw_user_input=str(materialized["raw_user_input"]),
                injected_context=dict(materialized["injected_context"]),
                interaction_event=(
                    _interaction_event(**interaction_event)
                    if isinstance(interaction_event, dict)
                    else None
                ),
            )
        )
    return scenarios


def _validate(scenarios: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    by_id = {str(scenario["scenario_id"]): scenario for scenario in scenarios}

    no_context = by_id["half_sugar_no_context"]
    resolved_target = by_id["half_sugar_resolved_target"]
    pending_followup = by_id["pending_followup_answer"]
    ui_target = by_id["ui_explicit_target_action"]

    if no_context["target_workflow_family"] != "general_chat" or no_context["disposition"] != "defer":
        blockers.append("half_sugar_no_context.runtime_posture_drift")
    if resolved_target["target_workflow_family"] != "intake" or resolved_target["disposition"] != "correct":
        blockers.append("half_sugar_resolved_target.runtime_posture_drift")
    if resolved_target["attachment_reason"] != "resolved_target_reference":
        blockers.append("half_sugar_resolved_target.attachment_reason_drift")
    if pending_followup["target_workflow_family"] != "intake" or pending_followup["disposition"] != "continue":
        blockers.append("pending_followup_answer.runtime_posture_drift")
    if pending_followup["attachment_reason"] != "pending_followup_answer":
        blockers.append("pending_followup_answer.attachment_reason_drift")
    if ui_target["target_workflow_family"] != "intake" or ui_target["disposition"] != "continue":
        blockers.append("ui_explicit_target_action.runtime_posture_drift")
    if ui_target["attachment_reason"] != "explicit_interaction_target":
        blockers.append("ui_explicit_target_action.attachment_reason_drift")
    if no_context["manager_context_promoted_target_resolution_posture"] is not False:
        blockers.append("half_sugar_no_context.unexpected_manager_context_promotion")
    if "followup_or_correction_context" not in resolved_target["promotion_reasons"]:
        blockers.append("half_sugar_resolved_target.missing_manager_context_promotion")
    if "followup_or_correction_context" not in pending_followup["promotion_reasons"]:
        blockers.append("pending_followup_answer.missing_manager_context_promotion")

    for scenario in scenarios:
        scenario_id = str(scenario["scenario_id"])
        if scenario["phase_a_trace_present"] is not True:
            blockers.append(f"{scenario_id}.phase_a_trace_missing")
        if scenario["manager_context_pack_present"] is not True:
            blockers.append(f"{scenario_id}.manager_context_pack_missing")
        if scenario["target_resolution_posture_read_only"] is not True:
            blockers.append(f"{scenario_id}.target_resolution_posture_not_read_only")
        if scenario["candidate_attachment_targets_read_only"] is not True:
            blockers.append(f"{scenario_id}.candidate_targets_not_read_only")
        if scenario["manager_context_current_budget_snapshot_read_only"] is not True:
            blockers.append(f"{scenario_id}.budget_snapshot_not_read_only_in_manager_context")
        if scenario["manager_context_recent_chat_turns_read_only"] is not True:
            blockers.append(f"{scenario_id}.recent_chat_turns_not_read_only_in_manager_context")

    return blockers


def build_context_packet_acceptance_gate_artifact() -> dict[str, Any]:
    scenarios = _scenarios()
    blockers = _validate(scenarios)
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_packet_acceptance_gate",
            "claim_scope": "manager_runtime_context_packet_acceptance_gate",
            "status": "pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "runtime_backed": True,
            "live_llm_invoked": False,
            "fooddb_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": blockers,
            "summary": {
                "scenario_count": len(scenarios),
                "same_utterance_context_switch_cases": 2,
                "pending_followup_cases": 1,
                "ui_target_cases": 1,
            },
            "scenarios": scenarios,
        }
    )


__all__ = ["build_context_packet_acceptance_gate_artifact"]
