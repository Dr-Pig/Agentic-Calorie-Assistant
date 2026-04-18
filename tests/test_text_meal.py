from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient

from app.agent.exact_item_packets import resolve_exact_item
from app.agent.local_knowledge_selector import resolve_ingredient_anchors
from app.application.planner import fallback_planner_result
from app.application.evidence_assembly import search_result_quality as _search_result_quality
from app.database import SessionLocal, append_message, get_or_create_user, save_meal_log, get_latest_message_for_role
from app.main import app
from app.models import MealLog
from app.infrastructure.meal_log_persistence import persist_text_meal_result
from app.providers.builderspace_adapter import BuilderSpaceAdapter
from app.routes import planner_provider, primary_provider, provider
from app.schemas import ComponentEstimate, EstimatePayload, EstimateRequest, TaskMealLinkResult
from app.infrastructure.conversation_state_loader import load_conversation_state
from app.infrastructure.session_record_store import load_transcript_records
from app.usecases.text_meal import _run_text_stage, run_text_meal_canary
from app.usecases import text_meal_orchestration_support as text_meal_orchestration_support
from app.usecases.text_meal_runtime_support import canonical_safety_floor_kcal, run_decision_stage
from app.application.answer_support import (
    evaluate_answer as _evaluate_answer,
)


client = TestClient(app)


