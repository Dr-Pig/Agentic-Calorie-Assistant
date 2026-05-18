from __future__ import annotations

from datetime import UTC, datetime
import json
from types import SimpleNamespace
from typing import Any

from app.intake.application.attachment_resolver import resolve_attachment_decision
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.manager_context_policy import build_manager_context_packet_v1


_REQUIRED_SCENARIO_IDS = (
    "remove_previous_item",
    "remove_named_item",
    "modify_drink_sugar",
    "modify_rice_portion",
    "correct_previous_identity",
    "pending_followup_answer",
    "long_chat_with_pinned_pending_draft",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _resolved_state(
    *,
    local_date: str,
    pending_followup: dict[str, Any] | None = None,
    pending_draft: dict[str, Any] | None = None,
    recent_chat_turns: list[dict[str, Any]] | None = None,
    recent_committed_meals: list[dict[str, Any]] | None = None,
    target_meal_reference: dict[str, Any] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        user_external_id="short-term-context-runtime-replay-user",
        user_id=1,
        local_date=local_date,
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
            "RECENT_CHAT_TURNS": list(recent_chat_turns or []),
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
            "SESSION_SUMMARY": {
                "latest_assistant_turns": [
                    str(pending_followup.get("pending_question") or "")
                    for pending_followup in [pending_followup]
                    if isinstance(pending_followup, dict) and pending_followup.get("pending_question")
                ]
            },
        },
        pending_draft=pending_draft,
    )


def _meal(
    *,
    thread_id: int,
    version_id: int,
    title: str,
    item_names: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "meal_thread_id": thread_id,
        "meal_version_id": version_id,
        "meal_title": title,
        "occurred_at": "2026-05-05T12:30:00",
        "item_resolution_source": "runtime_replay_fixture_state",
        "item_candidates": [
            {
                "meal_item_id": thread_id * 100 + index,
                "canonical_name": item_name,
                "item_index": index,
                "estimated_kcal": 100 + index * 20,
                "mutation_authority": False,
                "selected_target": False,
            }
            for index, item_name in enumerate(item_names, start=1)
        ],
    }


def _recent_chat(count: int) -> list[dict[str, Any]]:
    return [
        {
            "message_id": index,
            "role": "user" if index % 2 else "assistant",
            "content": f"context replay prior turn {index}",
            "created_at": f"2026-05-05T10:{index % 60:02d}:00",
            "trace_id": f"prior-{index}",
            "local_date": "2026-05-05",
            "read_only": True,
            "mutation_authority": False,
            "source": "runtime_replay_fixture_state",
        }
        for index in range(1, count + 1)
    ]


def _target_reference(
    *,
    thread_id: int,
    version_id: int,
    title: str,
    source: str,
    confidence: str = "high",
    item_id: int | None = None,
    canonical_name: str | None = None,
) -> dict[str, Any]:
    ref: dict[str, Any] = {
        "meal_thread_id": thread_id,
        "meal_version_id": version_id,
        "meal_title": title,
        "target_resolution_source": source,
        "correction_confidence": confidence,
        "item_resolution_source": "runtime_replay_fixture_state",
    }
    if item_id is not None:
        ref["meal_item_id"] = item_id
    if canonical_name is not None:
        ref["canonical_name"] = canonical_name
    return ref


