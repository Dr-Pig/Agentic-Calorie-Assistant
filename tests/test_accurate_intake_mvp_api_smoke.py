from __future__ import annotations

import secrets
from threading import Event, Thread

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.composition import intake_chat_turn_routes, intake_routes
from app.composition.inflight_chat_turn import PENDING_ASSISTANT_MESSAGE
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_db, get_or_create_user
from app.models import Base
from app.routes import router
from scripts.run_accurate_intake_mvp_manager_style_smoke import DeterministicSelfUseManagerProvider


def _session(db_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _seed_body_plan(db: Session, *, user_external_id: str, local_date: str) -> None:
    user = get_or_create_user(db, user_external_id)
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=34,
            height_cm=170,
            current_weight_kg=70,
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            timezone="Asia/Taipei",
            daily_lifestyle="sedentary_with_some_walking",
            weekly_exercise_days_band="1_2",
            local_date=local_date,
        ),
    )


def _client(db: Session, monkeypatch) -> tuple[TestClient, DeterministicSelfUseManagerProvider]:
    provider = DeterministicSelfUseManagerProvider()
    monkeypatch.setattr(intake_routes, "manager_provider", provider)
    monkeypatch.setattr(intake_routes, "search_provider", None)
    monkeypatch.setattr(intake_routes, "extract_provider", None)

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), provider


class _BlockingSelfUseManagerProvider(DeterministicSelfUseManagerProvider):
    def __init__(self) -> None:
        super().__init__()
        self.started = Event()
        self.release = Event()
        self._blocked_once = False

    async def complete_with_trace(self, **kwargs):
        if not self._blocked_once:
            self._blocked_once = True
            self.started.set()
            if not self.release.wait(timeout=10):
                raise TimeoutError("blocking provider was not released")
        return await super().complete_with_trace(**kwargs)


def _threaded_client(db_path: Path, monkeypatch) -> tuple[TestClient, _BlockingSelfUseManagerProvider]:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    seed_session = testing_session()
    try:
        _seed_body_plan(seed_session, user_external_id="api-inflight-user", local_date="2026-05-02")
    finally:
        seed_session.close()
    provider = _BlockingSelfUseManagerProvider()
    monkeypatch.setattr(intake_routes, "manager_provider", provider)
    monkeypatch.setattr(intake_routes, "search_provider", None)
    monkeypatch.setattr(intake_routes, "extract_provider", None)

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), provider


def test_estimate_route_closes_manager_style_product_loop_against_debug_surface(monkeypatch, tmp_path: Path) -> None:
    debug_token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", debug_token)
    db = _session(tmp_path / "api-smoke.sqlite3")
    user_external_id = "api-smoke-user"
    local_date = "2026-05-02"
    _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
    client, provider = _client(db, monkeypatch)

    try:
        initial_response = client.post(
            "/estimate",
            json={"text": "chicken sandwich", "allow_search": False, "user_id": user_external_id},
        )
        assert initial_response.status_code == 200
        initial_payload = initial_response.json()["payload"]
        assert initial_payload["state_delta"]["canonical_commit"] is True
        assert initial_payload["intake_execution_manager"]["final"]["final_action"] == "commit"
        route_local_date = initial_payload["remaining_budget"]["local_date"]

        correction_response = client.post(
            "/estimate",
            json={"text": "the chicken sandwich was smaller", "allow_search": False, "user_id": user_external_id},
        )
        assert correction_response.status_code == 200
        correction_payload = correction_response.json()["payload"]
        assert correction_payload["state_delta"]["canonical_commit"] is True
        assert correction_payload["state_delta"]["old_version_superseded"] is True
        assert correction_payload["intake_execution_manager"]["final"]["final_action"] == "correction_applied"

        query_response = client.post(
            "/estimate",
            json={"text": "how much have I eaten today", "allow_search": False, "user_id": user_external_id},
        )
        assert query_response.status_code == 200
        query_payload = query_response.json()["payload"]
        assert query_payload["state_delta"]["canonical_commit"] is False
        assert query_payload["manager_decision"]["intent_type"] == "answer_remaining_budget"

        debug_response = client.get(
            "/accurate-intake/debug",
            params={"user_id": user_external_id, "local_date": route_local_date},
            headers={"X-Local-Debug-Token": debug_token},
        )
        assert debug_response.status_code == 200
        debug_payload = debug_response.json()
        model = debug_payload["model"]
        assert debug_payload["read_only"] is True
        assert model["today_summary"]["consumed_kcal"] > 0
        assert model["same_truth"]["status"] == "pass"
        assert provider.readiness()["live_llm_invoked"] is False
        assert any(
            "estimate_nutrition" in call["available_tools"]
            for call in provider.calls
        )
    finally:
        client.close()
        db.close()


