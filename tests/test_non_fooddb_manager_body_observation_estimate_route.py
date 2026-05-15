from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.body.application import build_active_body_plan_view
from app.body.application.body_observation_service import get_latest_weight_observation
from app.composition import intake_routes
from app.composition.body_observation_manager_tool_runtime import body_observation_guard
from app.intake.application import chat_intents as intake_chat_intents
import app.intake.application as intake_application
from app.composition.onboarding_service import (
    OnboardingBootstrapInput,
    bootstrap_body_plan_for_date,
)
from app.database import get_db, get_or_create_user
from app.models import Base
from app.routes import router
from scripts.accurate_intake_body_observation_manager_fixture import BodyObservationManagerFixtureProvider


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _client(db: Session, provider: BodyObservationManagerFixtureProvider, monkeypatch: Any) -> TestClient:
    monkeypatch.setattr(intake_routes, "manager_provider", provider)
    monkeypatch.setattr(intake_routes, "search_provider", None)
    monkeypatch.setattr(intake_routes, "extract_provider", None)

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


class _EntryThenBodyObservationManagerProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"configured": True, "provider": "entry_then_body_observation_fixture"}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = dict(kwargs.get("user_payload") or {})
        available_tools = list(payload.get("available_tools") or [])
        round_index = int(payload.get("round_index") or 0)
        self.calls.append(
            {
                "available_tools": available_tools,
                "manager_loop_scope": payload.get("manager_loop_scope"),
                "tool_results": list(payload.get("tool_results") or []),
                "round_index": round_index,
            }
        )
        if "body.record_observation" not in available_tools:
            return (
                {
                    "manager_action": "final",
                    "intent": "body observation",
                    "intent_type": "body_observation",
                    "final_action": "no_commit",
                    "workflow_effect": "route_to_body_observation",
                    "target_attachment": {},
                    "exactness": "high",
                    "confidence": "high",
                    "evidence_posture": "body_observation_handoff",
                    "repair_ack": False,
                    "answer_contract": {},
                    "uncertainty_posture": "none",
                    "evidence_honesty_posture": "handoff_only",
                    "semantic_decision": {
                        "semantic_authority": "deterministic_fake_provider",
                        "current_turn_intent": "body_observation",
                        "target_attachment": {},
                        "workflow_effect": "route_to_body_observation",
                        "final_action_candidate": "record_observation",
                        "mutation_intent_candidate": "body_observation_write",
                        "source": "manager_structured_output",
                        "semantic_owner": "manager",
                    },
                    "tool_calls": [],
                },
                {"source": "entry_then_body_observation_fixture"},
            )
        if round_index == 0:
            return (
                {
                    "manager_action": "call_tools",
                    "tool_calls": [
                        {
                            "name": "body.record_observation",
                            "arguments": {"observation_type": "weight", "value": 84.0, "unit": "kg"},
                        }
                    ],
                },
                {"source": "entry_then_body_observation_fixture"},
            )
        return (
            {
                "manager_action": "final",
                "intent": "body_observation",
                "intent_type": "body_observation",
                "final_action": "answer_only",
                "workflow_effect": "record_weight",
                "target_attachment": {"mode": "body_observation_recorded"},
                "exactness": "high",
                "confidence": "high",
                "evidence_posture": "write_only_domain_mutation",
                "repair_ack": False,
                "answer_contract": {"reply_text": "Recorded weight 84.0 kg. Body plan was not changed."},
                "response_summary": "record_weight",
                "uncertainty_posture": "none",
                "evidence_honesty_posture": "mutation_result",
                "semantic_decision": {
                    "semantic_authority": "deterministic_fake_provider",
                    "current_turn_intent": "body_observation",
                    "target_attachment": {"mode": "body_observation_recorded"},
                    "workflow_effect": "record_weight",
                    "final_action_candidate": "answer_only",
                    "followup_posture": "none",
                    "mutation_intent_candidate": "body_observation_write",
                    "semantic_owner": "manager",
                },
                "tool_calls": [],
            },
            {"source": "entry_then_body_observation_fixture"},
        )


def _bootstrap_user_with_plan(db: Session, *, user_external_id: str) -> int:
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
            local_date="2026-05-07",
            timezone="Asia/Taipei",
        ),
    )
    return int(user.id)


