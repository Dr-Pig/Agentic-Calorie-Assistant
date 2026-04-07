from __future__ import annotations

import asyncio

from app.agent.decision_llm import normalize_decision_result
from app.agent.final_response_llm import sanitize_final_response_result
from app.agent.nutrition_resolution_llm import normalize_structured_answer, nutrition_result_from_primary
from app.agent.task_meal_link_llm import normalize_task_meal_link_result
from app.application.context_assembly import build_decision_payload
from app.application.evidence_assembly import build_partial_grounding_packet, infer_expected_components
from app.application.nutrition_invariants import apply_nutrition_invariant_guards
from app.application.pass_runner import run_pass
from app.application.planner import normalize_planner_result
from app.application.state_transition import build_canonical_meal_state
from app.domain import ConversationState
from app.providers.builderspace_adapter import BuilderSpaceAdapter, BuilderSpaceResponseError
from app.schemas import DecisionPassResult, FinalResponseResult, NutritionResolutionResult, TaskMealLinkResult
from app.usecases.text_meal import _run_text_stage


def test_build_canonical_meal_state_supports_followup_fields() -> None:
    followup_question = "portion question"
    state = build_canonical_meal_state(
        meal_id=123,
        meal_title="beef noodle soup",
        status="draft_unresolved",
        followup_count=2,
        asked_questions_history=[followup_question, followup_question],
        last_followup_key=followup_question,
    )

    assert state.followup_count == 2
    assert state.last_followup_key == followup_question
    assert state.asked_questions_history[-1] == followup_question


def test_run_pass_retries_once_and_marks_degraded() -> None:
    class FakeProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary failure")
            return {"intent": "food_estimation"}, {"stage": stage}

    fallback = TaskMealLinkResult()

    result, envelope = asyncio.run(
        run_pass(
            provider=FakeProvider(),
            stage="task_meal_link_pass",
            system_prompt="x",
            user_payload={},
            max_tokens=32,
            fallback_result=fallback,
            normalize=lambda raw, default: TaskMealLinkResult(
                intent=str(raw.get("intent") or default.intent),  # type: ignore[arg-type]
                scope=default.scope,
                meal_link_action=default.meal_link_action,
                target_meal_id=default.target_meal_id,
                link_confidence=default.link_confidence,
                boundary_reason=default.boundary_reason,
                clarification_blocking=default.clarification_blocking,
                normalized_user_input=default.normalized_user_input,
            ),
            dump=lambda model: model.model_dump(mode="json"),
            run_stage=_run_text_stage,
            request_id="req-1",
            llm_traces=[],
            trigger_reason="task_meal_link",
            required_fields=["intent", "meal_link_action"],
        )
    )

    assert result.intent == "food_estimation"
    assert envelope.status == "degraded"
    assert envelope.fallback_used is True
    assert "attempt=2" in str(envelope.error)


def test_run_pass_failed_error_includes_attempt_number() -> None:
    class FakeProvider:
        async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
            raise RuntimeError("timeout")

    fallback = TaskMealLinkResult()
    _, envelope = asyncio.run(
        run_pass(
            provider=FakeProvider(),
            stage="task_meal_link_pass",
            system_prompt="x",
            user_payload={},
            max_tokens=32,
            fallback_result=fallback,
            normalize=lambda raw, default: default,
            dump=lambda model: model.model_dump(mode="json"),
            run_stage=_run_text_stage,
            request_id="req-2",
            llm_traces=[],
            trigger_reason="task_meal_link",
            required_fields=["intent"],
        )
    )
    assert envelope.status == "failed"
    assert "attempt=2" in str(envelope.error)


