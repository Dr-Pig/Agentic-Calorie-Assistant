from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

from app.benchmark_loader import load_benchmark_cases
from app.database import SessionLocal, get_or_create_user
from app.infrastructure.conversation_state_loader import load_conversation_state
from app.schemas import EstimateRequest
from app.usecases.text_meal import run_text_meal_canary


ROOT = Path(__file__).resolve().parents[1]


def test_followup_closure_seed_sources_cover_required_lanes() -> None:
    structured = load_benchmark_cases(ROOT / "tests" / "fixtures" / "benchmark_test_set_v1.json")
    structured_actions = {
        str(case.get("expected_behavior", {}).get("action") or "")
        for case in structured
    }

    text_cases = load_benchmark_cases(ROOT / "docs" / "quality" / "benchmark_test_set_v2.txt")
    text_actions = {
        str(case.get("expected_behavior", {}).get("action") or "")
        for case in text_cases
    }

    assert "ask_followup_only" in structured_actions
    assert "estimate_with_followup" in structured_actions
    assert "direct_estimate" in structured_actions
    assert "ask_followup_only" in text_actions
    assert "estimate_with_followup" in text_actions


def test_two_turn_ask_followup_only_closes_same_intake_without_memory_dependency(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")
    db = SessionLocal()
    try:
        user_id = f"followup-ask-only-{uuid4().hex}"
        get_or_create_user(db, user_id)

        class FirstTurnPlanner:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                return {
                    "intent": "food_estimation",
                    "scope": "meal_specific",
                    "meal_link_action": "create_new_meal",
                    "target_meal_id": None,
                    "link_confidence": "high",
                    "boundary_reason": "new_meal",
                    "clarification_blocking": False,
                    "normalized_user_input": user_payload["current_user_input"],
                }, {"stage": stage}

        class AskOnlyPrimary:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                if stage == "decision_pass":
                    return {
                        "next_action": "run_clarify",
                        "tool_plan": "none",
                        "decision_confidence": "high",
                        "clarify_priority": "menu_item_identity",
                        "unresolved_info": ["menu_item_identity"],
                        "response_mode_hint": "clarify_first",
                        "clarify_is_blocking": True,
                        "can_proceed_without_clarify": False,
                    }, {"stage": stage}
                if stage == "final_response_pass":
                    return {
                        "reply_text": "Which MOS item did you eat?",
                        "ui_hints": {},
                    }, {"stage": stage}
                raise AssertionError(f"unexpected stage: {stage}")

        first = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="I ate MOS Burger for breakfast", allow_search=False, user_id=user_id),
                provider=AskOnlyPrimary(),
                planner_provider=FirstTurnPlanner(),
                primary_provider=AskOnlyPrimary(),
                request_id="followup-ask-only-turn-1",
                search_adapter=None,
                db=db,
            )
        )

        first_persistence = first.trace_contract["persistence_decision"]
        first_log_id = first_persistence["persisted_log_id"]
        assert first_persistence["status"] == "draft_unresolved"
        assert first_persistence["canonical_commit"] is None
        assert first.used_search is False
        assert first_log_id is not None

        state_after_first = load_conversation_state(db, user_id=user_id, incoming_user_text=None).state
        assert state_after_first.pending_followup_state.is_open is True
        assert state_after_first.pending_followup_state.source_meal_id == first_log_id

        class SecondTurnPlanner:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                return {
                    "intent": "clarification",
                    "scope": "meal_specific",
                    "meal_link_action": "attach_to_existing_meal",
                    "target_meal_id": first_log_id,
                    "link_confidence": "high",
                    "boundary_reason": "same_meal_followup",
                    "clarification_blocking": False,
                    "normalized_user_input": user_payload["current_user_input"],
                }, {"stage": stage}

        class CompletionPrimary:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                if stage == "decision_pass":
                    return {
                        "next_action": "run_nutrition_resolution",
                        "tool_plan": "none",
                        "decision_confidence": "high",
                        "clarify_priority": None,
                        "unresolved_info": [],
                        "response_mode_hint": "rough_estimate_ok",
                        "clarify_is_blocking": False,
                        "can_proceed_without_clarify": True,
                    }, {"stage": stage}
                if stage == "nutrition_resolution_pass_initial":
                    return {
                        "action_taken": "direct_answer",
                        "resolution_mode": "provisional_estimate",
                        "resolution_basis": "component_model",
                        "exactness": "best_effort",
                        "estimate_mode": "anchored_component",
                        "confidence": "medium",
                        "response_mode_hint": "rough_estimate_ok",
                        "tool_request": "none",
                        "tool_request_reason": "",
                        "state_transition_hint": "completed_meal",
                        "food_origin": "restaurant_chain",
                        "food_class": "combo_meal",
                        "needs_external_data": False,
                        "private_info_risk": "low",
                        "title": "MOS plum pork burger + black tea",
                        "components": ["MOS plum pork burger", "black tea"],
                        "protein_g": 20,
                        "carb_g": 54,
                        "fat_g": 18,
                        "kcal_low": 500,
                        "kcal_high": 560,
                        "kcal_most_likely": 530,
                        "uncertainty_factors": [],
                        "follow_up_needed": False,
                        "follow_up_question": "",
                        "follow_up_reasoning": "",
                        "followup_questions": [],
                        "top_uncertainty_drivers": [],
                        "external_data_query": "",
                        "answer_payload": {},
                    }, {"stage": stage}
                if stage == "final_response_pass":
                    return {
                        "reply_text": "MOS plum pork burger plus black tea is about 530 kcal.",
                        "ui_hints": {},
                    }, {"stage": stage}
                raise AssertionError(f"unexpected stage: {stage}")

        second = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="It was plum pork burger plus black tea", allow_search=False, user_id=user_id),
                provider=CompletionPrimary(),
                planner_provider=SecondTurnPlanner(),
                primary_provider=CompletionPrimary(),
                request_id="followup-ask-only-turn-2",
                search_adapter=None,
                db=db,
            )
        )

        second_persistence = second.trace_contract["persistence_decision"]
        assert second.boundary_trace["meal_boundary"] == "continue_active_meal"
        assert second.boundary_trace["active_meal_context_allowed"] is True
        assert second.used_search is False
        assert second_persistence["parent_log_id"] == first_log_id
        assert second_persistence["canonical_commit"] is not None

        state_after_second = load_conversation_state(db, user_id=user_id, incoming_user_text=None).state
        assert state_after_second.pending_followup_state.is_open is False
    finally:
        db.close()