def test_estimate_route_records_weight_via_manager_tool_loop_without_direct_parser(monkeypatch: Any) -> None:
    db = _session()
    provider = BodyObservationManagerFixtureProvider()
    client = _client(db, provider, monkeypatch)
    user_external_id = "manager-body-observation-route"
    user_id = _bootstrap_user_with_plan(db, user_external_id=user_external_id)
    before_plan = build_active_body_plan_view(db, user_id=user_id)

    monkeypatch.setattr(
        intake_routes,
        "build_workflow_routing_decision",
        lambda **_: SimpleNamespace(
            target_workflow_family="body_observation",
            disposition="open_new_workflow",
            phase_a_trace={},
            required_read_surfaces=[],
        ),
    )

    async def _unexpected_parser(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("direct weight parser must not run on manager-owned body observation path")

    monkeypatch.setattr(intake_chat_intents, "parse_weight_or_budget_intent", _unexpected_parser)
    monkeypatch.setattr(intake_application, "parse_weight_or_budget_intent", _unexpected_parser)

    response = client.post(
        "/estimate",
        json={
            "text": "my weight is 70kg",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": "2026-05-07",
        },
    )

    after_plan = build_active_body_plan_view(db, user_id=user_id)
    latest_weight = get_latest_weight_observation(db, user_id=user_id, local_date="2026-05-07")

    assert response.status_code == 200
    assert provider.calls[0]["available_tools"] == ["body.record_observation"]
    assert provider.calls[0]["tool_results"] == []
    assert provider.calls[1]["tool_results"][0]["tool_name"] == "body.record_observation"
    assert provider.calls[1]["tool_results"][0]["provenance"]["canonical_tool_name"] == "body.record_observation"
    assert response.json()["coach_message"] == "Recorded weight 70.0 kg. Body plan was not changed."

    payload = response.json()["payload"]
    assert payload["manager_decision"]["intent_type"] == "body_observation"
    assert payload["manager_decision"]["workflow_effect"] == "record_weight"
    assert payload["state_delta"]["body_observation_recorded"] is True
    assert payload["state_delta"]["meal_logged"] is False
    assert payload["state_delta"]["canonical_commit"] is False
    assert payload["state_delta"]["ledger_updated"] is False

    assert latest_weight is not None
    assert latest_weight.value == 70.0
    assert latest_weight.unit == "kg"
    assert after_plan.body_plan_id == before_plan.body_plan_id
    assert after_plan.daily_budget_kcal == before_plan.daily_budget_kcal
    assert after_plan.recommended_target_kcal == before_plan.recommended_target_kcal


def test_estimate_route_hands_body_observation_from_entry_manager_without_router_semantics(
    monkeypatch: Any,
) -> None:
    db = _session()
    provider = _EntryThenBodyObservationManagerProvider()
    client = _client(db, provider, monkeypatch)
    user_external_id = "entry-manager-body-observation-route"
    user_id = _bootstrap_user_with_plan(db, user_external_id=user_external_id)
    before_plan = build_active_body_plan_view(db, user_id=user_id)

    async def _unexpected_parser(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("direct weight parser must not run on manager-owned body observation path")

    monkeypatch.setattr(intake_chat_intents, "parse_weight_or_budget_intent", _unexpected_parser)
    monkeypatch.setattr(intake_application, "parse_weight_or_budget_intent", _unexpected_parser)

    response = client.post(
        "/estimate",
        json={
            "text": "my weight is 84kg",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": "2026-05-07",
        },
    )

    after_plan = build_active_body_plan_view(db, user_id=user_id)
    latest_weight = get_latest_weight_observation(db, user_id=user_id, local_date="2026-05-07")

    assert response.status_code == 200
    assert provider.calls[0]["manager_loop_scope"] == "turn_entry_or_read_only"
    assert "body.record_observation" not in provider.calls[0]["available_tools"]
    assert provider.calls[1]["available_tools"] == ["body.record_observation"]
    assert provider.calls[2]["tool_results"][0]["tool_name"] == "body.record_observation"
    assert response.json()["coach_message"] == "Recorded weight 84.0 kg. Body plan was not changed."

    payload = response.json()["payload"]
    assert payload["manager_decision"]["intent_type"] == "body_observation"
    assert payload["manager_decision"]["workflow_effect"] == "record_weight"
    assert payload["state_delta"]["body_observation_recorded"] is True
    assert latest_weight is not None
    assert latest_weight.value == 84.0
    assert after_plan.body_plan_id == before_plan.body_plan_id
    assert after_plan.daily_budget_kcal == before_plan.daily_budget_kcal
    assert after_plan.recommended_target_kcal == before_plan.recommended_target_kcal


def test_body_observation_guard_requests_bounded_repair_when_tool_result_missing() -> None:
    outcome = body_observation_guard(
        manager_payload={
            "intent_type": "body_observation",
            "workflow_effect": "record_weight",
            "semantic_decision": {
                "current_turn_intent": "body_observation",
                "mutation_intent_candidate": "body_observation_write",
            },
        },
        tool_results=[],
        resolved_state=object(),
    )

    assert outcome["ok"] is False
    assert outcome["failure_family"] == "body_observation_missing_successful_tool_result"
    assert outcome["repair_request"] is True
    assert outcome["required_tool"] == "body.record_observation"
