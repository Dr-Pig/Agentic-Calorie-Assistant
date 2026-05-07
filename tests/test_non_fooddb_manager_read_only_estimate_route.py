from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.body.application.body_observation_service import record_body_observation_to_canonical
from app.composition import intake_routes
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.onboarding_service import (
    OnboardingBootstrapInput,
    bootstrap_body_plan_for_date,
)
from app.database import get_db, get_or_create_user
from app.models import Base
from app.routes import router
from app.schemas import CommitRequestCandidate


class _ReadOnlyBudgetManagerProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"configured": True, "provider": "read_only_budget_fixture"}

    async def complete_with_trace(
        self,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        self.calls.append(
            {
                "available_tools": list(user_payload.get("available_tools") or []),
                "tool_results": list(user_payload.get("tool_results") or []),
                "round_index": user_payload.get("round_index"),
            }
        )
        if int(user_payload.get("round_index") or 0) == 0:
            return (
                {
                    "manager_action": "call_tools",
                    "tool_calls": [{"name": "budget.get_remaining_calories"}],
                },
                {"source": "read_only_budget_fixture"},
            )
        return (
            {
                "manager_action": "final",
                "intent": "answer_remaining_budget",
                "intent_type": "answer_remaining_budget",
                "final_action": "answer_only",
                "workflow_effect": "answer_budget_summary_without_state_mutation",
                "target_attachment": {"mode": "read_only_budget_answer"},
                "exactness": "read_only_state",
                "confidence": "high",
                "evidence_posture": "read_only_state",
                "repair_ack": False,
                "answer_contract": {"reply_text": "use remaining budget renderer"},
                "response_summary": "answer_budget_summary_without_state_mutation",
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "read_only_state",
                "semantic_decision": {
                    "semantic_authority": "deterministic_fake_provider",
                    "current_turn_intent": "answer_remaining_budget",
                    "target_attachment": {"mode": "read_only_budget_answer"},
                    "workflow_effect": "answer_budget_summary_without_state_mutation",
                    "final_action_candidate": "answer_only",
                    "estimation_posture": "not_applicable",
                    "followup_posture": "none",
                    "followup_targets": [],
                    "mutation_intent_candidate": "no_mutation",
                    "uncertainty_posture": "bounded",
                    "source": "read_only_budget_fixture",
                    "semantic_owner": "manager",
                    "deterministic_role": "fixture_simulates_manager_output_only",
                },
                "tool_calls": [],
            },
            {"source": "read_only_budget_fixture"},
        )


class _ReadOnlyBodyGoalManagerProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"configured": True, "provider": "read_only_body_goal_fixture"}

    async def complete_with_trace(
        self,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        self.calls.append(
            {
                "available_tools": list(user_payload.get("available_tools") or []),
                "tool_results": list(user_payload.get("tool_results") or []),
                "round_index": user_payload.get("round_index"),
            }
        )
        if int(user_payload.get("round_index") or 0) == 0:
            return (
                {
                    "manager_action": "call_tools",
                    "tool_calls": [{"name": "body.get_active_plan"}],
                },
                {"source": "read_only_body_goal_fixture"},
            )
        return (
            {
                "manager_action": "final",
                "intent": "general_chat",
                "intent_type": "general_chat",
                "final_action": "answer_only",
                "workflow_effect": "answer_goal_summary_without_state_mutation",
                "target_attachment": {"mode": "read_only_body_goal_answer"},
                "exactness": "read_only_state",
                "confidence": "high",
                "evidence_posture": "read_only_state",
                "repair_ack": False,
                "answer_contract": {"reply_text": "目前目標是減脂，今天目標維持現有計畫。"},
                "response_summary": "answer_goal_summary_without_state_mutation",
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "read_only_state",
                "semantic_decision": {
                    "semantic_authority": "deterministic_fake_provider",
                    "current_turn_intent": "general_chat",
                    "target_attachment": {"mode": "read_only_body_goal_answer"},
                    "workflow_effect": "answer_goal_summary_without_state_mutation",
                    "final_action_candidate": "answer_only",
                    "estimation_posture": "not_applicable",
                    "followup_posture": "none",
                    "followup_targets": [],
                    "mutation_intent_candidate": "no_mutation",
                    "uncertainty_posture": "bounded",
                    "source": "read_only_body_goal_fixture",
                    "semantic_owner": "manager",
                    "deterministic_role": "fixture_simulates_manager_output_only",
                },
                "tool_calls": [],
            },
            {"source": "read_only_body_goal_fixture"},
        )


class _UnsupportedGeneralChatManagerProvider:
    def readiness(self) -> dict[str, Any]:
        return {"configured": True, "provider": "unsupported_general_chat_fixture"}

    async def complete_with_trace(
        self,
        **_: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return (
            {
                "manager_action": "final",
                "intent": "general_chat",
                "intent_type": "general_chat",
                "final_action": "answer_only",
                "workflow_effect": "fallback_answer_without_supported_read_tool",
                "target_attachment": {"mode": "read_only_app_help_answer"},
                "exactness": "read_only_state",
                "confidence": "high",
                "evidence_posture": "read_only_state",
                "repair_ack": False,
                "answer_contract": {"reply_text": "這條 generic chat lane 還沒收斂進 manager tool loop。"},
                "response_summary": "fallback_answer_without_supported_read_tool",
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "read_only_state",
                "semantic_decision": {
                    "semantic_authority": "deterministic_fake_provider",
                    "current_turn_intent": "general_chat",
                    "target_attachment": {"mode": "read_only_app_help_answer"},
                    "workflow_effect": "fallback_answer_without_supported_read_tool",
                    "final_action_candidate": "answer_only",
                    "estimation_posture": "not_applicable",
                    "followup_posture": "none",
                    "followup_targets": [],
                    "mutation_intent_candidate": "no_mutation",
                    "uncertainty_posture": "bounded",
                    "source": "unsupported_general_chat_fixture",
                    "semantic_owner": "manager",
                    "deterministic_role": "fixture_simulates_manager_output_only",
                },
                "tool_calls": [],
            },
            {"source": "unsupported_general_chat_fixture"},
        )


class _AppUsageManagerProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"configured": True, "provider": "app_usage_fixture"}

    async def complete_with_trace(
        self,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        self.calls.append(
            {
                "available_tools": list(user_payload.get("available_tools") or []),
                "tool_results": list(user_payload.get("tool_results") or []),
                "round_index": user_payload.get("round_index"),
            }
        )
        if int(user_payload.get("round_index") or 0) == 0:
            return (
                {
                    "manager_action": "call_tools",
                    "tool_calls": [{"name": "app.answer_usage_question"}],
                },
                {"source": "app_usage_fixture"},
            )
        return (
            {
                "manager_action": "final",
                "intent": "general_chat",
                "intent_type": "general_chat",
                "final_action": "answer_only",
                "workflow_effect": "answer_general_product_question_without_state_mutation",
                "target_attachment": {"mode": "read_only_app_help_answer"},
                "exactness": "read_only_state",
                "confidence": "high",
                "evidence_posture": "read_only_state",
                "repair_ack": False,
                "answer_contract": {
                    "reply_text": "I can answer general product questions here, but I will not change state from this path."
                },
                "response_summary": "answer_general_product_question_without_state_mutation",
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "read_only_state",
                "semantic_decision": {
                    "semantic_authority": "deterministic_fake_provider",
                    "current_turn_intent": "general_chat",
                    "target_attachment": {"mode": "read_only_app_help_answer"},
                    "workflow_effect": "answer_general_product_question_without_state_mutation",
                    "final_action_candidate": "answer_only",
                    "estimation_posture": "not_applicable",
                    "followup_posture": "none",
                    "followup_targets": [],
                    "mutation_intent_candidate": "no_mutation",
                    "uncertainty_posture": "bounded",
                    "source": "app_usage_fixture",
                    "semantic_owner": "manager",
                    "deterministic_role": "fixture_simulates_manager_output_only",
                },
                "tool_calls": [],
            },
            {"source": "app_usage_fixture"},
        )


class _DayMealLogManagerProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"configured": True, "provider": "day_meal_log_fixture"}

    async def complete_with_trace(
        self,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        self.calls.append(
            {
                "available_tools": list(user_payload.get("available_tools") or []),
                "tool_results": list(user_payload.get("tool_results") or []),
                "round_index": user_payload.get("round_index"),
            }
        )
        if int(user_payload.get("round_index") or 0) == 0:
            return (
                {
                    "manager_action": "call_tools",
                    "tool_calls": [{"name": "budget.get_day_meal_log"}],
                },
                {"source": "day_meal_log_fixture"},
            )
        return (
            {
                "manager_action": "final",
                "intent": "general_chat",
                "intent_type": "general_chat",
                "final_action": "answer_only",
                "workflow_effect": "answer_day_meal_log_without_state_mutation",
                "target_attachment": {"mode": "read_only_day_meal_log_answer"},
                "exactness": "read_only_state",
                "confidence": "high",
                "evidence_posture": "read_only_state",
                "repair_ack": False,
                "answer_contract": {"reply_text": "今天已記錄 breakfast sandwich。"},
                "response_summary": "answer_day_meal_log_without_state_mutation",
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "read_only_state",
                "semantic_decision": {
                    "semantic_authority": "deterministic_fake_provider",
                    "current_turn_intent": "general_chat",
                    "target_attachment": {"mode": "read_only_day_meal_log_answer"},
                    "workflow_effect": "answer_day_meal_log_without_state_mutation",
                    "final_action_candidate": "answer_only",
                    "estimation_posture": "not_applicable",
                    "followup_posture": "none",
                    "followup_targets": [],
                    "mutation_intent_candidate": "no_mutation",
                    "uncertainty_posture": "bounded",
                    "source": "day_meal_log_fixture",
                    "semantic_owner": "manager",
                    "deterministic_role": "fixture_simulates_manager_output_only",
                },
                "tool_calls": [],
            },
            {"source": "day_meal_log_fixture"},
        )


class _PublicReadOnlyGeneralToolManagerProvider:
    def __init__(self, *, tool_name: str, workflow_effect: str, target_mode: str, reply_text: str) -> None:
        self.calls: list[dict[str, Any]] = []
        self._tool_name = tool_name
        self._workflow_effect = workflow_effect
        self._target_mode = target_mode
        self._reply_text = reply_text

    def readiness(self) -> dict[str, Any]:
        return {"configured": True, "provider": "public_read_only_general_fixture"}

    async def complete_with_trace(
        self,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        self.calls.append(
            {
                "available_tools": list(user_payload.get("available_tools") or []),
                "tool_results": list(user_payload.get("tool_results") or []),
                "round_index": user_payload.get("round_index"),
            }
        )
        if int(user_payload.get("round_index") or 0) == 0:
            return (
                {
                    "manager_action": "call_tools",
                    "tool_calls": [{"name": self._tool_name}],
                },
                {"source": "public_read_only_general_fixture"},
            )
        return (
            {
                "manager_action": "final",
                "intent": "general_chat",
                "intent_type": "general_chat",
                "final_action": "answer_only",
                "workflow_effect": self._workflow_effect,
                "target_attachment": {"mode": self._target_mode},
                "exactness": "read_only_state",
                "confidence": "high",
                "evidence_posture": "read_only_state",
                "repair_ack": False,
                "answer_contract": {"reply_text": self._reply_text},
                "response_summary": self._workflow_effect,
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "read_only_state",
                "semantic_decision": {
                    "semantic_authority": "deterministic_fake_provider",
                    "current_turn_intent": "general_chat",
                    "target_attachment": {"mode": self._target_mode},
                    "workflow_effect": self._workflow_effect,
                    "final_action_candidate": "answer_only",
                    "estimation_posture": "not_applicable",
                    "followup_posture": "none",
                    "followup_targets": [],
                    "mutation_intent_candidate": "no_mutation",
                    "uncertainty_posture": "bounded",
                    "source": "public_read_only_general_fixture",
                    "semantic_owner": "manager",
                    "deterministic_role": "fixture_simulates_manager_output_only",
                },
                "tool_calls": [],
            },
            {"source": "public_read_only_general_fixture"},
        )


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _client(
    db: Session,
    provider: _ReadOnlyBudgetManagerProvider,
    monkeypatch: Any,
) -> TestClient:
    monkeypatch.setattr(intake_routes, "manager_provider", provider)
    monkeypatch.setattr(intake_routes, "search_provider", None)
    monkeypatch.setattr(intake_routes, "extract_provider", None)

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _bootstrap_budget_state(db: Session, *, user_external_id: str) -> None:
    user = get_or_create_user(db, user_external_id)
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=30,
            height_cm=165.0,
            current_weight_kg=58.0,
            activity_level="sedentary",
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            local_date="2026-05-06",
        ),
    )
    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="budget-read-breakfast",
            manager_intent="food_estimation",
            version_reason="new_intake",
            meal_title="breakfast sandwich",
            raw_input="breakfast sandwich",
            estimated_kcal=420,
            protein_g=18,
            carb_g=32,
            fat_g=14,
            resolution_status="completed_meal",
            local_date="2026-05-06",
        ),
    )