def _scenario_specs() -> list[dict[str, Any]]:
    drink_meal = _meal(thread_id=31, version_id=310, title="bubble tea", item_names=("bubble tea",))
    rice_meal = _meal(thread_id=41, version_id=410, title="lunch rice", item_names=("rice", "egg"))
    luwei_meal = _meal(thread_id=51, version_id=510, title="luwei", item_names=("tofu", "seaweed", "fish ball"))
    return [
        {
            "scenario_id": "remove_previous_item",
            "raw_user_input": "把剛剛那個拿掉",
            "expected_context_posture": "ambiguous_until_manager_decision",
            "recent_committed_meals": [luwei_meal],
            "target_meal_reference": _target_reference(
                thread_id=51,
                version_id=510,
                title="luwei",
                source="recent_committed_meal",
                confidence="medium",
            ),
        },
        {
            "scenario_id": "remove_named_item",
            "raw_user_input": "豆干拿掉",
            "expected_context_posture": "candidate_supported",
            "recent_committed_meals": [luwei_meal],
        },
        {
            "scenario_id": "modify_drink_sugar",
            "raw_user_input": "那杯改半糖",
            "expected_context_posture": "candidate_supported",
            "recent_committed_meals": [drink_meal],
        },
        {
            "scenario_id": "modify_rice_portion",
            "raw_user_input": "飯改少一點",
            "expected_context_posture": "candidate_supported",
            "recent_committed_meals": [rice_meal],
        },
        {
            "scenario_id": "correct_previous_identity",
            "raw_user_input": "剛剛那個其實不是拿鐵",
            "expected_context_posture": "ambiguous_until_manager_decision",
            "recent_committed_meals": [drink_meal],
            "target_meal_reference": _target_reference(
                thread_id=31,
                version_id=310,
                title="drink",
                source="recent_committed_meal",
                confidence="medium",
            ),
        },
        {
            "scenario_id": "pending_followup_answer",
            "raw_user_input": "有豆干、海帶、貢丸",
            "expected_context_posture": "pending_followup_pinned",
            "pending_followup": {
                "is_open": True,
                "meal_id": 51,
                "meal_thread_id": 51,
                "pending_question": "請列出滷味品項",
                "expected_answer_type": "listed_basket_components",
            },
            "target_meal_reference": _target_reference(
                thread_id=51,
                version_id=510,
                title="luwei",
                source="pending_followup_state",
            ),
        },
        {
            "scenario_id": "long_chat_with_pinned_pending_draft",
            "raw_user_input": "剛剛那份滷味裡還有米血",
            "expected_context_posture": "pending_draft_pinned_despite_recent_window",
            "recent_chat_turns": _recent_chat(28),
            "pending_draft": {
                "meal_thread_id": 61,
                "meal_version_id": 610,
                "meal_title": "luwei draft",
                "resolution_status": "draft_unresolved",
            },
            "target_meal_reference": _target_reference(
                thread_id=61,
                version_id=610,
                title="luwei draft",
                source="pending_draft_state",
            ),
        },
    ]