def test_run_pass_collects_exception_trace_payload() -> None:
    class FakeProvider:
        async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
            raise BuilderSpaceResponseError(
                "transport failed",
                trace={
                    "stage": stage,
                    "provider": "builderspace",
                    "transport_attempts": [{"attempt_index": 1, "error_type": "ConnectError"}],
                },
            )

    fallback = TaskMealLinkResult()
    llm_traces: list[dict[str, object]] = []
    _, envelope = asyncio.run(
        run_pass(
            provider=FakeProvider(),
            stage="task_meal_link_pass",
            system_prompt="x",
            user_payload={},
            max_tokens=32,
            fallback_result=fallback,
            normalize=lambda raw, default: default,
            dump=lambda model: model.model_dump(mode="json"),
            run_stage=_run_text_stage,
            request_id="req-trace",
            llm_traces=llm_traces,
            trigger_reason="task_meal_link",
            required_fields=["intent"],
        )
    )

    assert envelope.status == "failed"
    assert llm_traces
    assert llm_traces[0]["provider"] == "builderspace"
    assert llm_traces[0]["transport_attempts"] == [{"attempt_index": 1, "error_type": "ConnectError"}]


def test_builderspace_adapter_skips_gemini_extra_body_for_grok() -> None:
    adapter = BuilderSpaceAdapter()

    assert adapter._extra_body_for_stage("decision_pass", model="grok-4-fast") is None
    assert adapter._extra_body_for_stage("decision_pass", model="gemini-2.5-pro") is not None


def test_invariant_guard_flags_exact_label_mismatch_but_keeps_portion_reasoning() -> None:
    result = NutritionResolutionResult(
        resolution_mode="exact_label_finalize",
        resolution_basis="exact_item_evidence",
        confidence="high",
        exactness="exact_item",
        answer_payload={
            "title": "latte",
            "estimated_kcal": 212,
            "protein_g": 6,
            "carb_g": 27,
            "fat_g": 7,
            "base_estimated_kcal": 400,
            "base_protein_g": 12,
            "base_carb_g": 54,
            "base_fat_g": 14,
            "portion_multiplier": 0.5,
            "portion_reason": "size adjustment",
        },
        unresolved_info=[],
        state_transition_hint="completed_meal",
    )
    normalized_evidence = [
        {
            "source_type": "local_retrieval",
            "match_quality": "high",
            "raw": {
                "source_class": "exact_item_db",
                "identity_confidence": "high",
                "title": "latte",
                "label_kcal": 423,
                "label_macros": {"protein_g": 12, "carb_g": 54, "fat_g": 14},
            },
        }
    ]

    adjusted, meta = apply_nutrition_invariant_guards(result=result, normalized_evidence=normalized_evidence)

    assert adjusted.answer_payload["estimated_kcal"] == 212
    assert adjusted.answer_payload["portion_multiplier"] == 0.5
    assert "flag_exact_label_mismatch" in meta["guard_actions"]


def test_invariant_guard_does_not_veto_resolution_mode_on_large_macro_delta() -> None:
    result = NutritionResolutionResult(
        resolution_mode="provisional_estimate",
        resolution_basis="component_model",
        confidence="high",
        exactness="component_grounded",
        answer_payload={
            "title": "beef fried rice",
            "estimated_kcal": 850,
            "protein_g": 10,
            "carb_g": 20,
            "fat_g": 5,
        },
        unresolved_info=[],
        state_transition_hint="draft_unresolved",
    )

    adjusted, meta = apply_nutrition_invariant_guards(result=result, normalized_evidence=[])

    assert adjusted.resolution_mode == "provisional_estimate"
    assert adjusted.answer_payload["estimated_kcal"] == 850
    assert "fallback_to_cannot_estimate_yet" not in meta["guard_actions"]
    assert meta["macro_delta"] is not None


def test_task_meal_link_normalizer_accepts_live_legacy_shape() -> None:
    fallback = TaskMealLinkResult()
    raw = {
        "is_food_related": True,
        "meal_link_decision": "new_intake",
        "candidate_meal_id": 72,
        "reasoning": "legacy provider shape",
    }

    normalized = normalize_task_meal_link_result(
        raw,
        fallback=fallback,
        state=ConversationState(user_id="u1"),
    )

    assert normalized.intent == "food_estimation"
    assert normalized.meal_link_action == "create_new_meal"
    assert normalized.target_meal_id == 72
    assert normalized.clarification_blocking is False


