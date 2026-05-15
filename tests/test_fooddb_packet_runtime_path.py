from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.composition import intake_routes
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_db, get_or_create_user
from app.models import Base
from app.runtime.application import conversation_state_assembler
from app.shared.domain import PendingFollowupState
from app.routes import router
from scripts.run_accurate_intake_mvp_manager_style_smoke import (
    DeterministicSelfUseManagerProvider,
)


@pytest.fixture(autouse=True)
def _restore_conversation_summary_builders(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        conversation_state_assembler,
        "build_pending_followup_state",
        lambda *_, **__: PendingFollowupState(),
    )


def _route_session(db_path: Path) -> Session:
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


def _route_client(db: Session, monkeypatch) -> tuple[TestClient, DeterministicSelfUseManagerProvider]:
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


def test_route_commits_approved_generic_fooddb_packet_without_shadow_stub(monkeypatch, tmp_path: Path) -> None:
    db = _route_session(tmp_path / "fooddb-generic-runtime.sqlite3")
    user_external_id = "fooddb-generic-runtime"
    local_date = "2026-05-09"
    raw_input = "\u8336\u8449\u86cb"
    _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
    client, provider = _route_client(db, monkeypatch)

    try:
        estimate_response = client.post(
            "/estimate",
            json={
                "text": raw_input,
                "allow_search": False,
                "user_id": user_external_id,
                "local_date": local_date,
            },
        )
        assert estimate_response.status_code == 200
        route_payload = estimate_response.json()["payload"]

        assert route_payload["state_delta"]["canonical_commit"] is True
        assert route_payload["intake_execution_manager"]["final"]["final_action"] == "commit"

        macro = route_payload["sidecar"]["macro"]
        assert macro["display_status"] == "hide"
        assert macro["guard_reason"] == "no_macro_data"
        trace = macro["approved_fooddb_evidence_trace"]
        assert trace["source_lane"] == "generic_common_serving"
        assert trace["macro_visibility_status"] == "hidden_missing_source"
        assert trace["macro_truth_owner"] == "fooddb_approved_packet"
        assert trace["live_llm_invoked"] is False
        assert trace["websearch_evidence_used"] is False
        assert trace["fooddb_truth_updated"] is False

        evidence = route_payload["sidecar"]["evidence"]
        assert evidence["db_hit_type"] == "approved_fooddb_packet"
        assert evidence["generic_count"] == 1
        assert evidence["search_attempt_count"] == 0

        budget_response = client.get(
            "/today/current-budget",
            params={"user_id": user_external_id, "local_date": local_date},
        )
        assert budget_response.status_code == 200
        current_budget = budget_response.json()
        assert current_budget["consumed_kcal"] == 80
        assert current_budget["active_meal_count"] == 1
        assert current_budget["show_macro"] is False
        assert current_budget["macro_guard_reason"] == "no_macro_data"
        assert provider.readiness()["live_llm_invoked"] is False
    finally:
        client.close()
        db.close()


def test_route_blocks_bare_basket_fooddb_packet_from_canonical_commit(monkeypatch, tmp_path: Path) -> None:
    db = _route_session(tmp_path / "fooddb-bare-basket-runtime.sqlite3")
    user_external_id = "fooddb-bare-basket-runtime"
    local_date = "2026-05-09"
    raw_input = "\u6211\u5403\u6ef7\u5473"
    _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
    client, provider = _route_client(db, monkeypatch)

    try:
        estimate_response = client.post(
            "/estimate",
            json={
                "text": raw_input,
                "allow_search": False,
                "user_id": user_external_id,
                "local_date": local_date,
            },
        )
        assert estimate_response.status_code == 200
        route_payload = estimate_response.json()["payload"]

        assert route_payload["state_delta"].get("canonical_commit") is not True
        assert route_payload["intake_execution_manager"]["final"]["final_action"] == "no_commit"
        same_truth = route_payload["phase_c_trace"]["same_truth_read_result"]
        assert same_truth["phase_a_projected_commit_intent"] == "draft"

        macro = route_payload["sidecar"]["macro"]
        trace = macro["approved_fooddb_evidence_trace"]
        assert trace["source_lane"] == "basket_family_alias_modifier"
        assert trace["macro_visibility_status"] == "hidden_missing_source"
        assert trace["runtime_truth_allowed"] is False
        assert trace["fooddb_truth_updated"] is False

        budget_response = client.get(
            "/today/current-budget",
            params={"user_id": user_external_id, "local_date": local_date},
        )
        assert budget_response.status_code == 200
        current_budget = budget_response.json()
        assert current_budget["consumed_kcal"] == 0
        assert current_budget["active_meal_count"] == 0
        assert provider.readiness()["live_llm_invoked"] is False
    finally:
        client.close()
        db.close()