def test_ping_exposes_current_schema_signature() -> None:
    response = client.get("/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["schema_signature"] == "optional_planner_llm+risk_validator+layer_trace_contract+structured_main_path+local_retrieval_then_search_fallback+zero_kcal_guard+retry+uncertainty_drivers|request_id_trace"
    assert data["planner_provider"]["stage_models"]["planner_pass_initial"] == planner_provider.readiness()["stage_models"]["planner_pass_initial"]
    assert data["primary_provider"]["stage_models"]["primary_answer_pass_initial"] == primary_provider.readiness()["stage_models"]["primary_answer_pass_initial"]
    assert data["primary_provider"]["stage_models"]["primary_answer_pass_tool_round_2"] == primary_provider.readiness()["stage_models"]["primary_answer_pass_tool_round_2"]
    assert data["primary_provider"]["stage_models"]["final_response_pass"] == primary_provider.readiness()["stage_models"]["final_response_pass"]
    assert data["provider"]["stage_models"]["primary_answer_pass_initial"] == provider.readiness()["stage_models"]["primary_answer_pass_initial"]


def test_builder_space_stage_routing_uses_structured_schema() -> None:
    adapter = BuilderSpaceAdapter()
    planner_schema = adapter._response_schema_for_stage("planner_pass_initial")
    schema = adapter._response_schema_for_stage("primary_answer_pass_initial")
    nutrition_schema = adapter._response_schema_for_stage("nutrition_resolution_pass_initial")
    final_schema = adapter._response_schema_for_stage("final_response_pass")
    assert adapter._model_for_stage("planner_pass_initial") == adapter.planner_model
    assert adapter._model_for_stage("primary_answer_pass_initial") == adapter.primary_model
    assert adapter._model_for_stage("primary_answer_pass_tool_round_2") == adapter.primary_model
    assert adapter._model_for_stage("final_response_pass") == adapter.final_response_model
    assert planner_schema is not None
    assert "intent" in planner_schema["properties"]
    assert "meal_boundary" in planner_schema["properties"]
    assert "normalized_user_input" in planner_schema["properties"]
    assert "planning_brief" in planner_schema["properties"]
    assert schema is not None
    assert nutrition_schema is not None
    assert final_schema is not None
    assert "action_taken" in schema["properties"]
    assert "unresolved_info" in schema["properties"]
    assert "food_origin" in schema["properties"]
    assert "dish_structure" in schema["properties"]
    assert "current_evidence_sufficiency" in nutrition_schema["properties"]
    assert "why_no_more_tools" in nutrition_schema["properties"]
    assert "reply_text" in final_schema["properties"]


def test_missing_macro_is_soft_signal_only() -> None:
    packet = {"risk_flags": [], "required_checks": {}}
    parsed = {
        "decision": "DIRECT_ANSWER",
        "estimated_kcal": 75,
        "kcal_low": 65,
        "kcal_high": 85,
        "components": ["water"],
        "protein_g": 0,
        "carb_g": 0,
        "fat_g": 0,
        "followup_question": "",
        "followup_questions": [],
        "uncertainty_factors": [],
        "top_uncertainty_drivers": [],
        "parse_mode": "structured",
    }
    quality = _evaluate_answer(parsed, packet)
    assert quality["missing_macro"] is True


def test_run_text_meal_canary_applies_deterministic_estimate_from_local_knowledge(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")

    class FakeProvider:
        async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
            if stage == "task_meal_link_pass":
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
            user_input = user_payload.get("user_input") or user_payload.get("current_user_input")
            if stage == "decision_pass":
                return {
                    "next_action": "run_nutrition_resolution",
                    "tool_plan": "none",
                    "decision_confidence": "medium",
                    "clarify_priority": None,
                    "unresolved_info": [],
                    "response_mode_hint": "rough_estimate_ok",
                    "clarify_is_blocking": False,
                    "can_proceed_without_clarify": True,
                }, {"stage": stage}
            if stage == "nutrition_resolution_pass_initial":
                return {
                    "action_taken": "request_tool",
                    "exactness": "unknown",
                    "tool_request": "resolve_ingredient_anchors",
                    "tool_request_reason": "Need ingredient anchors before answering.",
                    "state_transition_hint": "draft_unresolved",
                    "food_origin": "generic_common",
                    "food_class": "simple_meal",
                    "needs_external_data": True,
                    "private_info_risk": "low",
                    "title": user_input,
                    "components": [],
                    "protein_g": 0,
                    "carb_g": 0,
                    "fat_g": 0,
                    "kcal_low": 0,
                    "kcal_high": 0,
                    "kcal_most_likely": 0,
                    "uncertainty_factors": [],
                    "follow_up_needed": False,
                    "follow_up_question": "",
                    "follow_up_reasoning": "",
                    "followup_questions": [],
                    "top_uncertainty_drivers": [],
                    "external_data_query": "擐? 鞊撚",
                    "answer_payload": {},
                }, {"stage": stage}
            if stage == "nutrition_resolution_pass_tool_round_2":
                    return {
                        "action_taken": "direct_answer",
                        "resolution_mode": "provisional_estimate",
                        "resolution_basis": "component_model",
                        "estimate_mode": "llm_only",
                        "confidence": "low",
                        "exactness": "component_grounded",
                        "tool_request": "none",
                        "tool_request_reason": "",
                        "state_transition_hint": "completed_meal",
                        "food_origin": "generic_common",
                        "food_class": "simple_meal",
                        "needs_external_data": False,
                        "private_info_risk": "low",
                    "title": "擐?鞊撚",
                    "components": ["擐?", "鞊撚"],
                        "protein_g": 8,
                        "carb_g": 30,
                        "fat_g": 4,
                        "kcal_low": 180,
                        "kcal_high": 260,
                        "kcal_most_likely": 220,
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
                    "reply_text": "擐?鞊撚我會先抓約 220 kcal。",
                    "ui_hints": {},
                }, {"stage": stage}
            raise AssertionError(f"unexpected stage: {stage}")

    payload = asyncio.run(
        run_text_meal_canary(
            EstimateRequest(text="soy milk banana smoothie", allow_search=False),
            provider=FakeProvider(),
            request_id="deterministic-local-knowledge",
            search_adapter=None,
        )
    )

    assert payload.best_answer_source == "primary"
    assert payload.best_estimate_mode == "llm_only"
    assert payload.estimate_confidence_tier == "low"
    assert payload.retry_triggered is False
    assert payload.retrieval_triggered is True
    assert any(step["step"] in {"planner_pass", "task_meal_link_pass"} for step in payload.debug_steps)
    assert isinstance(payload.retrieved_knowledge, list)
    assert isinstance(payload.retrieved_evidence_summary, list)
    assert "220" in payload.reply_text
    assert payload.trace_contract["db_hit_type"] in {"exact_truth", "reference_anchor", "anchor_truth", "retrieved_knowledge", "none"}
    assert payload.trace_contract["planner_used"] is True
    assert payload.north_star_evaluation["win_loss_neutral"] in {"win", "neutral", "loss"}
    assert "stage_quality_signals" in payload.trace_contract
    assert "grounding_summary" in payload.trace_contract
    assert isinstance(payload.component_estimates, list)


def test_estimate_payload_supports_trace_contract_and_north_star_evaluation() -> None:
    payload = EstimatePayload(
        request_id="trace-payload",
        meal_title="test meal",
        trace_contract={"db_hit_type": "exact_truth"},
        judge_trace={"judge_decision": "keep_best"},
        north_star_evaluation={"win_loss_neutral": "win"},
        failed_layer=None,
        primary_failure_reason=None,
    )

    assert payload.trace_contract["db_hit_type"] == "exact_truth"
    assert payload.judge_trace["judge_decision"] == "keep_best"
    assert payload.north_star_evaluation["win_loss_neutral"] == "win"


def test_estimate_payload_supports_reasoning_state_trace() -> None:
    payload = EstimatePayload(
        request_id="reasoning-trace",
        meal_title="test meal",
        reasoning_state={"search_attempt_count": 1, "why_current_evidence_is_insufficient": "exact lane empty"},
    )

    assert payload.reasoning_state["search_attempt_count"] == 1


def test_decision_stage_escalates_brand_case_without_exact_lane(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")

    class FakeProvider:
        async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
            if stage == "decision_pass":
                return {
                    "next_action": "run_nutrition_resolution",
                    "tool_plan": "none",
                    "decision_confidence": "medium",
                    "clarify_priority": None,
                    "unresolved_info": [],
                    "response_mode_hint": "rough_estimate_ok",
                    "clarify_is_blocking": False,
                    "can_proceed_without_clarify": True,
                }, {"stage": stage}
            raise AssertionError(f"unexpected stage: {stage}")

    class FakeSearchAdapter:
        def __init__(self) -> None:
            self.queries: list[str] = []

        async def search(self, query: str, limit: int = 5):
            self.queries.append(query)
            return [
                {
                    "title": "吉野家牛丼營養資訊",
                    "url": "https://www.yoshinoya.com.tw/nutrition/beef-bowl",
                    "snippet": "吉野家 牛丼 熱量與營養資訊 official nutrition",
                }
            ]

    planner_result = fallback_planner_result(
        "吉野家牛丼",
        normalize_text=lambda text: text,
        normalize_user_input_for_estimation=lambda text: {
            "normalized_text": text,
            "normalizer_applied": False,
            "notes": [],
        },
    ).model_copy(
        update={
            "resolved_query": "吉野家牛丼",
            "input_signals": {
                "modalities": ["text"],
                "foods": ["牛丼"],
                "brands": ["吉野家"],
                "portion_clues": [],
            },
        }
    )
    task_meal_link_result = TaskMealLinkResult(
        intent="food_estimation",
        scope="meal_specific",
        meal_link_action="create_new_meal",
        target_meal_id=None,
        link_confidence="high",
        boundary_reason="new_meal",
        clarification_blocking=False,
        normalized_user_input="吉野家牛丼",
    )
    filtered_knowledge = [
        {
            "title": "吉野家牛丼類別先驗",
            "brand": "吉野家",
            "brand_hint": "Yoshinoya",
            "source_class": "base_nutrition_db",
            "evidence_role": "dish_prior",
            "retrieval_lane": "anchor_lane",
            "identity_confidence": "medium",
            "kcal": 650,
        }
    ]
    partial_grounding = {
        "exact_truth_present": False,
        "anchor_lane_candidates": [{"title": "吉野家牛丼類別先驗"}],
        "template_lane_hits": [],
        "search_attempt_count": 0,
    }
    llm_traces: list[dict[str, object]] = []
    debug_steps: list[dict[str, object]] = []
    search_adapter = FakeSearchAdapter()

    outcome = asyncio.run(
        run_decision_stage(
            primary_llm=FakeProvider(),
            request_id="decision-escalation",
            effective_user_input="吉野家牛丼",
            canonical_meal_state=None,
            task_meal_link_result=task_meal_link_result,
            planner_result=planner_result,
            filtered_knowledge=filtered_knowledge,
            available_tools=["search_official_nutrition"],
            local_exact_truth_present=False,
            request=EstimateRequest(text="吉野家牛丼", allow_search=True),
            search_adapter=search_adapter,
            executed_tool_calls=[],
            normalized_evidence=[],
            partial_grounding=partial_grounding,
            run_stage=_run_text_stage,
            llm_traces=llm_traces,
            debug_steps=debug_steps,
            planner_max_tokens=512,
        )
    )

    assert outcome.decision_result.next_action == "run_tool_lookup"
    assert outcome.decision_result.tool_plan == "search_official_nutrition"
    assert outcome.decision_result.tool_goal == "find_exact_verified_brand_item"
    assert outcome.decision_result.missing_evidence_type == "official_exact"
    assert outcome.used_search is True
    assert search_adapter.queries
    assert outcome.search_query is not None
    assert outcome.partial_grounding["search_attempt_count"] == 1
    assert any(step["step"] == "decision_tool_lookup" for step in debug_steps)


def test_decision_stage_skips_search_when_exact_truth_is_present(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")

    class FakeProvider:
        async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
            if stage == "decision_pass":
                return {
                    "next_action": "run_tool_lookup",
                    "tool_plan": "search_official_nutrition",
                    "decision_confidence": "high",
                    "clarify_priority": None,
                    "unresolved_info": [],
                    "response_mode_hint": "exact_answer",
                    "clarify_is_blocking": False,
                    "can_proceed_without_clarify": True,
                }, {"stage": stage}
            raise AssertionError(f"unexpected stage: {stage}")

    class FakeSearchAdapter:
        def __init__(self) -> None:
            self.queries: list[str] = []

        async def search(self, query: str, limit: int = 5):
            self.queries.append(query)
            return []

    planner_result = fallback_planner_result(
        "吉野家牛丼",
        normalize_text=lambda text: text,
        normalize_user_input_for_estimation=lambda text: {
            "normalized_text": text,
            "normalizer_applied": False,
            "notes": [],
        },
    ).model_copy(
        update={
            "resolved_query": "吉野家牛丼",
            "input_signals": {
                "modalities": ["text"],
                "foods": ["牛丼"],
                "brands": ["吉野家"],
                "portion_clues": [],
            },
        }
    )
    task_meal_link_result = TaskMealLinkResult(
        intent="food_estimation",
        scope="meal_specific",
        meal_link_action="create_new_meal",
        target_meal_id=None,
        link_confidence="high",
        boundary_reason="new_meal",
        clarification_blocking=False,
        normalized_user_input="吉野家牛丼",
    )
    filtered_knowledge = [
        {
            "title": "吉野家牛丼",
            "brand": "吉野家",
            "source_class": "exact_item_db",
            "evidence_role": "exact_truth",
            "retrieval_lane": "exact_lane",
            "identity_confidence": "high",
            "kcal": 650,
        }
    ]
    partial_grounding = {
        "exact_truth_present": True,
        "exact_lane_candidates": [{"title": "吉野家牛丼"}],
        "anchor_lane_candidates": [],
        "template_lane_hits": [],
        "search_attempt_count": 0,
    }
    llm_traces: list[dict[str, object]] = []
    debug_steps: list[dict[str, object]] = []
    search_adapter = FakeSearchAdapter()

    outcome = asyncio.run(
        run_decision_stage(
            primary_llm=FakeProvider(),
            request_id="decision-exact-skip-search",
            effective_user_input="吉野家牛丼",
            canonical_meal_state=None,
            task_meal_link_result=task_meal_link_result,
            planner_result=planner_result,
            filtered_knowledge=filtered_knowledge,
            available_tools=["search_official_nutrition"],
            local_exact_truth_present=True,
            request=EstimateRequest(text="吉野家牛丼", allow_search=True),
            search_adapter=search_adapter,
            executed_tool_calls=[],
            normalized_evidence=[],
            partial_grounding=partial_grounding,
            run_stage=_run_text_stage,
            llm_traces=llm_traces,
            debug_steps=debug_steps,
            planner_max_tokens=512,
        )
    )

    assert outcome.decision_result.tool_plan == "search_official_nutrition"
    assert outcome.used_search is False
    assert not search_adapter.queries
    assert outcome.partial_grounding["search_attempt_count"] == 0
    assert not any(step["step"] == "decision_tool_lookup" for step in debug_steps)


def test_run_text_meal_canary_uses_disabled_planner_mode_by_default(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "0")

    class FakeProvider:
        async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
            if stage == "decision_pass":
                return {
                    "next_action": "run_nutrition_resolution",
                    "tool_plan": "none",
                    "decision_confidence": "medium",
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
                    "estimate_mode": "heuristic_fallback",
                    "confidence": "medium",
                    "response_mode_hint": "rough_estimate_ok",
                    "tool_request": "none",
                    "tool_request_reason": "",
                    "state_transition_hint": "completed_meal",
                    "food_origin": "generic_common",
                    "food_class": "simple_meal",
                    "needs_external_data": False,
                    "private_info_risk": "low",
                    "title": user_payload["user_input"],
                    "components": ["soy milk"],
                    "protein_g": 12,
                    "carb_g": 44,
                    "fat_g": 12,
                    "kcal_low": 320,
                    "kcal_high": 420,
                    "kcal_most_likely": 380,
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
                return {"reply_text": "soy milk 400ml from app note我會先抓約 380 kcal。", "ui_hints": {}}, {"stage": stage}
            raise AssertionError(f"unexpected stage {stage}")

    payload = asyncio.run(
        run_text_meal_canary(
            EstimateRequest(text="soy milk 400ml from app note", allow_search=False),
            provider=FakeProvider(),
            request_id="planner-disabled",
            search_adapter=None,
        )
    )

    assert any(
        step["step"] == "planner_pass" and step.get("planner_mode") == "disabled" and step.get("planner_reason") == "feature_flag_off"
        for step in payload.debug_steps
    )
    planner_step = next(
        step for step in payload.debug_steps if step["step"] == "planner_pass" and "normalized_user_input" in step
    )
    assert planner_step["normalized_user_input"] == "soy milk 400ml from app note"
    assert payload.estimated_kcal > 0


def test_run_text_meal_canary_falls_back_when_planner_stage_is_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")

    class FakeProvider:
        async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
            if stage == "task_meal_link_pass":
                raise RuntimeError("planner unavailable")
            if stage == "decision_pass":
                return {
                    "next_action": "run_nutrition_resolution",
                    "tool_plan": "none",
                    "decision_confidence": "medium",
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
                    "estimate_mode": "heuristic_fallback",
                    "confidence": "medium",
                    "response_mode_hint": "rough_estimate_ok",
                    "tool_request": "none",
                    "tool_request_reason": "",
                    "state_transition_hint": "completed_meal",
                    "food_origin": "generic_common",
                    "food_class": "simple_meal",
                    "needs_external_data": False,
                    "private_info_risk": "low",
                    "title": user_payload["user_input"],
                    "components": ["soy milk"],
                    "protein_g": 12,
                    "carb_g": 44,
                    "fat_g": 12,
                    "kcal_low": 320,
                    "kcal_high": 360,
                    "kcal_most_likely": 340,
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
                return {"reply_text": "soy milk 400ml from app note我會先抓約 340 kcal。", "ui_hints": {}}, {"stage": stage}
            raise AssertionError(f"unexpected stage: {stage}")

    payload = asyncio.run(
        run_text_meal_canary(
            EstimateRequest(text="soy milk 400ml from app note", allow_search=False),
            provider=FakeProvider(),
            request_id="planner-fallback",
            search_adapter=None,
        )
    )

    planner_step = next(
        step
        for step in payload.debug_steps
        if step["step"] == "planner_pass"
        and step["planner_mode"] == "fallback"
        and "normalized_user_input" in step
    )
    assert planner_step["normalized_user_input"] == "soy milk 400ml from app note"
    assert payload.estimated_kcal > 0


def test_search_result_quality_prefers_relevant_chain_results() -> None:
    quality, results = _search_result_quality(
        "暻亦??憭折漸???梢?",
        [
            {"title": "暻亦?之暻亙???鞈?", "url": "https://www.mcdonalds.com.tw/bigmac", "snippet": "憭折漸??550 kcal"},
            {"title": "forum post", "url": "https://www.ptt.cc/example", "snippet": "user estimate"},
        ],
    )
    assert quality == "high"
    assert len(results) == 2


def test_search_result_quality_rejects_sibling_variant_substitution() -> None:
    quality, results = _search_result_quality(
        "pocari sweat 580ml",
        [
            {"title": "ION WATER 580ml", "url": "https://www.pocari.tw/ion-water", "snippet": "雿??憌脫?"},
            {"title": "pocari sweat 580ml", "url": "https://www.pocari.com.tw/product/580ml", "snippet": "official product page"},
        ],
    )
    assert quality == "high"
    assert len(results) == 2


def test_conversation_archive_persists_beyond_recent_window() -> None:
    db = SessionLocal()
    try:
        user_id = f"archive-test-{uuid4().hex}"
        user = get_or_create_user(db, user_id)
        for index in range(12):
            role = "user" if index % 2 == 0 else "assistant"
            content = f"banana smoothie context {index}"
            append_message(db, user, role, content)

        loaded = load_conversation_state(db, user_id=user_id, incoming_user_text="banana smoothie large cup")
        assert loaded.state.conversation_archive_count >= 13
        assert len(loaded.state.recent_messages) == 5
        assert len(loaded.state.conversation_archive_hits) > 0
        assert loaded.state.planner_state_digest.archive_hit_count == len(loaded.state.conversation_archive_hits)
        assert any("banana smoothie" in hit.content for hit in loaded.state.conversation_archive_hits)
        assert loaded.state.retrieved_transcript_chunks
        assert loaded.state.retrieved_meal_records == []
    finally:
        db.close()


def test_conversation_state_exposes_file_backed_retrieval_layers() -> None:
    db = SessionLocal()
    try:
        user_id = f"file-backed-{uuid4().hex}"
        user = get_or_create_user(db, user_id)
        append_message(db, user, "user", "我早餐吃青梅豬排堡加紅茶")
        append_message(db, user, "assistant", "杯量是大杯還是中杯？")
        save_meal_log(
            db,
            user,
            meal_title="青梅豬排堡加紅茶",
            raw_input="我早餐吃青梅豬排堡加紅茶",
            kcal=520,
            protein_g=21,
            carb_g=55,
            fat_g=18,
            components=[{"name": "青梅豬排堡", "portion_hint": "1份"}, {"name": "紅茶", "portion_hint": "1杯"}],
            debug_steps=[],
            status="draft",
            pending_question="紅茶是大杯還是中杯？",
        )
        loaded = load_conversation_state(db, user_id=user_id, incoming_user_text="我半夜吃了一個滷味")
    finally:
        db.close()

    assert loaded.state.retrieved_transcript_chunks
    assert loaded.state.retrieved_meal_records
    assert loaded.state.active_meal_time_gap_seconds is not None


def test_session_record_sync_preserves_transcript_meal_linkage() -> None:
    db = SessionLocal()
    try:
        user_id = f"linked-transcript-{uuid4().hex}"
        user = get_or_create_user(db, user_id)
        meal = save_meal_log(
            db,
            user,
            meal_title="青梅豬排堡加紅茶",
            raw_input="我早餐吃青梅豬排堡加紅茶",
            kcal=520,
            protein_g=21,
            carb_g=55,
            fat_g=18,
            components=[{"name": "青梅豬排堡", "portion_hint": "1份"}],
            debug_steps=[],
            status="draft",
            pending_question="紅茶是大杯還是中杯？",
        )
        append_message(db, user, "assistant", "紅茶是大杯還是中杯？", linked_meal_log_id=meal.id)
        append_message(db, user, "user", "中杯無糖", linked_meal_log_id=meal.id)
        load_conversation_state(db, user_id=user_id, incoming_user_text=None)
        transcript_records = load_transcript_records(user_id)
    finally:
        db.close()

    assert any(record.linked_meal_id == meal.id for record in transcript_records)


def test_boundary_clarification_short_circuit_skips_log_creation(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")
    db = SessionLocal()
    try:
        user_id = f"boundary-clarify-{uuid4().hex}"
        user = get_or_create_user(db, user_id)
        initial_count = len(user.logs)

        class PlannerProvider:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                return {
                    "intent": "new_intake",
                    "scope": "meal_specific",
                    "meal_link_action": "boundary_ambiguous",
                    "target_meal_id": None,
                    "link_confidence": "low",
                    "boundary_reason": "boundary_unresolved",
                    "clarification_blocking": True,
                    "normalized_user_input": user_payload["current_user_input"],
                }, {"stage": stage}

        payload = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="裡面還有高麗菜", allow_search=False, user_id=user_id),
                provider=PlannerProvider(),
                planner_provider=PlannerProvider(),
                primary_provider=PlannerProvider(),
                request_id="boundary-clarify-short-circuit",
                search_adapter=None,
                db=db,
            )
        )
        final_count = len(user.logs)
        user_messages = get_latest_message_for_role(db, user, "user")
        assistant_messages = get_latest_message_for_role(db, user, "assistant")
    finally:
        db.close()

    assert payload.boundary_trace["boundary_resolution_state"] == "open"
    assert payload.trace_contract["persistence_decision"]["action"] == "skip_log_boundary_clarification"
    assert final_count == initial_count
    assert user_messages is not None and user_messages.linked_meal_log_id is None
    assert assistant_messages is not None and assistant_messages.linked_meal_log_id is None


def test_clarify_required_lane_blocks_canonical_commit(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")
    db = SessionLocal()
    try:
        user_id = f"clarify-blocking-{uuid4().hex}"
        get_or_create_user(db, user_id)

        class PlannerProvider:
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

        class PrimaryProvider:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                if stage == "decision_pass":
                    return {
                        "next_action": "run_clarify",
                        "tool_plan": "none",
                        "decision_confidence": "medium",
                        "clarify_priority": "portion_size",
                        "unresolved_info": ["portion_size"],
                        "response_mode_hint": "clarify_first",
                        "clarify_is_blocking": True,
                        "can_proceed_without_clarify": True,
                    }, {"stage": stage}
                if stage == "final_response_pass":
                    return {
                        "reply_text": "請問這份餐點的份量是多大？",
                        "ui_hints": {},
                    }, {"stage": stage}
                raise AssertionError(f"unexpected stage: {stage}")

        payload = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="我吃了一份便當", allow_search=False, user_id=user_id),
                provider=PrimaryProvider(),
                planner_provider=PlannerProvider(),
                primary_provider=PrimaryProvider(),
                request_id="clarify-blocking-test",
                search_adapter=None,
                db=db,
            )
        )
    finally:
        db.close()

    persistence_decision = payload.trace_contract["persistence_decision"]
    assert payload.route_target == "clarify_user_private"
    assert payload.follow_up_needed is True
    assert persistence_decision["action"] == "save_draft_log"
    assert persistence_decision["status"] == "draft_unresolved"
    assert persistence_decision["canonical_commit"] is None


def test_cannot_estimate_lane_refuses_canonical_commit_and_marks_abstain(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")
    db = SessionLocal()
    try:
        user_id = f"cannot-estimate-{uuid4().hex}"
        user = get_or_create_user(db, user_id)

        class PlannerProvider:
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

        class PrimaryProvider:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                if stage == "decision_pass":
                    return {
                        "next_action": "run_nutrition_resolution",
                        "tool_plan": "none",
                        "decision_confidence": "medium",
                        "clarify_priority": None,
                        "unresolved_info": [],
                        "response_mode_hint": "rough_estimate_ok",
                        "clarify_is_blocking": False,
                        "can_proceed_without_clarify": True,
                    }, {"stage": stage}
                if stage == "nutrition_resolution_pass_initial":
                    return {
                        "action_taken": "clarify_before_estimate",
                        "resolution_mode": "cannot_estimate_yet",
                        "resolution_basis": "component_model",
                        "exactness": "unknown",
                        "estimate_mode": "llm_only",
                        "confidence": "low",
                        "response_mode_hint": "clarify_first",
                        "tool_request": "none",
                        "tool_request_reason": "",
                        "state_transition_hint": "draft_unresolved",
                        "food_origin": "generic_common",
                        "food_class": "simple_meal",
                        "needs_external_data": False,
                        "private_info_risk": "low",
                        "title": "unknown meal",
                        "components": [],
                        "protein_g": 0,
                        "carb_g": 0,
                        "fat_g": 0,
                        "kcal_low": 0,
                        "kcal_high": 0,
                        "kcal_most_likely": 0,
                        "uncertainty_factors": [],
                        "follow_up_needed": True,
                        "follow_up_question": "I can't estimate this safely yet. What exactly did you have?",
                        "follow_up_reasoning": "no_safe_estimate",
                        "followup_questions": [],
                        "top_uncertainty_drivers": [],
                        "external_data_query": "",
                        "unresolved_info": ["cannot_estimate_yet"],
                        "answer_payload": {},
                    }, {"stage": stage}
                if stage == "final_response_pass":
                    return {
                        "reply_text": "I can't estimate this safely yet. What exactly did you have?",
                        "ui_hints": {},
                    }, {"stage": stage}
                raise AssertionError(f"unexpected stage: {stage}")

        payload = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="mystery meal", allow_search=False, user_id=user_id),
                provider=PrimaryProvider(),
                planner_provider=PlannerProvider(),
                primary_provider=PrimaryProvider(),
                request_id="cannot-estimate-test",
                search_adapter=None,
                db=db,
            )
        )
        latest_user_message = get_latest_message_for_role(db, user, "user")
        latest_assistant_message = get_latest_message_for_role(db, user, "assistant")
    finally:
        db.close()

    persistence_decision = payload.trace_contract["persistence_decision"]
    canonical_write_decision = payload.trace_contract["canonical_write_decision"]
    assert payload.route_target == "clarify_user_private"
    assert payload.follow_up_needed is True
    assert "can't estimate" in payload.reply_text.lower()
    assert canonical_write_decision["mode"] == "abstain"
    assert canonical_write_decision["can_write_canonical"] is False
    assert persistence_decision["canonical_commit"] is None
    assert persistence_decision["status"] == "draft_unresolved"
    assert latest_user_message is not None and latest_user_message.linked_meal_log_id is not None
    assert latest_assistant_message is not None and latest_assistant_message.linked_meal_log_id is not None