def test_estimate_route_persists_inflight_chat_turn_before_provider_returns(monkeypatch, tmp_path: Path) -> None:
    debug_token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", debug_token)
    client, provider = _threaded_client(tmp_path / "inflight.sqlite3", monkeypatch)
    result: dict[str, object] = {}
    debug_headers = {"X-Local-Debug-Token": debug_token}

    def post_estimate() -> None:
        result["response"] = client.post(
            "/estimate",
            json={
                "text": "早餐吃早餐店鐵板麵套餐",
                "allow_search": False,
                "user_id": "api-inflight-user",
                "local_date": "2026-05-02",
            },
        )

    thread = Thread(target=post_estimate)
    thread.start()
    try:
        assert provider.started.wait(timeout=5)
        pending_response = client.get(
            "/accurate-intake/chat-history",
            params={"user_id": "api-inflight-user", "local_date": "2026-05-02"},
            headers=debug_headers,
        )
        assert pending_response.status_code == 200
        pending_messages = pending_response.json()["messages"]
        assert [(message["role"], message["content"]) for message in pending_messages] == [
            ("user", "早餐吃早餐店鐵板麵套餐"),
            ("assistant", "處理中..."),
        ]
        assert pending_messages[0]["trace_id"] == pending_messages[1]["trace_id"]
        assert pending_messages[1]["runtime_turn_trace_present"] is True
    finally:
        provider.release.set()
        thread.join(timeout=10)

    response = result.get("response")
    assert response is not None
    assert response.status_code == 200
    final_response = client.get(
        "/accurate-intake/chat-history",
        params={"user_id": "api-inflight-user", "local_date": "2026-05-02"},
        headers=debug_headers,
    )
    assert final_response.status_code == 200
    final_messages = final_response.json()["messages"]
    assert len(final_messages) == 2
    assert final_messages[0]["content"] == "早餐吃早餐店鐵板麵套餐"
    assert final_messages[1]["content"] != "處理中..."
    assert final_messages[0]["trace_id"] == final_messages[1]["trace_id"]
    client.close()


def test_async_chat_turn_accepts_and_persists_inflight_before_background_work(
    monkeypatch,
    tmp_path: Path,
) -> None:
    debug_token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", debug_token)
    db = _session(tmp_path / "async-chat-turn.sqlite3")
    user_external_id = "api-async-chat-user"
    local_date = "2026-05-02"
    _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
    client, _provider = _client(db, monkeypatch)

    async def noop_background(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(intake_chat_turn_routes, "_complete_chat_turn_background", noop_background)

    try:
        response = client.post(
            "/accurate-intake/chat-turn",
            json={
                "text": "早餐吃鐵板麵套餐",
                "allow_search": False,
                "user_id": user_external_id,
                "local_date": local_date,
            },
        )

        assert response.status_code == 202
        accepted = response.json()
        assert accepted["status"] == "accepted"
        assert accepted["coach_message"] == PENDING_ASSISTANT_MESSAGE
        assert accepted["request_id"]
        assert accepted["trace_id"] == accepted["request_id"]

        history = client.get(
            "/accurate-intake/chat-history",
            params={"user_id": user_external_id, "local_date": local_date},
            headers={"X-Local-Debug-Token": debug_token},
        )
        assert history.status_code == 200
        messages = history.json()["messages"]
        assert [(message["role"], message["content"]) for message in messages] == [
            ("user", "早餐吃鐵板麵套餐"),
            ("assistant", PENDING_ASSISTANT_MESSAGE),
        ]
        assert messages[0]["trace_id"] == accepted["request_id"]
        assert messages[1]["trace_id"] == accepted["request_id"]
        assert messages[1]["runtime_turn_status"] == "in_progress"
    finally:
        client.close()
        db.close()
