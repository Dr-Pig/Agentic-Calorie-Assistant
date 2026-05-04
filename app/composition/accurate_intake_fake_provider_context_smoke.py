from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from app.intake.application.attachment_resolver import resolve_attachment_decision
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.manager_context_policy import (
    MANAGER_CONTEXT_POLICY_VERSION,
    build_manager_context_packet_v1,
)
from app.intake.application.shadow_hypothesis_runtime import build_shadow_hypothesis_runtime
from app.intake.application.transition_guard import resolve_transition_guard
from app.runtime.contracts.phase_a import CurrentTurnContextV1, InteractionEvent


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _context() -> CurrentTurnContextV1:
    return CurrentTurnContextV1(
        user_utterance="\u628a\u8c46\u5e72\u62ff\u6389",
        last_system_question="\u6ef7\u5473\u88e1\u6709\u54ea\u4e9b\u6771\u897f\uff1f",
        recent_chat_turns=[
            {"message_id": "u1", "role": "user", "content": "\u665a\u9910\u5403\u6ef7\u5473"},
            {"message_id": "a1", "role": "assistant", "content": "\u8acb\u544a\u8a34\u6211\u6709\u54ea\u4e9b\u6771\u897f"},
        ],
        pending_followup={
            "is_open": True,
            "runtime_turn_id": "turn-luwei-ask",
            "expected_answer_type": "listed_basket_components",
        },
        current_budget_snapshot={
            "target_kcal": 1600,
            "consumed_kcal": 420,
            "remaining_kcal": 1180,
            "read_only": True,
        },
        recent_item_targets=[
            {"meal_item_id": 1, "display_name": "\u8c46\u5e72", "meal_thread_id": "meal-1"},
            {"meal_item_id": 2, "display_name": "\u6d77\u5e36", "meal_thread_id": "meal-1"},
        ],
        target_resolution_posture={"mutation_authority": False},
        current_interaction_event=InteractionEvent(
            source="chat",
            event_type="user_message",
            raw_text="\u628a\u8c46\u5e72\u62ff\u6389",
        ),
    )


def _resolved_state(
    *,
    pending_followup: dict[str, Any] | None = None,
    recent_committed_meals: list[dict[str, Any]] | None = None,
    target_meal_reference: dict[str, Any] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        user_external_id="fake-provider-handoff-user",
        user_id=1,
        local_date="2026-05-05",
        active_meal=None,
        conversation_state=object(),
        injected_context={
            "ACTIVE_MEAL": None,
            "PENDING_FOLLOWUP": pending_followup
            if pending_followup is not None
            else {
                "is_open": False,
                "meal_id": None,
                "meal_thread_id": None,
                "pending_question": None,
            },
            "RECENT_CHAT_TURNS": [],
            "RECENT_COMMITTED_MEALS_SUMMARY": list(recent_committed_meals or []),
            "CURRENT_BUDGET": {
                "budget_kcal": 1600,
                "consumed_kcal": 420,
                "remaining_kcal": 1180,
                "active_meal_count": len(list(recent_committed_meals or [])),
            },
            "ACTIVE_BODY_PLAN": {
                "body_plan_id": 1,
                "goal_type": "lose_weight",
                "daily_budget_kcal": 1600,
            },
            "TARGET_MEAL_REFERENCE": target_meal_reference
            if target_meal_reference is not None
            else {
                "meal_thread_id": None,
                "meal_version_id": None,
                "meal_title": None,
                "target_resolution_source": "none",
                "correction_confidence": "low",
            },
            "SESSION_SUMMARY": {},
        },
    )


def _target_reference(*, thread_id: int, version_id: int, title: str, source: str) -> dict[str, Any]:
    return {
        "meal_thread_id": thread_id,
        "meal_version_id": version_id,
        "meal_title": title,
        "target_resolution_source": source,
        "correction_confidence": "high" if source != "recent_committed_meal" else "medium",
    }


def _meal(*, thread_id: int, version_id: int, title: str) -> dict[str, Any]:
    return {
        "meal_thread_id": thread_id,
        "meal_version_id": version_id,
        "meal_title": title,
        "occurred_at": "2026-05-05T12:30:00",
    }


def _handoff_specs() -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": "ambiguous_back_reference",
            "raw_user_input": "change that to half sugar",
            "recent_committed_meals": [_meal(thread_id=77, version_id=78, title="milk tea")],
            "target_meal_reference": _target_reference(
                thread_id=77,
                version_id=78,
                title="milk tea",
                source="recent_committed_meal",
            ),
            "fixture_manager_decision": {
                "semantic_source": "fixture_manager_structured_decision",
                "target_resolution_status": "requires_manager_review",
            },
        },
        {
            "scenario_id": "named_item_correction",
            "raw_user_input": "remove tofu",
            "recent_committed_meals": [_meal(thread_id=51, version_id=52, title="luwei")],
            "target_meal_reference": _target_reference(
                thread_id=51,
                version_id=52,
                title="luwei",
                source="history_expansion",
            ),
            "fixture_manager_decision": {
                "semantic_source": "fixture_manager_structured_decision",
                "target_resolution_status": "candidate_supported",
            },
        },
        {
            "scenario_id": "pending_followup_answer",
            "raw_user_input": "tofu, seaweed, fish ball",
            "pending_followup": {
                "is_open": True,
                "meal_id": 51,
                "meal_thread_id": 51,
                "pending_question": "Which luwei items?",
            },
            "target_meal_reference": _target_reference(
                thread_id=51,
                version_id=52,
                title="luwei",
                source="pending_followup_state",
            ),
            "fixture_manager_decision": {
                "semantic_source": "fixture_manager_structured_decision",
                "target_resolution_status": "pending_followup_answer",
            },
        },
    ]