def test_run_text_meal_canary_splits_planner_and_primary_providers(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")

    class PlannerProvider:
        def __init__(self) -> None:
            self.stages: list[str] = []

        async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
            self.stages.append(stage)
            assert stage == "task_meal_link_pass"
            return {
                "intent": "new_intake",
                "scope": "meal_specific",
                "meal_link_action": "create_new_meal",
                "target_meal_id": None,
                "link_confidence": "high",
                "boundary_reason": "new_meal",
                "clarification_blocking": False,
                "normalized_user_input": user_payload["current_user_input"],
            }, {"stage": stage}

    class PrimaryProvider:
        def __init__(self) -> None:
            self.stages: list[str] = []

        async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
            self.stages.append(stage)
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
                assert user_payload["current_user_input"] == "banana milk"
                return {
                    "action_taken": "direct_answer",
                    "resolution_mode": "provisional_estimate",
                    "resolution_basis": "component_model",
                    "exactness": "best_effort",
                    "estimate_mode": "heuristic_fallback",
                    "confidence": "medium",
                    "response_mode_hint": "rough_estimate_ok",
                    "tool_request": "none",
                    "tool_request_reason": "",
                    "state_transition_hint": "completed_meal",
                    "food_origin": "generic_common",
                    "food_class": "simple_meal",
                    "needs_external_data": False,
                    "private_info_risk": "low",
                    "title": "banana milk",
                    "components": ["banana milk"],
                    "protein_g": 8,
                    "carb_g": 25,
                    "fat_g": 3,
                    "kcal_low": 150,
                    "kcal_high": 210,
                    "kcal_most_likely": 180,
                    "uncertainty_factors": [],
                    "follow_up_needed": False,
                    "follow_up_question": "",
                    "follow_up_reasoning": "",
                    "followup_questions": [],
                    "top_uncertainty_drivers": [],
                    "external_data_query": "",
                    "answer_payload": {},
                }, {"stage": stage}
            assert stage == "final_response_pass"
            return {
                "reply_text": "banana milk我會先抓約 180 kcal。",
                "ui_hints": {},
            }, {"stage": stage}

    planner = PlannerProvider()
    primary = PrimaryProvider()

    payload = asyncio.run(
        run_text_meal_canary(
            EstimateRequest(text="banana milk", allow_search=False, user_id=f"provider-split-{uuid4().hex}"),
            provider=primary,
            planner_provider=planner,
            primary_provider=primary,
            request_id="provider-split",
            search_adapter=None,
        )
    )

    assert planner.stages == ["task_meal_link_pass"]
    assert primary.stages[0] == "decision_pass"
    assert primary.stages[1] == "nutrition_resolution_pass_initial"
    assert primary.stages[-1] == "final_response_pass"
    assert all(stage in {"nutrition_resolution_pass_repair", "final_response_pass"} for stage in primary.stages[2:])
    assert payload.action_taken == "direct_answer"
    assert payload.trace_contract["planner_output"]["resolved_query"] == "banana milk"
    assert payload.trace_contract["planner_output"]["planning_brief"]["resolved_query"] == "banana milk"


def test_decision_pass_can_trigger_search_before_nutrition(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")
    db = SessionLocal()
    try:
        user_id = f"search-followup-{uuid4().hex}"
        user = get_or_create_user(db, user_id)
        save_meal_log(
            db,
            user,
            meal_title="豆乳雞蛋餅",
            raw_input="我中午吃了豆乳雞蛋餅",
            kcal=0,
            protein_g=0,
            carb_g=0,
            fat_g=0,
            components=[{"name": "豆乳雞蛋餅", "portion_hint": "1份"}],
            debug_steps=[],
            status="draft_unresolved",
            pending_question="這是哪一家店的？",
        )

        class PlannerProvider:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                return {
                    "intent": "clarification",
                    "scope": "meal_specific",
                    "meal_link_action": "attach_to_existing_meal",
                    "target_meal_id": 1,
                    "link_confidence": "high",
                    "boundary_reason": "same_meal_followup",
                    "clarification_blocking": False,
                    "normalized_user_input": user_payload["current_user_input"],
                }, {"stage": stage}

        class PrimaryProvider:
            def __init__(self) -> None:
                self.nutrition_payloads: list[dict[str, object]] = []

            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                if stage == "decision_pass":
                    return {
                        "next_action": "run_tool_lookup",
                        "tool_plan": "search_official_nutrition",
                        "decision_confidence": "high",
                        "clarify_priority": None,
                        "unresolved_info": [],
                        "response_mode_hint": "rough_estimate_ok",
                        "clarify_is_blocking": False,
                        "can_proceed_without_clarify": True,
                    }, {"stage": stage}
                if stage == "nutrition_resolution_pass_initial":
                    self.nutrition_payloads.append(user_payload)
                    return {
                        "action_taken": "direct_answer",
                        "resolution_mode": "provisional_estimate",
                        "resolution_basis": "component_model",
                        "estimate_mode": "llm_only",
                        "confidence": "medium",
                        "exactness": "best_effort",
                        "tool_request": "none",
                        "tool_request_reason": "",
                        "state_transition_hint": "completed_meal",
                        "food_origin": "restaurant_chain",
                        "food_class": "simple_meal",
                        "needs_external_data": False,
                        "private_info_risk": "low",
                        "title": "軟實力豆乳雞蛋餅",
                        "components": ["蛋餅", "豆乳雞"],
                        "protein_g": 22,
                        "carb_g": 42,
                        "fat_g": 18,
                        "kcal_low": 420,
                        "kcal_high": 560,
                        "kcal_most_likely": 490,
                        "uncertainty_factors": [],
                        "follow_up_needed": False,
                        "follow_up_question": "",
                        "follow_up_reasoning": "",
                        "followup_questions": [],
                        "top_uncertainty_drivers": [],
                        "external_data_query": "",
                        "answer_payload": {},
                    }, {"stage": stage}
                assert stage == "final_response_pass"
                return {"reply_text": "軟實力豆乳雞蛋餅我先抓約 490 kcal。", "ui_hints": {}}, {"stage": stage}

        class FakeSearch:
            def __init__(self) -> None:
                self.queries: list[str] = []

            async def search(self, query, limit=5):
                self.queries.append(query)
                return [{"title": "軟實力菜單", "source_class": "web_search_official"}]

        primary = PrimaryProvider()
        search = FakeSearch()
        payload = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="你可以查查軟實力這家店", allow_search=True, user_id=user_id),
                provider=primary,
                planner_provider=PlannerProvider(),
                primary_provider=primary,
                request_id="decision-search-trigger",
                search_adapter=search,
                db=db,
            )
        )
    finally:
        db.close()

    assert search.queries
    assert any("軟實力" in query for query in search.queries)
    assert payload.used_search is True
    assert "490" in payload.reply_text