def test_estimate_route_uses_manager_read_only_tool_loop_for_budget_query(
    monkeypatch: Any,
) -> None:
    db = _session()
    provider = _ReadOnlyBudgetManagerProvider()
    client = _client(db, provider, monkeypatch)
    user_external_id = "manager-read-only-budget-route"
    _bootstrap_budget_state(db, user_external_id=user_external_id)

    response = client.post(
        "/estimate",
        json={
            "text": "我今天還能吃多少？",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": "2026-05-06",
        },
    )

    assert response.status_code == 200
    assert provider.calls[0]["available_tools"] == [
        "budget.get_today_summary",
        "budget.get_remaining_calories",
        "budget.get_day_meal_log",
        "body.get_active_plan",
        "body.get_latest_observation",
        "calibration.get_pending_proposal",
        "app.answer_usage_question",
    ]
    assert provider.calls[0]["tool_results"] == []
    assert provider.calls[1]["tool_results"][0]["tool_name"] == "budget.get_remaining_calories"
    payload = response.json()["payload"]
    assert payload["manager_decision"]["intent_type"] == "answer_remaining_budget"
    assert payload["manager_decision"]["workflow_effect"] == "answer_budget_summary_without_state_mutation"
    assert payload["state_delta"]["canonical_commit"] is False
    assert payload["state_delta"]["ledger_updated"] is False
    assert payload["state_delta"]["meal_logged"] is False
    assert (
        provider.calls[1]["tool_results"][0]["evidence"]["remaining_budget_contract"]["remaining_kcal"]
        == payload["remaining_budget"]["remaining_kcal"]
    )
    assert (
        provider.calls[1]["tool_results"][0]["evidence"]["remaining_budget_contract"]["daily_target_kcal"]
        == payload["remaining_budget"]["daily_target_kcal"]
    )