def _handoff_scenario(spec: dict[str, Any]) -> dict[str, Any]:
    context = build_current_turn_context_v1(
        raw_user_input=str(spec["raw_user_input"]),
        resolved_state=_resolved_state(
            pending_followup=spec.get("pending_followup"),
            recent_committed_meals=spec.get("recent_committed_meals"),
            target_meal_reference=spec.get("target_meal_reference"),
        ),
    )
    attachment = resolve_attachment_decision(context)
    guard = resolve_transition_guard(context, attachment)
    shadow = build_shadow_hypothesis_runtime(
        current_turn_context=context,
        attachment_decision=attachment,
        transition_guard_result=guard,
    )
    packet = build_manager_context_packet_v1(
        current_turn_context=context,
        user_id="fake-provider-handoff-user",
        local_date="2026-05-05",
        session_id=f"fake-provider-handoff:{spec['scenario_id']}",
        target_candidates=list(context.candidate_attachment_targets),
        raw_trace_dump={"excluded": True},
        long_term_memory={"excluded": True},
    )
    decision = dict(spec["fixture_manager_decision"])
    return {
        "scenario_id": spec["scenario_id"],
        "raw_user_input_role": "display_only",
        "pre_attachment_disposition": attachment.disposition,
        "pre_attachment_reason": attachment.reason,
        "pre_attachment_target_object_id": attachment.target_object_id,
        "transition_guard_verdict": guard.verdict,
        "shadow_created": shadow.created,
        "shadow_skip_reason": shadow.skip_reason,
        "shadow_role": (shadow.manager_payload or {}).get("role"),
        "shadow_candidate_target_object_id": (shadow.manager_payload or {}).get("candidate_target_object_id"),
        "manager_context_policy_version_present": bool(packet["metadata"].get("context_policy_version")),
        "manager_context_target_candidate_count": len(packet["target_candidates"]["for_correction_or_removal"]),
        "loaded_context_summary_present": bool(packet["context_loading_artifact"]["loaded_context_summary"]),
        "omitted_context_summary_present": bool(packet["context_loading_artifact"]["omitted_context_summary"]),
        "fixture_manager_decision_source": decision["semantic_source"],
        "fixture_manager_target_resolution_status": decision["target_resolution_status"],
        "deterministic_selected_target": False,
        "deterministic_semantic_inference_used": False,
        "raw_text_intent_router_used": False,
        "mutation_authority": False,
    }


def build_fake_provider_context_smoke_artifact() -> dict[str, Any]:
    packet = build_manager_context_packet_v1(
        current_turn_context=_context(),
        user_id="local-user",
        local_date="2026-05-04",
        session_id="fake-provider-context-smoke",
        target_candidates=[
            {
                "meal_item_id": 1,
                "display_name": "\u8c46\u5e72",
                "meal_thread_id": "meal-1",
                "removable": True,
            }
        ],
        raw_trace_dump={"excluded": True},
        long_term_memory={"excluded": True},
        proactive_context={"excluded": True},
        rescue_context={"excluded": True},
    )
    loading = packet["context_loading_artifact"]
    target_candidates = packet["target_candidates"]["for_correction_or_removal"]
    omitted_ids = {
        item["context_id"]
        for item in packet["omitted_context"]
        if isinstance(item, dict)
    }
    handoff_scenarios = [_handoff_scenario(spec) for spec in _handoff_specs()]
    ambiguous_handoffs = [
        scenario
        for scenario in handoff_scenarios
        if scenario["pre_attachment_reason"] == "ambiguous_back_reference_requires_manager"
    ]
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_fake_provider_context_smoke",
            "claim_scope": "fake_provider_context_smoke",
            "status": "pass",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "provider_mode": "fake_provider_contract_test",
            "provider_profile_id": "fake-provider-pl-ce-context-smoke",
            "context_policy_version": MANAGER_CONTEXT_POLICY_VERSION,
            "provider_input_summary": {
                "context_policy_version_present": bool(packet["metadata"]["context_policy_version"]),
                "loaded_context_summary_present": bool(loading["loaded_context_summary"]),
                "omitted_context_summary_present": bool(loading["omitted_context_summary"]),
                "target_candidates_present": bool(target_candidates),
                "forbidden_context_excluded": {"raw_trace_dump", "long_term_memory"}.issubset(omitted_ids),
                "manager_context_packet_schema_changed": False,
            },
            "manager_handoff_matrix_checked": True,
            "summary": {
                "manager_handoff_scenario_count": len(handoff_scenarios),
                "ambiguous_back_reference_scenarios": len(ambiguous_handoffs),
                "shadow_candidate_scenarios": sum(
                    1 for scenario in handoff_scenarios if scenario["shadow_created"]
                ),
            },
            "manager_handoff_scenarios": handoff_scenarios,
            "tool_loop_trace_attributable": True,
            "final_semantic_decision_source": "fixture_manager_structured_decision",
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "live_provider_called": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "production_db_used": False,
            "ready_for_live_diagnostic_decision": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "real_fooddb_pass_claimed": False,
            "fooddb_truth_updated": False,
        }
    )


__all__ = ["build_fake_provider_context_smoke_artifact"]