def _scenario_result(spec: dict[str, Any]) -> dict[str, Any]:
    local_date = "2026-05-05"
    resolved_state = _resolved_state(
        local_date=local_date,
        pending_followup=spec.get("pending_followup"),
        pending_draft=spec.get("pending_draft"),
        recent_chat_turns=spec.get("recent_chat_turns"),
        recent_committed_meals=spec.get("recent_committed_meals"),
        target_meal_reference=spec.get("target_meal_reference"),
    )
    current_turn_context = build_current_turn_context_v1(
        raw_user_input=str(spec["raw_user_input"]),
        resolved_state=resolved_state,
    )
    if spec.get("recent_chat_turns"):
        # Mirror manager_context_runtime: the runtime packet loads the bounded
        # same-day message buffer directly instead of relying on the smaller
        # current-turn summary window.
        current_turn_context = current_turn_context.model_copy(
            update={"recent_chat_turns": list(spec["recent_chat_turns"])}
        )
    packet = build_manager_context_packet_v1(
        current_turn_context=current_turn_context,
        user_id="short-term-context-runtime-replay-user",
        local_date=local_date,
        session_id=f"runtime-replay:{spec['scenario_id']}",
        manager_mode="fixture",
        pending_draft=spec.get("pending_draft"),
    )
    attachment = resolve_attachment_decision(current_turn_context)
    loading = packet["context_loading_artifact"]
    loaded = loading["loaded_context_summary"]
    omitted = loading["omitted_context_summary"]
    target_candidates = list(packet["target_candidates"]["for_correction_or_removal"])
    forbidden_detected = any(
        context_id in packet
        for context_id in (
            "debug_artifacts",
            "dogfood_review_artifacts",
            "raw_trace_dump",
            "food_gap_candidates",
            "long_term_memory",
            "proactive_context",
            "rescue_context",
            "recommendation_context",
        )
    )
    gap_signals: list[str] = []
    if (
        spec["expected_context_posture"] == "ambiguous_until_manager_decision"
        and attachment.reason == "identified_back_reference_target"
    ):
        gap_signals.append("runtime_back_reference_heuristic_attached_target")
    deterministic_selected_target = (
        spec["expected_context_posture"] == "candidate_supported"
        and attachment.target_object_id is not None
    )
    return {
        "scenario_id": spec["scenario_id"],
        "raw_user_input": spec["raw_user_input"],
        "raw_user_input_role": "display_only",
        "expected_context_posture": spec["expected_context_posture"],
        "semantic_source": "manager_or_fixture_structured_decision_required",
        "runtime_attachment_reason": attachment.reason,
        "runtime_attachment_disposition": attachment.disposition,
        "runtime_attachment_target_object_id": attachment.target_object_id,
        "context_policy_version_present": bool(packet["metadata"].get("context_policy_version")),
        "loaded_context_summary_present": bool(loaded),
        "omitted_context_summary_present": bool(omitted),
        "pending_followup_present": packet["hard_pins"]["pending_followup"] is not None,
        "pending_draft_present": packet["hard_pins"]["pending_draft"] is not None,
        "target_candidate_count": len(target_candidates),
        "target_candidates": target_candidates,
        "recent_chat_messages_loaded": int(loaded.get("recent_chat_messages") or 0),
        "recent_chat_messages_omitted": int(omitted.get("recent_chat_messages_omitted") or 0),
        "forbidden_context_detected": forbidden_detected,
        "context_packet_read_only": packet["current_turn"]["read_only"] is True,
        "context_packet_mutation_authority": packet["current_turn"]["mutation_authority"],
        "deterministic_selected_target": deterministic_selected_target,
        "deterministic_semantic_inference_used": False,
        "raw_text_intent_router_used": False,
        "mutation_authority": False,
        "gap_signals": gap_signals,
    }