def test_active_meal_continuation_preserves_canonical_thread_lineage(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")
    db = SessionLocal()
    try:
        user_id = f"active-continuation-{uuid4().hex}"
        user = get_or_create_user(db, user_id)
        first = persist_text_meal_result(
            db,
            user=user,
            latest_log=None,
            planner_intent="food_estimation",
            payload=EstimatePayload(
                request_id="cont-1",
                meal_title="豆乳雞蛋餅",
                estimated_kcal=490,
                protein_g=22,
                carb_g=42,
                fat_g=18,
                route_target="best_effort_answer",
                action_taken="direct_answer",
                reply_text="豆乳雞蛋餅 ok",
                quality_signals={"estimate_mode": "exact_item"},
                trace_contract={"local_date": "2026-04-12"},
                boundary_trace={},
                component_estimates=[
                    ComponentEstimate(
                        name="豆乳雞蛋餅",
                        quantity_hint="1 serving",
                        estimated_kcal=490,
                        protein_g=22,
                        carb_g=42,
                        fat_g=18,
                    )
                ],
            ),
            raw_input="我中午吃了豆乳雞蛋餅",
            request_id="cont-1",
        )
        original_thread_id = first["canonical_commit"]["meal_thread_id"]
        original_version_id = first["canonical_commit"]["meal_version_id"]
        latest_log = db.get(MealLog, first["persisted_log_id"])
        assert latest_log is not None

        class PlannerProvider:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                if stage == "task_meal_link_pass":
                    assert user_payload["meal_log_summaries"]
                    return {
                        "intent": "clarification",
                        "scope": "meal_specific",
                        "meal_link_action": "attach_to_existing_meal",
                        "target_meal_id": first["persisted_log_id"],
                        "link_confidence": "high",
                        "boundary_reason": "same_meal_followup",
                        "clarification_blocking": False,
                        "normalized_user_input": user_payload["current_user_input"],
                    }, {"stage": stage}
                raise AssertionError(f"unexpected stage: {stage}")

        class PrimaryProvider:
            def __init__(self) -> None:
                self.nutrition_payloads: list[dict[str, object]] = []

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
                    self.nutrition_payloads.append(user_payload)
                    assert user_payload["active_meal_context_allowed"] is True
                    assert [item["name"] for item in user_payload["old_components"]] == ["豆乳雞蛋餅"]
                    return {
                        "action_taken": "direct_answer",
                        "resolution_mode": "provisional_estimate",
                        "resolution_basis": "component_model",
                        "estimate_mode": "llm_only",
                        "confidence": "medium",
                        "exactness": "best_effort",
                        "tool_request": "none",
                        "tool_request_reason": "",
                        "state_transition_hint": "completed_meal",
                        "food_origin": "restaurant_chain",
                        "food_class": "simple_meal",
                        "needs_external_data": False,
                        "private_info_risk": "low",
                        "title": "豆乳雞蛋餅加一半蛋",
                        "components": ["豆乳雞蛋餅", "半份蛋"],
                        "protein_g": 24,
                        "carb_g": 44,
                        "fat_g": 19,
                        "kcal_low": 520,
                        "kcal_high": 590,
                        "kcal_most_likely": 550,
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
                    return {"reply_text": "豆乳雞蛋餅我先抓約 550 kcal。", "ui_hints": {}}, {"stage": stage}
                raise AssertionError(f"unexpected stage: {stage}")

        primary = PrimaryProvider()
        payload = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="再加半份蛋", allow_search=False, user_id=user_id),
                provider=primary,
                planner_provider=PlannerProvider(),
                primary_provider=primary,
                request_id="active-continuation-test",
                search_adapter=None,
                db=db,
            )
        )
    finally:
        db.close()

    persistence = payload.trace_contract["persistence_decision"]
    assert payload.boundary_trace["meal_boundary"] == "continue_active_meal"
    assert payload.boundary_trace["active_meal_context_allowed"] is True
    assert persistence["canonical_commit"] is not None
    assert persistence["canonical_commit"]["meal_thread_id"] == original_thread_id
    assert persistence["canonical_commit"]["created_new_thread"] is False
    assert persistence["canonical_commit"]["superseded_version_id"] == original_version_id
    assert persistence["linked_meal_log_id"] == persistence["persisted_log_id"]


