from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.application.followup_policy import annotate_followup_policy
from app.infrastructure.session_record_store import retrieve_planner_context, sync_session_records
from app.observability.payload_builders import build_trace_contract
from app.observability.text_meal_observability import build_multi_turn_context
from app.database import SessionLocal, append_message, get_or_create_user, save_meal_log
from app.infrastructure.conversation_state_loader import load_conversation_state
from app.schemas import EstimateRequest, PlanningBrief, TurnIntentResult


def test_annotate_followup_policy_distinguishes_followup_modes() -> None:
    estimate_with_followup = annotate_followup_policy(
        {
            "estimated_kcal": 480,
            "followup_question": "這杯是大杯還是中杯？",
            "follow_up_needed": True,
            "follow_up_reasoning": "size materially changes estimate",
            "reasoning_state": {"missing_high_impact_slots": ["杯型"]},
        }
    )
    assert estimate_with_followup["followup_decision_type"] == "estimate_with_followup"
    assert "size" in estimate_with_followup["followup_targets"]
    assert estimate_with_followup["why_followup"] == "size materially changes estimate"

    ask_only = annotate_followup_policy(
        {
            "estimated_kcal": 0,
            "followup_question": "你夾了哪些滷味食材？",
            "follow_up_needed": True,
            "reasoning_state": {"missing_high_impact_slots": ["哪些食材"]},
        }
    )
    assert ask_only["followup_decision_type"] == "ask_followup_only"
    assert "main_items" in ask_only["followup_targets"]
    assert ask_only["reason_not_direct_answer"] == "high_impact_slot_missing"


def test_build_multi_turn_context_exposes_state_memory_layers() -> None:
    db = SessionLocal()
    try:
        user_id = f"state-memory-{uuid4().hex}"
        user = get_or_create_user(db, user_id)
        append_message(db, user, "user", "我早餐吃摩斯豬排堡")
        append_message(db, user, "assistant", "飲料是什麼？")
        save_meal_log(
            db,
            user,
            meal_title="摩斯豬排堡",
            raw_input="我早餐吃摩斯豬排堡",
            kcal=336,
            protein_g=14,
            carb_g=39,
            fat_g=14,
            components=[{"name": "摩斯豬排堡", "portion_hint": "1份"}],
            debug_steps=[],
            status="draft_unresolved",
            pending_question="飲料是什麼？",
        )
        loaded = load_conversation_state(db, user_id=user_id, incoming_user_text="不是麥當勞，是摩斯")
    finally:
        db.close()

    context = build_multi_turn_context(
        state=loaded.state,
        planner_intent="modification",
        context_snapshot="snapshot",
        retrieval_query_rewritten=False,
        original_retrieval_query=None,
        effective_retrieval_query=None,
    )
    assert context["active_meal_state"]["meal_title"] == "摩斯豬排堡"
    assert context["pending_followup_state"]["is_open"] is True
    assert context["dynamic_context_pack"]["pending_followup_state"]["pending_question"] == "飲料是什麼？"
    assert context["history_retrieval_router"] == ["state_memory", "typed_meal_records", "transcript_hybrid"]


def test_retrieve_planner_context_prefers_typed_meal_records_with_time_filters() -> None:
    session_id = f"context-router-{uuid4().hex}"
    now = datetime.now(timezone.utc)
    sync_session_records(
        session_id=session_id,
        transcript_records=[],
        meal_records=[
            {
                "session_id": session_id,
                "meal_id": 1,
                "title": "MOS pork burger breakfast",
                "raw_input": "today breakfast mos pork burger",
                "timestamp": now.isoformat(),
                "status": "finalized",
                "components": [{"name": "MOS pork burger", "portion_hint": "1 serving"}],
            },
            {
                "session_id": session_id,
                "meal_id": 2,
                "title": "familymart dinner box",
                "raw_input": "yesterday dinner familymart box",
                "timestamp": (now - timedelta(days=1)).isoformat(),
                "status": "finalized",
                "components": [{"name": "familymart dinner box", "portion_hint": "1 serving"}],
            },
        ],
    )

    _, meal_hits, _, diagnostics = retrieve_planner_context(
        session_id=session_id,
        query="today breakfast mos",
        active_meal_id=None,
        pending_question=None,
    )

    assert diagnostics["router_order"] == ["state_memory", "typed_meal_records", "transcript_hybrid"]
    assert diagnostics["query_filters"]["requested_meal_type"] == "breakfast"
    assert meal_hits
    assert meal_hits[0].metadata["title"] == "MOS pork burger breakfast"


def test_build_trace_contract_includes_followup_and_reasoning_fields() -> None:
    planner_result = TurnIntentResult(
        intent="food_estimation",
        meal_boundary="start_new_meal",
        boundary_confidence="high",
        resolved_query="珍珠奶茶",
        planning_brief=PlanningBrief(),
        route_hints={},
    )
    trace_contract = build_trace_contract(
        request=EstimateRequest(text="珍珠奶茶"),
        effective_request=EstimateRequest(text="珍珠奶茶"),
        planner_result=planner_result,
        planner_enabled=True,
        normalization={},
        risk_packet={},
        meal_template=None,
        template_override_blocked=False,
        retrieval_query=None,
        retrieved_knowledge=[],
        sources=[],
        used_search=False,
        search_query=None,
        current_parsed={},
        best_parsed={
            "response_mode_hint": "clarify_first",
            "missing_high_impact_slots": ["杯型"],
            "followup_targets": ["size"],
            "why_followup": "size materially changes estimate",
            "reason_not_direct_answer": "high_impact_slot_missing",
            "why_not_exact": "no exact lane",
            "why_no_more_tools": "brand missing and no verified context",
            "reasoning_state": {"search_attempt_count": 0},
        },
        best_source="primary",
        quality_signals={},
        retry_triggered=False,
        retry_reason=None,
    )

    assert trace_contract["missing_high_impact_slots"] == ["杯型"]
    assert trace_contract["followup_targets"] == ["size"]
    assert trace_contract["why_followup"] == "size materially changes estimate"
    assert trace_contract["why_not_exact"] == "no exact lane"
    assert trace_contract["why_no_more_tools"] == "brand missing and no verified context"
