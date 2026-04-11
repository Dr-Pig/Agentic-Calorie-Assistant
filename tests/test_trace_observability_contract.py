from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.logging import get_trace_summaries
from app.main import app
from app.observability.text_meal_observability import build_trace_envelope


client = TestClient(app)


def test_build_trace_envelope_produces_machine_first_contract() -> None:
    trace_contract = {
        "planner_output": {"intent": "food_estimation", "planner_mode": "llm"},
        "route_family": "default",
        "followup_policy_decision": "direct_best_effort",
        "followup_decision": "answer",
        "grounding_attempts": [{"kind": "local_retrieval", "query": "banana milk", "hit_count": 2, "used": True}],
        "grounding_summary": {
            "reference_card": {"title": "Banana Milk", "kcal": 180},
        },
        "grounding_contradiction": False,
        "match_confidence": "high",
        "db_hit_type": "exact_truth",
        "best_answer_source": "with_local_knowledge",
        "retry_triggered": False,
        "retry_reason": None,
        "rescue_applied": {"rescue_layer": None, "candidate_guard_applied": False},
        "final_answer_summary": {"decision": "DIRECT_ANSWER", "estimated_kcal": 180},
        "context_pack_trace": {"sections": [{"name": "session_state", "estimated_tokens": 10}], "total_estimated_tokens": 10},
        "tool_decision_trace": {"available_tools": ["resolve_exact_item"], "candidate_tool_calls": [], "executed_tool_calls": []},
        "boundary_trace": {"meal_boundary": "start_new_meal", "active_meal_context_allowed": False},
        "judge_trace": {"judge_model": "deepseek-chat", "candidate_count": 2, "selected_titles": ["Banana Milk"], "dropped_titles": [], "judge_decision": "keep_best", "requested_action": None},
        "evidence_resolution_trace": {"local_exact_candidates": [], "local_anchor_candidates": [], "search_candidates": [], "doc_read_fragments": [], "final_kept_evidence": [], "dropped_evidence": []},
        "memory_trace": {"durable_memory_enabled": True, "hits": [], "write_candidates": []},
    }
    llm_traces = [
        {
            "stage": "planner_pass_initial",
            "request_payload": {"messages": []},
            "parsed_object": {"intent": "food_estimation"},
            "attempt_index": 1,
            "trigger_reason": "initial_planning",
            "duration_ms": 12,
            "stage_input_summary": {"user_payload_keys": ["raw_user_input"]},
            "stage_output_summary": {"decision": None, "estimated_kcal": None},
            "handoff_contract": {"context_snapshot_present": True},
        },
        {
            "stage": "primary_answer_pass_initial",
            "request_payload": {"messages": []},
            "parsed_object": {"decision": "DIRECT_ANSWER", "estimated_kcal": 180},
            "attempt_index": 1,
            "trigger_reason": "main_estimation",
            "duration_ms": 25,
            "stage_input_summary": {"user_payload_keys": ["user_input", "evidence"]},
            "stage_output_summary": {"decision": "DIRECT_ANSWER", "estimated_kcal": 180},
            "handoff_contract": {"evidence_count": 2},
        },
    ]
    debug_steps = [
        {"step": "deterministic_enrichment", "stage_label": "primary", "deterministic_applied": True, "deterministic_hit": True, "deterministic_estimated_kcal": 180, "estimate_mode": "anchored_component"},
    ]

    envelope = build_trace_envelope(
        request_id="req-trace-1",
        user_id="trace-user",
        timestamp="2026-04-02T00:00:00Z",
        provider_name="FakeProvider",
        schema_signature="trace.v2",
        source_page_version="dashboard-v1",
        trace_contract=trace_contract,
        llm_traces=llm_traces,
        debug_steps=debug_steps,
        quality_signals={"invalid_zero_kcal_candidate": False},
        best_answer_source="with_local_knowledge",
        retry_triggered=False,
        multi_turn_context={"is_multi_turn": False},
    )

    assert envelope.trace_meta["request_id"] == "req-trace-1"
    assert envelope.decision_journal["best_answer_source"] == "with_local_knowledge"
    assert envelope.evidence_journal["local_hit_count"] == 2
    assert envelope.diagnosis["suggested_next_action"] == "no_action_required"
    assert len(envelope.span_timeline) >= 3
    assert envelope.span_timeline[0]["stage"] == "planner_pass_initial"
    assert envelope.context_pack_trace["total_estimated_tokens"] == 10
    assert envelope.tool_decision_trace["available_tools"] == ["resolve_exact_item"]
    assert envelope.boundary_trace["meal_boundary"] == "start_new_meal"
    assert envelope.judge_trace["judge_model"] == "deepseek-chat"
    assert envelope.memory_trace["durable_memory_enabled"] is True