def test_estimate_route_supports_manager_read_only_body_goal_answer(
    monkeypatch: Any,
) -> None:
    db = _session()
    provider = _ReadOnlyBodyGoalManagerProvider()
    client = _client(db, provider, monkeypatch)
    user_external_id = "manager-read-only-body-goal-route"
    _bootstrap_budget_state(db, user_external_id=user_external_id)

    response = client.post(
        "/estimate",
        json={
            "text": "我現在的目標是什麼？",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": "2026-05-06",
        },
    )

    assert response.status_code == 200
    assert response.json()["coach_message"] == "目前目標是減脂，今天目標維持現有計畫。"
    assert provider.calls[1]["tool_results"][0]["tool_name"] == "body.get_active_plan"
    assert provider.calls[1]["tool_results"][0]["evidence"]["active_body_plan_view"]["goal_type"] == "lose_weight"
    payload = response.json()["payload"]
    assert payload["manager_decision"]["intent_type"] == "general_chat"
    assert payload["manager_decision"]["workflow_effect"] == "answer_goal_summary_without_state_mutation"
    assert payload["state_delta"]["canonical_commit"] is False
    assert payload["state_delta"]["ledger_updated"] is False


def test_estimate_route_rejects_unsupported_general_chat_fallback_lane(
    monkeypatch: Any,
) -> None:
    db = _session()
    provider = _UnsupportedGeneralChatManagerProvider()
    client = _client(db, provider, monkeypatch)
    _bootstrap_budget_state(db, user_external_id="unsupported-general-chat-route")

    response = client.post(
        "/estimate",
        json={
            "text": "我現在的目標是什麼？",
            "allow_search": False,
            "user_id": "unsupported-general-chat-route",
            "local_date": "2026-05-06",
        },
    )

    assert response.status_code == 500
    assert response.json()["error"] == "internal_server_error"