def test_decision_payload_includes_current_user_input_and_scopes_new_meal_state() -> None:
    meal_state = build_canonical_meal_state(
        meal_id=88,
        meal_title="rice bowl",
        status="draft_unresolved",
    )
    payload = build_decision_payload(
        user_input="two rice balls and soy milk",
        meal_state=meal_state,
        meal_link_result=TaskMealLinkResult(meal_link_action="create_new_meal"),
        selected_evidence_summary=[],
        available_tools=[],
    )
    assert payload["current_user_input"] == "two rice balls and soy milk"
    assert payload["canonical_meal_state"] == {}


def test_final_response_sanitizer_blocks_zero_kcal_fallback_language() -> None:
    nutrition = NutritionResolutionResult(
        resolution_mode="cannot_estimate_yet",
        resolution_basis="component_model",
        confidence="low",
        exactness="unknown",
        answer_payload={"estimated_kcal": 0, "protein_g": 0, "carb_g": 0, "fat_g": 0},
        unresolved_info=["portion_size"],
        state_transition_hint="draft_unresolved",
    )
    fallback = FinalResponseResult(reply_text="需要份量資訊才能更準。", asked_follow_up=True, ui_hints={})
    raw = FinalResponseResult(reply_text="目前是 0 kcal，蛋白質 0g、碳水 0g、脂肪 0g。", asked_follow_up=False, ui_hints={})

    adjusted = sanitize_final_response_result(
        result=raw,
        nutrition_result=nutrition,
        fallback=fallback,
    )

    assert adjusted.reply_text == fallback.reply_text
    assert adjusted.asked_follow_up is True


def test_normalize_structured_answer_accepts_live_aliases_and_item_groups() -> None:
    normalized = normalize_structured_answer(
        {
            "resolution_mode": "provisional_estimate",
            "resolution_basis": "named_dish_with_portion_clue",
            "confidence": "medium_low",
            "calories_kcal": 520,
            "protein_g": 18,
            "carbs_g": 65,
            "fat_g": 18,
            "items": [
                {"title": "sandwich", "estimated_kcal": 420, "protein_g": 14, "carb_g": 45, "fat_g": 16},
                {"title": "black tea", "estimated_kcal": 100, "protein_g": 0, "carb_g": 20, "fat_g": 0},
            ],
        },
        user_text="breakfast set",
    )

    assert normalized["estimated_kcal"] == 520
    assert normalized["carb_g"] == 65
    assert normalized["confidence"] == "medium"
    assert normalized["answer_payload"]["items"][0]["title"] == "sandwich"
    assert normalized["answer_payload"]["items"][1]["estimated_kcal"] == 100


def test_normalize_planner_result_prefers_planning_brief_intent_when_conflicted() -> None:
    planner_result = normalize_planner_result(
        {
            "intent": "clarification",
            "meal_boundary": "boundary_clarification",
            "normalized_user_input": "beef rice",
            "planning_brief": {
                "intent": "food_estimation",
                "slot_state": "enough_to_estimate",
                "resolved_query": "beef rice",
            },
        },
        raw_user_input="beef rice",
        normalize_text=lambda text: text,
        normalize_user_input_for_estimation=lambda text: {"normalized_text": text, "normalizer_applied": False, "notes": []},
    )

    assert planner_result.intent == "food_estimation"
    assert planner_result.meal_boundary == "start_new_meal"


def test_normalize_decision_result_parses_prose_tool_lookup() -> None:
    fallback = DecisionPassResult()
    normalized = normalize_decision_result(
        {
            "_raw_text": "**Next execution action:** resolve_ingredient_anchors\n\n**Clarification blocking:** no\n\n**Proceed to provisional estimate:** no"
        },
        fallback=fallback,
    )

    assert normalized.next_action == "run_tool_lookup"
    assert normalized.tool_plan == "resolve_ingredient_anchors"
    assert normalized.clarify_is_blocking is False