def test_trace_summaries_include_agent_feedback_fields(tmp_path, monkeypatch) -> None:
    request_dir = tmp_path / "requests"
    request_dir.mkdir(parents=True)
    monkeypatch.setattr("app.logging.REQUEST_TRACE_DIR", request_dir)

    artifact = {
        "request_id": "trace-123",
        "timestamp": "2026-04-02T00:00:00Z",
        "request": {"user_id": "user-1", "text": "banana milk", "allow_search": False},
        "trace_meta": {"request_id": "trace-123", "user_id": "user-1", "timestamp": "2026-04-02T00:00:00Z"},
        "diagnosis": {"failed_layer": "grounding", "repairability": "high", "trace_health": "degraded"},
        "trace_contract": {"planner_output": {"planner_mode": "llm"}, "best_answer_source": "with_local_knowledge", "retry_triggered": True},
        "multi_turn_context": {"is_multi_turn": True, "turn_intent": "clarification"},
        "north_star_evaluation": {"win_loss_neutral": "loss"},
        "token_usage": {"total_tokens": 321},
    }
    (request_dir / "trace-123.json").write_text(json.dumps(artifact), encoding="utf-8")

    summaries = get_trace_summaries(limit=10)
    assert summaries["traces"][0]["failed_layer"] == "grounding"
    assert summaries["traces"][0]["repairability"] == "high"
    assert summaries["traces"][0]["planner_mode"] == "llm"
    assert summaries["traces"][0]["best_answer_source"] == "with_local_knowledge"
    assert summaries["traces"][0]["retry_triggered"] is True


def test_estimate_to_trace_to_dashboard_loop_smoke(tmp_path, monkeypatch) -> None:
    request_dir = tmp_path / "requests"
    request_dir.mkdir(parents=True)
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True)
    monkeypatch.setattr("app.logging.REQUEST_TRACE_DIR", request_dir)
    monkeypatch.setattr("app.logging.LOG_DIR", log_dir)
    monkeypatch.setattr("app.logging.LOG_FILE", log_dir / "events.jsonl")

    class FakeProvider:
        def readiness(self) -> dict:
            return {
                "provider": "fake",
                "stage_models": {
                    "task_meal_link_pass": "fake-planner",
                    "decision_pass": "fake-model",
                    "nutrition_resolution_pass_initial": "fake-model",
                    "final_response_pass": "fake-model",
                },
            }

        async def complete_with_trace(self, *, system_prompt, user_payload, stage, max_tokens):
            if stage == "task_meal_link_pass":
                return {
                    "intent": "new_intake",
                    "scope": "meal_specific",
                    "meal_link_action": "create_new_meal",
                    "target_meal_id": None,
                    "link_confidence": "high",
                    "boundary_reason": "new_meal",
                    "clarification_blocking": False,
                    "normalized_user_input": user_payload["current_user_input"],
                }, {"stage": stage, "usage": {"prompt_tokens": 5, "completion_tokens": 10}}
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
                }, {"stage": stage, "usage": {"prompt_tokens": 6, "completion_tokens": 8}}
            if stage == "nutrition_resolution_pass_initial":
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
                    "title": user_payload["current_user_input"],
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
                }, {"stage": stage, "usage": {"prompt_tokens": 10, "completion_tokens": 20}}
            if stage == "final_response_pass":
                return {
                    "reply_text": "banana milk我會先抓約 180 kcal。",
                    "ui_hints": {},
                }, {"stage": stage, "usage": {"prompt_tokens": 8, "completion_tokens": 12}}
            raise AssertionError(stage)

    class FakeSearch:
        def readiness(self) -> dict:
            return {"provider": "fake-search", "configured": True}

        async def search(self, query: str, max_results: int = 5):
            return []

    monkeypatch.setattr("app.routes.provider", FakeProvider())
    monkeypatch.setattr("app.routes.planner_provider", FakeProvider())
    monkeypatch.setattr("app.routes.primary_provider", FakeProvider())
    monkeypatch.setattr("app.routes.search_provider", FakeSearch())

    response = client.post("/estimate", json={"text": "banana milk", "allow_search": False, "user_id": "trace-loop-user"})
    assert response.status_code == 200
    request_id = response.json()["request_id"]

    traces_response = client.get("/admin/traces")
    assert traces_response.status_code == 200
    trace_ids = [item["id"] for item in traces_response.json()["traces"]]
    assert request_id in trace_ids

    trace_detail = client.get(f"/admin/trace/{request_id}")
    assert trace_detail.status_code == 200
    detail = trace_detail.json()
    assert "diagnosis" in detail
    assert "span_timeline" in detail
    assert detail["trace_contract"]["best_answer_source"] in {"initial", "primary", "with_local_knowledge", "reference_card"}

    dashboard_response = client.get("/dashboard")
    assert dashboard_response.status_code == 200
    assert "CANARY_INSIGHT" in dashboard_response.text
    assert "Suggested Action" in dashboard_response.text