def test_estimate_route_uses_manager_read_only_tool_loop_for_app_usage_help(
    monkeypatch: Any,
) -> None:
    db = _session()
    provider = _AppUsageManagerProvider()
    client = _client(db, provider, monkeypatch)

    response = client.post(
        "/estimate",
        json={
            "text": "這個 app 怎麼用？",
            "allow_search": False,
            "user_id": "app-usage-manager-route",
            "local_date": "2026-05-06",
        },
    )

    assert response.status_code == 200
    assert provider.calls[0]["available_tools"] == [
        "budget.get_today_summary",
        "budget.get_remaining_calories",
        "budget.get_day_meal_log",
        "body.get_active_plan",
        "body.get_latest_observation",
        "calibration.get_pending_proposal",
        "app.answer_usage_question",
    ]
    assert provider.calls[0]["tool_results"] == []
    assert provider.calls[1]["tool_results"][0]["tool_name"] == "app.answer_usage_question"
    payload = response.json()["payload"]
    assert payload["manager_decision"]["intent_type"] == "general_chat"
    assert payload["manager_decision"]["workflow_effect"] == "answer_general_product_question_without_state_mutation"
    assert response.json()["coach_message"] == (
        "I can answer general product questions here, but I will not change state from this path."
    )


def test_estimate_route_supports_manager_read_only_latest_weight_answer(
    monkeypatch: Any,
) -> None:
    db = _session()
    provider = _PublicReadOnlyGeneralToolManagerProvider(
        tool_name="body.get_latest_observation",
        workflow_effect="answer_latest_weight_without_state_mutation",
        target_mode="read_only_latest_weight_answer",
        reply_text="Latest weight is available from body read model.",
    )
    client = _client(db, provider, monkeypatch)
    user_external_id = "manager-read-only-latest-weight-route"
    _bootstrap_budget_state(db, user_external_id=user_external_id)
    user = get_or_create_user(db, user_external_id)
    record_body_observation_to_canonical(
        db,
        user=user,
        value=57.8,
        unit="kg",
        observed_at=datetime(2026, 5, 6, 7, 30, 0),
        local_date="2026-05-06",
    )

    response = client.post(
        "/estimate",
        json={
            "text": "latest weight?",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": "2026-05-06",
        },
    )

    assert response.status_code == 200
    assert provider.calls[1]["tool_results"][0]["tool_name"] == "body.get_latest_observation"
    assert provider.calls[1]["tool_results"][0]["evidence"]["latest_weight_observation"]["value"] == 57.8
    payload = response.json()["payload"]
    assert payload["manager_decision"]["workflow_effect"] == "answer_latest_weight_without_state_mutation"
    assert payload["state_delta"]["canonical_commit"] is False
    assert payload["state_delta"]["ledger_updated"] is False
    assert response.json()["coach_message"] == "Latest weight is available from body read model."


