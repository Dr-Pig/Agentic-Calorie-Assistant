from __future__ import annotations

import secrets
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.composition import intake_routes
from app.database import get_db
from app.models import Base
from app.routes import router


class _ManualTargetManagerProvider:
    def __init__(self, target_kcal: int | None) -> None:
        self.target_kcal = target_kcal
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"configured": True, "provider": "manual_target_fixture", "live_llm_invoked": False}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        self.calls.append(
            {
                "raw_user_input": user_payload.get("raw_user_input"),
                "available_tools": list(user_payload.get("available_tools") or []),
                "round_index": user_payload.get("round_index"),
            }
        )
        target_attachment = {"mode": "manual_daily_target"}
        answer_contract: dict[str, Any] = {"reply_text": "manual target update requested"}
        semantic_decision: dict[str, Any] = {
            "semantic_authority": "deterministic_fake_provider",
            "current_turn_intent": "set_manual_daily_target",
            "target_attachment": dict(target_attachment),
            "workflow_effect": "manual_daily_target_update",
            "final_action_candidate": "target_updated",
            "estimation_posture": "not_applicable",
            "followup_posture": "none",
            "followup_targets": [],
            "mutation_intent_candidate": "budget_target_write",
            "uncertainty_posture": "bounded",
            "source": "manual_target_fixture",
            "semantic_owner": "manager",
            "deterministic_role": "fixture_simulates_manager_output_only",
        }
        if self.target_kcal is not None:
            target_attachment["daily_target_kcal"] = self.target_kcal
            answer_contract["daily_target_kcal"] = self.target_kcal
            semantic_decision["target_attachment"] = dict(target_attachment)
            semantic_decision["daily_target_kcal"] = self.target_kcal
        return (
            {
                "manager_action": "final",
                "intent": "set_manual_daily_target",
                "intent_type": "set_manual_daily_target",
                "final_action": "target_updated",
                "workflow_effect": "manual_daily_target_update",
                "target_attachment": target_attachment,
                "exactness": "deterministic_fixture",
                "confidence": "high",
                "evidence_posture": "read_only_state",
                "repair_ack": False,
                "answer_contract": answer_contract,
                "response_summary": "manual_daily_target_update",
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "not_applicable",
                "semantic_decision": semantic_decision,
                "tool_calls": [],
            },
            {"source": "manual_target_fixture", "live_llm_invoked": False},
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


def _client(db: Session, provider: _ManualTargetManagerProvider, monkeypatch) -> TestClient:
    monkeypatch.setattr(intake_routes, "manager_provider", provider)
    monkeypatch.setattr(intake_routes, "search_provider", None)
    monkeypatch.setattr(intake_routes, "extract_provider", None)

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_free_text_manual_target_uses_manager_decision_and_existing_target_service(monkeypatch) -> None:
    debug_token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", debug_token)
    db = _session()
    provider = _ManualTargetManagerProvider(target_kcal=1600)
    client = _client(db, provider, monkeypatch)
    user_external_id = "free-text-target-user"

    response = client.post(
        "/estimate",
        json={"text": "今天目標 1600", "allow_search": False, "user_id": user_external_id},
    )

    assert response.status_code == 200
    payload = response.json()["payload"]
    assert response.json()["coach_message"] == "Daily target updated to 1600 kcal. Consumed 0 kcal today; remaining 1600 kcal."
    assert payload["manager_decision"]["intent_type"] == "set_manual_daily_target"
    assert payload["manager_decision"]["workflow_effect"] == "manual_daily_target_update"
    assert payload["manager_decision"]["semantic_decision"]["mutation_intent_candidate"] == "budget_target_write"
    assert payload["state_delta"]["manual_daily_target_updated"] is True
    assert payload["state_delta"]["manual_daily_target_kcal"] == 1600
    assert payload["state_delta"]["meal_logged"] is False
    assert payload["state_delta"]["canonical_commit"] is False
    assert payload["remaining_budget"]["daily_target_kcal"] == 1600
    assert payload["remaining_budget"]["remaining_kcal"] == 1600

    today = client.get("/today/current-budget", params={"user_id": user_external_id})
    assert today.status_code == 200
    debug = client.get(
        "/accurate-intake/debug",
        params={"user_id": user_external_id, "local_date": today.json()["local_date"]},
        headers={"X-Local-Debug-Token": debug_token},
    )

    assert today.json()["budget_kcal"] == 1600
    assert today.json()["consumed_kcal"] == 0
    assert debug.json()["model"]["meal_threads"] == []
    assert debug.json()["model"]["same_truth"]["status"] == "pass"
    assert any("body.get_active_plan" in call["available_tools"] for call in provider.calls)


def test_free_text_manual_target_blocks_unsafe_target_without_meal_mutation(monkeypatch) -> None:
    debug_token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", debug_token)
    db = _session()
    provider = _ManualTargetManagerProvider(target_kcal=300)
    client = _client(db, provider, monkeypatch)
    user_external_id = "unsafe-target-user"

    response = client.post(
        "/estimate",
        json={"text": "改成 300", "allow_search": False, "user_id": user_external_id},
    )

    assert response.status_code == 200
    payload = response.json()["payload"]
    assert "between 800 and 5000 kcal" in response.json()["coach_message"]
    assert payload["manager_decision"]["intent_type"] == "set_manual_daily_target"
    assert payload["state_delta"]["manual_daily_target_blocked"] is True
    assert payload["state_delta"]["meal_logged"] is False
    assert payload["state_delta"]["canonical_commit"] is False
    assert payload["remaining_budget"]["daily_target_kcal"] is None
    assert payload["remaining_budget"]["remaining_kcal"] is None

    debug = client.get(
        "/accurate-intake/debug",
        params={"user_id": user_external_id},
        headers={"X-Local-Debug-Token": debug_token},
    )
    assert debug.status_code == 200
    assert debug.json()["model"]["meal_threads"] == []


def test_free_text_manual_target_blocks_ambiguous_manager_target_without_raw_text_parsing(monkeypatch) -> None:
    db = _session()
    provider = _ManualTargetManagerProvider(target_kcal=None)
    client = _client(db, provider, monkeypatch)

    response = client.post(
        "/estimate",
        json={"text": "今天目標越低越好", "allow_search": False, "user_id": "ambiguous-target-user"},
    )

    assert response.status_code == 200
    payload = response.json()["payload"]
    assert payload["state_delta"]["manual_daily_target_blocked"] is True
    assert payload["state_delta"].get("manual_daily_target_updated") is not True
    assert payload["state_delta"]["meal_logged"] is False
    assert payload["state_delta"]["canonical_commit"] is False