def test_cross_midnight_correction_uses_local_attribution_timestamp(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")
    db = SessionLocal()
    try:
        user_id = f"cross-midnight-{uuid4().hex}"
        get_or_create_user(db, user_id)

        class PlannerProvider:
            def __init__(self, *, meal_link_action: str, target_meal_id: int | None = None) -> None:
                self.meal_link_action = meal_link_action
                self.target_meal_id = target_meal_id

            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                if stage == "task_meal_link_pass":
                    return {
                        "intent": "food_estimation" if self.meal_link_action == "create_new_meal" else "modification",
                        "scope": "meal_specific",
                        "meal_link_action": self.meal_link_action,
                        "target_meal_id": self.target_meal_id,
                        "link_confidence": "high",
                        "boundary_reason": "new_meal" if self.meal_link_action == "create_new_meal" else "same_meal_followup",
                        "clarification_blocking": False,
                        "normalized_user_input": user_payload["current_user_input"],
                    }, {"stage": stage}
                raise AssertionError(f"unexpected stage: {stage}")

        class PrimaryProvider:
            def __init__(self, *, title: str, kcal: int, protein: int, carb: int, fat: int) -> None:
                self.title = title
                self.kcal = kcal
                self.protein = protein
                self.carb = carb
                self.fat = fat

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
                        "estimate_mode": "llm_only",
                        "confidence": "medium",
                        "exactness": "best_effort",
                        "tool_request": "none",
                        "tool_request_reason": "",
                        "state_transition_hint": "completed_meal",
                        "food_origin": "generic_common",
                        "food_class": "simple_meal",
                        "needs_external_data": False,
                        "private_info_risk": "low",
                        "title": self.title,
                        "components": [self.title],
                        "protein_g": self.protein,
                        "carb_g": self.carb,
                        "fat_g": self.fat,
                        "kcal_low": self.kcal,
                        "kcal_high": self.kcal,
                        "kcal_most_likely": self.kcal,
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
                    return {"reply_text": f"{self.title} 我先抓約 {self.kcal} kcal。", "ui_hints": {}}, {"stage": stage}
                raise AssertionError(f"unexpected stage: {stage}")

        monkeypatch.setattr(
            text_meal_orchestration_support,
            "now_iso",
            lambda: "2026-04-11T15:55:00+00:00",
        )
        first = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="我晚上吃了一碗飯", allow_search=False, user_id=user_id),
                provider=PrimaryProvider(title="late-night bowl", kcal=480, protein=18, carb=52, fat=14),
                planner_provider=PlannerProvider(meal_link_action="create_new_meal"),
                primary_provider=PrimaryProvider(title="late-night bowl", kcal=480, protein=18, carb=52, fat=14),
                request_id="midnight-1",
                search_adapter=None,
                db=db,
            )
        )
        first_log = db.get(MealLog, first.trace_contract["persistence_decision"]["persisted_log_id"])
        assert first_log is not None
        assert first.trace_contract["persistence_decision"]["canonical_commit"]["local_date"] == "2026-04-11"

        monkeypatch.setattr(
            text_meal_orchestration_support,
            "now_iso",
            lambda: "2026-04-11T16:05:00+00:00",
        )
        second = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="我剛剛那碗飯其實多了一點", allow_search=False, user_id=user_id),
                provider=PrimaryProvider(title="late-night bowl corrected", kcal=520, protein=20, carb=54, fat=15),
                planner_provider=PlannerProvider(meal_link_action="attach_to_existing_meal", target_meal_id=first_log.id),
                primary_provider=PrimaryProvider(title="late-night bowl corrected", kcal=520, protein=20, carb=54, fat=15),
                request_id="midnight-2",
                search_adapter=None,
                db=db,
            )
        )
    finally:
        db.close()

    second_commit = second.trace_contract["persistence_decision"]["canonical_commit"]
    assert second_commit is not None
    assert second_commit["meal_thread_id"] == first.trace_contract["persistence_decision"]["canonical_commit"]["meal_thread_id"]
    assert second_commit["local_date"] == "2026-04-12"
    assert second_commit["created_new_thread"] is False