def test_route_blocks_raw_text_listed_basket_without_manager_owned_components(monkeypatch, tmp_path: Path) -> None:
    db = _route_session(tmp_path / "fooddb-partial-listed-runtime.sqlite3")
    user_external_id = "fooddb-partial-listed-runtime"
    local_date = "2026-05-09"
    raw_input = "\u6ef7\u5473\u6709\u8c46\u5e72\u3001\u4e0d\u5b58\u5728\u7684\u914d\u6599"
    _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
    client, provider = _route_client(db, monkeypatch)

    try:
        estimate_response = client.post(
            "/estimate",
            json={
                "text": raw_input,
                "allow_search": False,
                "user_id": user_external_id,
                "local_date": local_date,
            },
        )
        assert estimate_response.status_code == 200
        route_payload = estimate_response.json()["payload"]

        assert route_payload["state_delta"].get("canonical_commit") is not True
        assert route_payload["intake_execution_manager"]["final"]["final_action"] == "no_commit"
        same_truth = route_payload["phase_c_trace"]["same_truth_read_result"]
        assert same_truth["phase_a_projected_commit_intent"] == "draft"

        macro = route_payload["sidecar"]["macro"]
        trace = macro["approved_fooddb_evidence_trace"]
        assert trace["source_lane"] == "basket_family_alias_modifier"
        assert trace["retrieval_boundary"] == "bare_basket_ask_followup_no_estimate"
        assert trace["runtime_truth_allowed"] is False
        assert trace["fooddb_truth_updated"] is False

        budget_response = client.get(
            "/today/current-budget",
            params={"user_id": user_external_id, "local_date": local_date},
        )
        assert budget_response.status_code == 200
        current_budget = budget_response.json()
        assert current_budget["consumed_kcal"] == 0
        assert current_budget["active_meal_count"] == 0
        assert provider.readiness()["live_llm_invoked"] is False
    finally:
        client.close()
        db.close()


def test_route_blocks_ambiguous_fooddb_packet_from_canonical_commit(monkeypatch, tmp_path: Path) -> None:
    db = _route_session(tmp_path / "fooddb-ambiguous-runtime.sqlite3")
    user_external_id = "fooddb-ambiguous-runtime"
    local_date = "2026-05-09"
    raw_input = "boba milk teaa"
    _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
    client, provider = _route_client(db, monkeypatch)

    try:
        estimate_response = client.post(
            "/estimate",
            json={
                "text": raw_input,
                "allow_search": False,
                "user_id": user_external_id,
                "local_date": local_date,
            },
        )
        assert estimate_response.status_code == 200
        route_payload = estimate_response.json()["payload"]

        assert route_payload["state_delta"].get("canonical_commit") is not True
        assert route_payload["intake_execution_manager"]["final"]["final_action"] == "no_commit"

        macro = route_payload["sidecar"]["macro"]
        trace = macro["approved_fooddb_evidence_trace"]
        assert trace["runtime_truth_allowed"] is False
        assert trace["fooddb_truth_updated"] is False
        assert trace["disambiguation_required"] is True

        budget_response = client.get(
            "/today/current-budget",
            params={"user_id": user_external_id, "local_date": local_date},
        )
        assert budget_response.status_code == 200
        current_budget = budget_response.json()
        assert current_budget["consumed_kcal"] == 0
        assert current_budget["active_meal_count"] == 0
        assert provider.readiness()["live_llm_invoked"] is False
    finally:
        client.close()
        db.close()