def _validate_scenarios(scenarios: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    scenario_ids = [str(scenario.get("scenario_id") or "") for scenario in scenarios]
    if scenario_ids != list(_REQUIRED_SCENARIO_IDS):
        blockers.append("required_scenario_order_mismatch")
    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id") or "unknown")
        expected_posture = str(scenario.get("expected_context_posture") or "")
        if scenario.get("context_policy_version_present") is not True:
            blockers.append(f"{scenario_id}.context_policy_version_missing")
        if scenario.get("loaded_context_summary_present") is not True:
            blockers.append(f"{scenario_id}.loaded_context_summary_missing")
        if scenario.get("omitted_context_summary_present") is not True:
            blockers.append(f"{scenario_id}.omitted_context_summary_missing")
        if scenario.get("forbidden_context_detected") is not False:
            blockers.append(f"{scenario_id}.forbidden_context_detected")
        if scenario.get("context_packet_read_only") is not True:
            blockers.append(f"{scenario_id}.context_packet_not_read_only")
        if scenario.get("context_packet_mutation_authority") is not False:
            blockers.append(f"{scenario_id}.context_packet_mutation_authority")
        if scenario.get("deterministic_selected_target") is not False:
            blockers.append(f"{scenario_id}.deterministic_selected_target")
        if scenario.get("deterministic_semantic_inference_used") is not False:
            blockers.append(f"{scenario_id}.deterministic_semantic_inference_used")
        if scenario.get("raw_text_intent_router_used") is not False:
            blockers.append(f"{scenario_id}.raw_text_intent_router_used")
        if scenario.get("mutation_authority") is not False:
            blockers.append(f"{scenario_id}.mutation_authority")
        if scenario.get("semantic_source") != "manager_or_fixture_structured_decision_required":
            blockers.append(f"{scenario_id}.semantic_source_not_manager_or_fixture")
        for candidate in scenario.get("target_candidates") or []:
            if isinstance(candidate, dict):
                if candidate.get("read_only") is not True:
                    blockers.append(f"{scenario_id}.target_candidate_not_read_only")
                if candidate.get("mutation_authority") is not False:
                    blockers.append(f"{scenario_id}.target_candidate_mutation_authority")
                if "selected_target" in candidate:
                    blockers.append(f"{scenario_id}.target_candidate_selected_by_runtime")
        if expected_posture == "ambiguous_until_manager_decision":
            if scenario.get("runtime_attachment_reason") != "ambiguous_back_reference_requires_manager":
                blockers.append(f"{scenario_id}.back_reference_not_ambiguous")
            if scenario.get("runtime_attachment_disposition") != "answer_only":
                blockers.append(f"{scenario_id}.ambiguous_back_reference_not_answer_only")
        if expected_posture == "candidate_supported":
            if int(scenario.get("target_candidate_count") or 0) < 1:
                blockers.append(f"{scenario_id}.candidate_target_missing")
            if scenario.get("runtime_attachment_target_object_id") is not None:
                blockers.append(f"{scenario_id}.candidate_supported_runtime_selected_target")
        if expected_posture == "pending_followup_pinned":
            if scenario.get("pending_followup_present") is not True:
                blockers.append(f"{scenario_id}.pending_followup_missing")
            if scenario.get("runtime_attachment_reason") != "pending_followup_requires_manager_resolution":
                blockers.append(f"{scenario_id}.pending_followup_manager_resolution_missing")
            if scenario.get("runtime_attachment_disposition") != "answer_only":
                blockers.append(f"{scenario_id}.pending_followup_not_manager_owned")
        if expected_posture == "pending_draft_pinned_despite_recent_window":
            if scenario.get("pending_draft_present") is not True:
                blockers.append(f"{scenario_id}.pending_draft_missing")
            if int(scenario.get("recent_chat_messages_loaded") or 0) != 20:
                blockers.append(f"{scenario_id}.recent_chat_window_not_bounded")
            if int(scenario.get("recent_chat_messages_omitted") or 0) <= 0:
                blockers.append(f"{scenario_id}.recent_chat_omission_not_recorded")
            if int(scenario.get("target_candidate_count") or 0) < 1:
                blockers.append(f"{scenario_id}.pending_draft_candidate_missing")
            if scenario.get("runtime_attachment_target_object_id") is not None:
                blockers.append(f"{scenario_id}.pending_draft_runtime_selected_target")
    return list(dict.fromkeys(blockers))


def build_short_term_context_runtime_replay_artifact() -> dict[str, Any]:
    scenarios = [_scenario_result(spec) for spec in _scenario_specs()]
    gap_scenarios = [scenario for scenario in scenarios if scenario["gap_signals"]]
    blockers = _validate_scenarios(scenarios)
    status = "runtime_replay_diagnostic_pass"
    if blockers:
        status = "fail"
    elif gap_scenarios:
        status = "diagnostic_has_known_context_gaps"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_short_term_context_runtime_replay",
            "status": status,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pl_ce_short_term_context_runtime_replay_diagnostic",
            "blockers": blockers,
            "local_only": True,
            "diagnostic_only": True,
            "runtime_trace_backed": True,
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_supplies_candidates_and_pins_only": True,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "scenario_count": len(scenarios),
            "summary": {
                "scenario_count": len(scenarios),
                "pending_pin_scenarios": sum(
                    1 for scenario in scenarios if scenario["pending_followup_present"]
                    or scenario["pending_draft_present"]
                ),
                "target_candidate_scenarios": sum(
                    1 for scenario in scenarios if scenario["target_candidate_count"] > 0
                ),
                "current_gap_scenarios": len(gap_scenarios),
                "known_gap_signals": sorted({signal for scenario in scenarios for signal in scenario["gap_signals"]}),
            },
            "scenarios": scenarios,
        }
    )


__all__ = ["build_short_term_context_runtime_replay_artifact"]