def test_estimate_route_supports_manager_read_only_calibration_pending_proposal_answer(
    monkeypatch: Any,
) -> None:
    db = _session()
    provider = _PublicReadOnlyGeneralToolManagerProvider(
        tool_name="calibration.get_pending_proposal",
        workflow_effect="answer_calibration_pending_proposal_without_state_mutation",
        target_mode="read_only_calibration_pending_proposal_answer",
        reply_text="No pending calibration proposal is available.",
    )
    client = _client(db, provider, monkeypatch)
    user_external_id = "manager-read-only-calibration-route"
    _bootstrap_budget_state(db, user_external_id=user_external_id)

    response = client.post(
        "/estimate",
        json={
            "text": "any pending calibration?",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": "2026-05-06",
        },
    )

    assert response.status_code == 200
    assert provider.calls[1]["tool_results"][0]["tool_name"] == "calibration.get_pending_proposal"
    assert provider.calls[1]["tool_results"][0]["evidence"]["pending_proposal_status"] == "not_available"
    payload = response.json()["payload"]
    assert payload["manager_decision"]["workflow_effect"] == (
        "answer_calibration_pending_proposal_without_state_mutation"
    )
    assert payload["state_delta"]["canonical_commit"] is False
    assert payload["state_delta"]["ledger_updated"] is False
    assert response.json()["coach_message"] == "No pending calibration proposal is available."


def test_estimate_route_uses_manager_read_only_tool_loop_for_day_meal_log_query(
    monkeypatch: Any,
) -> None:
    db = _session()
    provider = _DayMealLogManagerProvider()
    client = _client(db, provider, monkeypatch)
    user_external_id = "manager-read-only-day-meal-log-route"
    _bootstrap_budget_state(db, user_external_id=user_external_id)

    response = client.post(
        "/estimate",
        json={
            "text": "我今天吃了什麼？",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": "2026-05-06",
        },
    )

    assert response.status_code == 200
    assert provider.calls[0]["tool_results"] == []
    assert provider.calls[1]["tool_results"][0]["tool_name"] == "budget.get_day_meal_log"
    assert provider.calls[1]["tool_results"][0]["evidence"]["current_budget_view"]["meals"]
    payload = response.json()["payload"]
    assert payload["manager_decision"]["intent_type"] == "general_chat"
    assert payload["manager_decision"]["workflow_effect"] == "answer_day_meal_log_without_state_mutation"
    assert response.json()["coach_message"] == "今天已記錄 breakfast sandwich。"