def test_two_turn_estimate_with_followup_refines_same_intake_without_duplicate_thread(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")
    db = SessionLocal()
    try:
        user_id = f"followup-estimate-{uuid4().hex}"
        get_or_create_user(db, user_id)

        class FirstTurnPlanner:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                return {
                    "intent": "food_estimation",
                    "scope": "meal_specific",
                    "meal_link_action": "create_new_meal",
                    "target_meal_id": None,
                    "link_confidence": "high",
                    "boundary_reason": "new_meal",
                    "clarification_blocking": False,
                    "normalized_user_input": user_payload["current_user_input"],
                }, {"stage": stage}

        class EstimateWithFollowupPrimary:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                if stage == "decision_pass":
                    return {
                        "next_action": "run_nutrition_resolution",
                        "tool_plan": "none",
                        "decision_confidence": "high",
                        "clarify_priority": None,
                        "unresolved_info": [],
                        "response_mode_hint": "rough_estimate_ok",
                        "clarify_is_blocking": False,
                        "can_proceed_without_clarify": True,
                    }, {"stage": stage}
                if stage == "nutrition_resolution_pass_initial":
                    return {
                        "action_taken": "answer_with_uncertainty",
                        "resolution_mode": "provisional_estimate",
                        "resolution_basis": "component_model",
                        "exactness": "unknown",
                        "estimate_mode": "llm_only",
                        "confidence": "medium",
                        "response_mode_hint": "rough_estimate_ok",
                        "tool_request": "none",
                        "tool_request_reason": "",
                        "state_transition_hint": "draft_unresolved",
                        "food_origin": "generic_common",
                        "food_class": "customizable_drink",
                        "needs_external_data": False,
                        "private_info_risk": "low",
                        "title": "bubble milk tea",
                        "components": ["bubble milk tea"],
                        "protein_g": 3,
                        "carb_g": 62,
                        "fat_g": 9,
                        "kcal_low": 360,
                        "kcal_high": 500,
                        "kcal_most_likely": 420,
                        "uncertainty_factors": ["cup_size_missing"],
                        "follow_up_needed": True,
                        "followup_question": "What size was it?",
                        "follow_up_reasoning": "size materially changes estimate",
                        "followup_questions": [],
                        "top_uncertainty_drivers": ["cup_size"],
                        "external_data_query": "",
                        "unresolved_info": ["cup_size"],
                        "answer_payload": {},
                    }, {"stage": stage}
                if stage == "final_response_pass":
                    return {
                        "reply_text": "Bubble milk tea is about 420 kcal for now. What size was it?",
                        "asked_follow_up": True,
                        "ui_hints": {},
                    }, {"stage": stage}
                raise AssertionError(f"unexpected stage: {stage}")

        first = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="I drank bubble milk tea", allow_search=False, user_id=user_id),
                provider=EstimateWithFollowupPrimary(),
                planner_provider=FirstTurnPlanner(),
                primary_provider=EstimateWithFollowupPrimary(),
                request_id="followup-estimate-turn-1",
                search_adapter=None,
                db=db,
            )
        )

        first_persistence = first.trace_contract["persistence_decision"]
        first_log_id = first_persistence["persisted_log_id"]
        assert first_persistence["status"] == "draft_unresolved"
        assert first_persistence["canonical_commit"] is None
        assert first.estimated_kcal == 420
        assert first.used_search is False
        assert first_log_id is not None

        state_after_first = load_conversation_state(db, user_id=user_id, incoming_user_text=None).state
        assert state_after_first.pending_followup_state.is_open is True
        assert state_after_first.pending_followup_state.source_meal_id == first_log_id

        class SecondTurnPlanner:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                return {
                    "intent": "clarification",
                    "scope": "meal_specific",
                    "meal_link_action": "attach_to_existing_meal",
                    "target_meal_id": first_log_id,
                    "link_confidence": "high",
                    "boundary_reason": "same_meal_followup",
                    "clarification_blocking": False,
                    "normalized_user_input": user_payload["current_user_input"],
                }, {"stage": stage}

        class RefinementPrimary:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                if stage == "decision_pass":
                    return {
                        "next_action": "run_nutrition_resolution",
                        "tool_plan": "none",
                        "decision_confidence": "high",
                        "clarify_priority": None,
                        "unresolved_info": [],
                        "response_mode_hint": "rough_estimate_ok",
                        "clarify_is_blocking": False,
                        "can_proceed_without_clarify": True,
                    }, {"stage": stage}
                if stage == "nutrition_resolution_pass_initial":
                    return {
                        "action_taken": "direct_answer",
                        "resolution_mode": "provisional_estimate",
                        "resolution_basis": "component_model",
                        "exactness": "best_effort",
                        "estimate_mode": "anchored_component",
                        "confidence": "medium",
                        "response_mode_hint": "rough_estimate_ok",
                        "tool_request": "none",
                        "tool_request_reason": "",
                        "state_transition_hint": "completed_meal",
                        "food_origin": "generic_common",
                        "food_class": "customizable_drink",
                        "needs_external_data": False,
                        "private_info_risk": "low",
                        "title": "bubble milk tea",
                        "components": ["bubble milk tea"],
                        "protein_g": 4,
                        "carb_g": 70,
                        "fat_g": 10,
                        "kcal_low": 500,
                        "kcal_high": 560,
                        "kcal_most_likely": 530,
                        "uncertainty_factors": [],
                        "follow_up_needed": False,
                        "follow_up_question": "",
                        "follow_up_reasoning": "",
                        "followup_questions": [],
                        "top_uncertainty_drivers": [],
                        "external_data_query": "",
                        "answer_payload": {},
                    }, {"stage": stage}
                if stage == "final_response_pass":
                    return {
                        "reply_text": "Medium half-sugar bubble milk tea is about 530 kcal.",
                        "ui_hints": {},
                    }, {"stage": stage}
                raise AssertionError(f"unexpected stage: {stage}")

        second = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="Medium, half sugar, less ice", allow_search=False, user_id=user_id),
                provider=RefinementPrimary(),
                planner_provider=SecondTurnPlanner(),
                primary_provider=RefinementPrimary(),
                request_id="followup-estimate-turn-2",
                search_adapter=None,
                db=db,
            )
        )

        second_persistence = second.trace_contract["persistence_decision"]
        assert second.boundary_trace["meal_boundary"] == "continue_active_meal"
        assert second.boundary_trace["active_meal_context_allowed"] is True
        assert second.used_search is False
        assert second_persistence["parent_log_id"] == first_log_id
        assert second_persistence["canonical_commit"] is not None

        state_after_second = load_conversation_state(db, user_id=user_id, incoming_user_text=None).state
        assert state_after_second.pending_followup_state.is_open is False
    finally:
        db.close()