def test_start_new_meal_boundary_blocks_old_component_injection(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")
    db = SessionLocal()
    try:
        user_id = f"boundary-switch-{uuid4().hex}"
        user = get_or_create_user(db, user_id)
        save_meal_log(
            db,
            user,
            meal_title="青梅豬排堡加紅茶",
            raw_input="我早餐吃青梅豬排堡加紅茶",
            kcal=520,
            protein_g=21,
            carb_g=55,
            fat_g=18,
            components=[{"name": "青梅豬排堡", "portion_hint": "1份"}, {"name": "紅茶", "portion_hint": "1杯"}],
            debug_steps=[],
            status="draft",
            pending_question="紅茶是大杯還是中杯？",
        )

        class PlannerProvider:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                assert user_payload["meal_log_summaries"]
                return {
                    "intent": "new_intake",
                    "scope": "meal_specific",
                    "meal_link_action": "create_new_meal",
                    "target_meal_id": None,
                    "link_confidence": "high",
                    "boundary_reason": "new_meal_switch",
                    "clarification_blocking": False,
                    "normalized_user_input": "我半夜吃了一個滷味",
                }, {"stage": stage}

        class PrimaryProvider:
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
                    assert user_payload["active_meal_context_allowed"] is False
                    assert user_payload["old_components"] == []
                    return {
                        "action_taken": "direct_answer",
                        "exactness": "best_effort",
                        "tool_request": "none",
                        "tool_request_reason": "",
                        "state_transition_hint": "completed_meal",
                        "food_origin": "generic_common",
                        "food_class": "simple_meal",
                        "needs_external_data": False,
                        "private_info_risk": "low",
                        "title": "滷味",
                        "components": ["滷味"],
                        "protein_g": 18,
                        "carb_g": 35,
                        "fat_g": 12,
                        "kcal_low": 260,
                        "kcal_high": 420,
                        "kcal_most_likely": 340,
                        "uncertainty_factors": [],
                        "follow_up_needed": False,
                        "follow_up_question": "",
                        "follow_up_reasoning": "",
                        "followup_questions": [],
                        "top_uncertainty_drivers": [],
                        "external_data_query": "",
                        "answer_payload": {},
                    }, {"stage": stage}
                assert stage == "final_response_pass"
                return {"reply_text": "滷味我會先抓約 340 kcal。", "ui_hints": {}}, {"stage": stage}

        payload = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="我半夜吃了一個滷味", allow_search=False, user_id=user_id),
                provider=PrimaryProvider(),
                planner_provider=PlannerProvider(),
                primary_provider=PrimaryProvider(),
                request_id="boundary-switch-test",
                search_adapter=None,
                db=db,
            )
        )
    finally:
        db.close()

    assert payload.boundary_trace["meal_boundary"] == "start_new_meal"
    assert payload.boundary_trace["active_meal_context_allowed"] is False