def test_nutrition_result_from_primary_keeps_provisional_mode_when_resolution_mode_present() -> None:
    parsed = normalize_structured_answer(
        {
            "resolution_mode": "provisional_estimate",
            "resolution_basis": "recognizable_dish_structure",
            "calories_kcal": 850,
            "protein_g": 45,
            "carbs_g": 85,
            "fat_g": 35,
            "confidence": "medium_low",
        },
        user_text="fried noodles",
    )
    result = nutrition_result_from_primary(parsed)

    assert result.resolution_mode == "provisional_estimate"
    assert result.answer_payload["estimated_kcal"] == 850


def test_normalize_structured_answer_accepts_nutrition_model_total_calories() -> None:
    normalized = normalize_structured_answer(
        {
            "resolution_mode": "provisional_estimate",
            "resolution_basis": "named_dish_structure",
            "nutrition_model": {
                "total_calories": 850,
                "macros": {"carbs_g": 120, "protein_g": 35, "fat_g": 25},
                "components": [
                    {"name": "rice", "calories": 250, "macros": {"carbs_g": 50, "protein_g": 6, "fat_g": 3}},
                    {"name": "egg", "calories": 50, "macros": {"carbs_g": 7, "protein_g": 1, "fat_g": 1}},
                ],
            },
            "confidence": "medium_low",
        },
        user_text="rice bowl with egg",
    )

    assert normalized["estimated_kcal"] == 850
    assert normalized["protein_g"] == 35
    assert normalized["carb_g"] == 120
    assert normalized["fat_g"] == 25


def test_normalize_structured_answer_accepts_calories_macros_and_component_objects() -> None:
    normalized = normalize_structured_answer(
        {
            "resolution_mode": "provisional_estimate",
            "resolution_basis": "named_dish_structure",
            "calories": {"total": 950, "low": 820, "high": 1080, "confidence": "medium"},
            "macros": {"protein_g": 45, "carbs_g": 110, "fat_g": 35},
            "components": [
                {"name": "rice", "calories": {"est": 350, "low": 300, "high": 420}, "macros": {"protein_g": 15, "carbs_g": 50, "fat_g": 10}},
                {"name": "egg", "calories": {"est": 50, "low": 30, "high": 80}, "macros": {"protein_g": 3, "carbs_g": 8, "fat_g": 1}},
            ],
        },
        user_text="rice bowl with egg",
    )

    assert normalized["estimated_kcal"] == 950
    assert normalized["kcal_low"] == 820
    assert normalized["kcal_high"] == 1080
    assert normalized["protein_g"] == 45
    assert normalized["carb_g"] == 110
    assert normalized["fat_g"] == 35
    assert normalized["answer_payload"]["items"][0]["title"] == "rice"
    assert normalized["answer_payload"]["items"][0]["estimated_kcal"] == 350


def test_partial_grounding_packet_marks_missing_major_component_and_recommends_search() -> None:
    packet = build_partial_grounding_packet(
        user_input="breakfast shop sandwich 1x soy milk 1x hash brown 1x black tea",
        planner_foods=["breakfast shop sandwich 1x", "soy milk 1x", "hash brown 1x", "black tea"],
        selected_evidence=[
            {"title": "Soy Milk", "aliases": ["soy milk"], "evidence_role": "ingredient_anchor", "identity_confidence": "medium", "source_class": "base_nutrition_db"},
            {"title": "Black Tea", "aliases": ["black tea"], "evidence_role": "ingredient_anchor", "identity_confidence": "high", "source_class": "base_nutrition_db"},
        ],
    )

    assert packet["grounding_quality"] == "partial"
    assert "Soy Milk" in [item["evidence_title"] for item in packet["anchored_components"]]
    assert any(item["name"] == "hash brown" for item in packet["missing_components"])
    assert packet["search_recommended"] is True


def test_infer_expected_components_splits_quantity_list_input() -> None:
    components = infer_expected_components(
        user_input="sandwich 1x soy milk 1x hash brown 1x black tea",
        planner_foods=[],
    )

    assert components == ["sandwich", "soy milk", "hash brown", "black tea"]


def test_infer_expected_components_splits_chinese_add_on_phrase() -> None:
    components = infer_expected_components(
        user_input="鐵板麵加豬排加蛋",
        planner_foods=[],
    )

    assert components == ["鐵板麵", "豬排", "蛋"]