def test_new_meal_persistence_links_user_and_assistant_messages(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_MEAL_ENABLE_PLANNER", "1")
    db = SessionLocal()
    try:
        user_id = f"linked-messages-{uuid4().hex}"
        user = get_or_create_user(db, user_id)

        class PlannerProvider:
            async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
                return {
                    "intent": "new_intake",
                    "scope": "meal_specific",
                    "meal_link_action": "create_new_meal",
                    "target_meal_id": None,
                    "link_confidence": "high",
                    "boundary_reason": "new_meal_switch",
                    "clarification_blocking": False,
                    "normalized_user_input": user_payload["current_user_input"],
                }, {"stage": stage}

        class PrimaryProvider:
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
                return {
                    "food_origin": "generic_common",
                    "food_class": "simple_meal",
                    "needs_external_data": False,
                    "private_info_risk": "low",
                    "title": "滷味",
                    "components": ["滷味"],
                    "protein_g": 18,
                    "carb_g": 35,
                    "fat_g": 12,
                    "kcal_low": 260,
                    "kcal_high": 420,
                    "kcal_most_likely": 340,
                    "uncertainty_factors": [],
                    "followup_questions": [],
                    "top_uncertainty_drivers": [],
                    "external_data_query": "",
                }, {"stage": stage}

        payload = asyncio.run(
            run_text_meal_canary(
                EstimateRequest(text="我半夜吃了一個滷味", allow_search=False, user_id=user_id),
                provider=PrimaryProvider(),
                planner_provider=PlannerProvider(),
                primary_provider=PrimaryProvider(),
                request_id="linked-messages-test",
                search_adapter=None,
                db=db,
            )
        )
        latest_user_message = get_latest_message_for_role(db, user, "user")
        latest_assistant_message = get_latest_message_for_role(db, user, "assistant")
    finally:
        db.close()

    linked_meal_log_id = payload.trace_contract["persistence_decision"]["linked_meal_log_id"]
    assert linked_meal_log_id is not None
    assert latest_user_message is not None and latest_user_message.linked_meal_log_id == linked_meal_log_id
    assert latest_assistant_message is not None and latest_assistant_message.linked_meal_log_id == linked_meal_log_id


def test_local_resolvers_return_typed_source_classes() -> None:
    exact_candidates = resolve_exact_item("banana milk", limit=3)
    anchor_candidates = resolve_ingredient_anchors(["banana", "milk"], limit=4)

    assert all(item["source_class"] == "exact_item_db" for item in exact_candidates)
    assert all(item["tool_name"] == "resolve_exact_item" for item in exact_candidates)
    assert all(item["source_class"] == "base_nutrition_db" for item in anchor_candidates)
    assert all(item["tool_name"] == "resolve_ingredient_anchors" for item in anchor_candidates)


def test_canonical_safety_floor_prefers_body_plan_source_or_explicit_override() -> None:
    class FakeBodyPlan:
        safety_floor_kcal = 1450

    assert canonical_safety_floor_kcal(body_plan=FakeBodyPlan()) == 1450
    assert canonical_safety_floor_kcal(explicit_safety_floor_kcal=1200) == 1200
    assert canonical_safety_floor_kcal(body_plan={}) is None


def test_conversation_state_exposes_summary_and_memory_layers() -> None:
    db = SessionLocal()
    try:
        user_id = f"memory-state-{uuid4().hex}"
        user = get_or_create_user(db, user_id)
        append_message(db, user, "user", "我最近在減脂，早餐常喝無糖豆漿")
        append_message(db, user, "assistant", "收到")
        loaded = load_conversation_state(db, user_id=user_id, incoming_user_text="今天早餐喝無糖豆漿")
    finally:
        db.close()

    assert loaded.state.session_summary.active_goal is not None
    assert loaded.state.recent_turn_summary.user_messages
    assert any(hit.memory_type in {"goal", "preference", "routine_meal"} for hit in loaded.state.durable_memory_hits)


def test_fallback_planner_is_conservative_without_semantic_brand_inference() -> None:
    planner_result = fallback_planner_result(
        "我早餐吃摩斯漢堡",
        normalize_text=lambda text: text.strip(),
        normalize_user_input_for_estimation=lambda text: {
            "normalized_text": text.strip(),
            "normalizer_applied": False,
            "notes": [],
        },
    )

    assert planner_result.intent == "food_estimation"
    assert planner_result.meal_boundary == "start_new_meal"
    assert planner_result.boundary_confidence == "low"
    assert planner_result.planning_brief.entity_type == "unknown"
    assert planner_result.planning_brief.clarification_needed is False


def test_fallback_planner_does_not_semantically_attach_pending_question_context() -> None:
    db = SessionLocal()
    try:
        user_id = f"pending-followup-{uuid4().hex}"
        user = get_or_create_user(db, user_id)
        append_message(db, user, "user", "我早餐吃摩斯漢堡")
        loaded = load_conversation_state(db, user_id=user_id, incoming_user_text=None)
        loaded.state.pending_question = "你吃的是哪個品項或套餐？"
        loaded.state.latest_meal_title = "摩斯漢堡"
        planner_result = fallback_planner_result(
            "我是吃青梅豬排堡加紅茶",
            normalize_text=lambda text: text.strip(),
            normalize_user_input_for_estimation=lambda text: {
                "normalized_text": text.strip(),
                "normalizer_applied": False,
                "notes": [],
            },
        )
    finally:
        db.close()

    assert planner_result.intent == "food_estimation"
    assert planner_result.meal_boundary == "start_new_meal"
    assert planner_result.planning_brief.state_link == "standalone"
    assert planner_result.normalized_user_input == "我是吃青梅豬排堡加紅茶"


