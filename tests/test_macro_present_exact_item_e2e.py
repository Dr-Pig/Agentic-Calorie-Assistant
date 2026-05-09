from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.composition.accurate_intake_today_macro_mirror_gate import (
    build_today_macro_runtime_mirror_gate_artifact,
)
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.current_budget_read_model import build_current_budget_view
from app.composition import intake_routes
from app.composition.intake_estimation_tools import estimate_nutrition_tool
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_db
from app.database import get_or_create_user
from app.models import Base
from app.nutrition.agent.exact_item_packets import build_exact_item_lane_packet
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts
from app.routes import router
from scripts.run_accurate_intake_mvp_manager_style_smoke import DeterministicSelfUseManagerProvider


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


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


def _manager_gate_ledger() -> dict[str, object]:
    return yaml.safe_load(Path("docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml").read_text(encoding="utf-8"))


def test_macro_present_exact_item_flows_from_fooddb_seed_to_today_render() -> None:
    db = _session()
    user = get_or_create_user(db, "macro-present-exact-item-e2e")
    raw_input = "\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73(400ml)"

    exact_candidates = resolve_exact_item_fts(raw_input, limit=1)
    assert exact_candidates
    assert exact_candidates[0]["title"] == raw_input
    assert exact_candidates[0]["label_kcal"] == 300
    assert exact_candidates[0]["label_macros"] == {"protein_g": 12.0, "carb_g": 48.0, "fat_g": 6.0}

    exact_packet = build_exact_item_lane_packet(raw_input, limit=1)
    top_candidate = exact_packet["top_exact_candidate"]
    assert top_candidate["macro_completeness"] == "complete"
    assert top_candidate["protein_g"] == 12.0
    assert top_candidate["carb_g"] == 48.0
    assert top_candidate["fat_g"] == 6.0

    artifact = asyncio.run(
        estimate_nutrition_tool(
            db,
            user_external_id=user.user_id,
            raw_user_input=raw_input,
            request_id="req-macro-present-exact-item",
            local_date="2026-05-09",
            allow_search=False,
        )
    )
    payload = artifact.payload

    assert payload.best_estimate_mode == "exact_item"
    assert payload.trace_contract["db_hit_type"] == "exact_truth"
    assert payload.trace_contract["macro_display_authorized"] is True
    assert payload.display_macro_breakdown == {
        "protein_g": 12,
        "carb_g": 48,
        "fat_g": 6,
        "macro_source": "exact_item_db",
        "macro_confidence": "high",
        "macro_status": "available",
    }

    commit_meal_payload_to_canonical(
        db,
        user=user,
        payload=payload,
        raw_input=raw_input,
        manager_intent="food_estimation",
        request_id=payload.request_id,
        budget_kcal=1200,
    )

    current_budget = build_current_budget_view(db, user_id=user.id, local_date="2026-05-09")
    assert current_budget.consumed_kcal == 300
    assert current_budget.consumed_protein == 12
    assert current_budget.consumed_carbs == 48
    assert current_budget.consumed_fat == 6
    assert current_budget.show_macro is True
    assert current_budget.macro_guard_reason == "committed_and_aligned"

    today_gate = build_today_macro_runtime_mirror_gate_artifact(
        manager_gate_ledger_artifact=_manager_gate_ledger(),
        current_budget_payload=current_budget.model_dump(mode="json"),
    )
    assert today_gate["status"] == "today_macro_runtime_mirror_gate_ready_for_browser"
    assert today_gate["truth_owner"] == "CurrentBudgetView.macro_visibility"
    assert today_gate["frontend_calculates_macro_values"] is False
    assert today_gate["runtime_case"]["macro_state"] == "visible"
    assert today_gate["runtime_case"]["protein_text"] == "12"
    assert today_gate["runtime_case"]["carbs_text"] == "48"
    assert today_gate["runtime_case"]["fat_text"] == "6"


def test_estimate_route_traces_approved_exact_macro_packet_into_current_budget(monkeypatch, tmp_path: Path) -> None:
    db = _route_session(tmp_path / "macro-route.sqlite3")
    user_external_id = "macro-present-exact-item-route"
    local_date = "2026-05-09"
    raw_input = "\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73(400ml)"
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
        assert macro["protein_g"] == 12
        assert macro["carbs_g"] == 48
        assert macro["fat_g"] == 6
        assert macro["display_status"] == "show"
        assert macro["guard_reason"] == "committed_and_aligned"
        assert macro["macro_kcal"] == 294
        assert macro["macro_kcal_delta"] == 6
        assert macro["alignment_warning"] is False
        assert route_payload["sidecar"]["evidence"]["db_hit_type"] == "exact_truth"
        assert route_payload["sidecar"]["evidence"]["exact_count"] == 1

        exact_trace = macro["approved_exact_macro_trace"]
        assert exact_trace["source_lane"] == "exact_item_card"
        assert exact_trace["runtime_role"] == "exact_item_card"
        assert exact_trace["runtime_truth_allowed"] is True
        assert exact_trace["source_quality"] == "packet_ready_approved"
        assert exact_trace["approved_packet_schema_version"] == "fooddb_approved_packet_ready_artifact_v1"
        assert exact_trace["item_id"] == "exact_unified_chocolate_milk_400ml"
        assert exact_trace["macro_truth_owner"] == "fooddb_approved_packet"
        assert exact_trace["missing_macro_policy"] == "preserve_null_do_not_invent"
        assert exact_trace["packet_fields"] == [
            "protein_g",
            "carbs_g",
            "fat_g",
            "macro_visibility_status",
            "macro_source_basis",
            "macro_confidence",
        ]
        assert exact_trace["macro_visibility_status"] == "visible"
        assert exact_trace["macro_source_basis"] == "exact_item_seed_label"
        assert exact_trace["macro_confidence"] == "high"
        assert exact_trace["live_llm_invoked"] is False
        assert exact_trace["websearch_evidence_used"] is False
        assert exact_trace["fooddb_truth_updated"] is False

        budget_response = client.get(
            "/today/current-budget",
            params={"user_id": user_external_id, "local_date": local_date},
        )
        assert budget_response.status_code == 200
        current_budget = budget_response.json()
        assert current_budget["consumed_kcal"] == 300
        assert current_budget["consumed_protein"] == 12
        assert current_budget["consumed_carbs"] == 48
        assert current_budget["consumed_fat"] == 6
        assert current_budget["show_macro"] is True
        assert current_budget["macro_guard_reason"] == "committed_and_aligned"
        assert provider.readiness()["live_llm_invoked"] is False
    finally:
        client.close()
        db.close()


def test_estimate_route_preserves_missing_exact_macro_as_hidden_unknown(monkeypatch, tmp_path: Path) -> None:
    db = _route_session(tmp_path / "macro-missing-route.sqlite3")
    user_external_id = "macro-missing-exact-item-route"
    local_date = "2026-05-09"
    raw_input = "\u722d\u9bae \u7126\u7cd6\u9bae\u9b5a(\u5169\u8cab)"
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
        assert macro["protein_g"] == 0
        assert macro["carbs_g"] == 0
        assert macro["fat_g"] == 0
        assert macro["display_status"] == "hide"
        assert macro["guard_reason"] == "no_macro_data"
        assert macro["macro_kcal_delta"] == 0
        assert route_payload["sidecar"]["evidence"]["db_hit_type"] == "exact_truth"
        assert route_payload["sidecar"]["evidence"]["exact_count"] == 1

        exact_trace = macro["approved_exact_macro_trace"]
        assert exact_trace["source_lane"] == "exact_item_card"
        assert exact_trace["runtime_truth_allowed"] is True
        assert exact_trace["item_id"] == "exact_sushiro_caramel_fish_two_piece"
        assert exact_trace["macro_truth_owner"] == "fooddb_approved_packet"
        assert exact_trace["missing_macro_policy"] == "preserve_null_do_not_invent"
        assert exact_trace["macro_visibility_status"] == "hidden_missing_source"
        assert exact_trace["macro_source_basis"] == "unavailable"
        assert exact_trace["macro_confidence"] == "unknown"
        assert exact_trace["live_llm_invoked"] is False
        assert exact_trace["websearch_evidence_used"] is False
        assert exact_trace["fooddb_truth_updated"] is False

        budget_response = client.get(
            "/today/current-budget",
            params={"user_id": user_external_id, "local_date": local_date},
        )
        assert budget_response.status_code == 200
        current_budget = budget_response.json()
        assert current_budget["consumed_kcal"] == 130
        assert current_budget["consumed_protein"] == 0
        assert current_budget["consumed_carbs"] == 0
        assert current_budget["consumed_fat"] == 0
        assert current_budget["show_macro"] is False
        assert current_budget["macro_guard_reason"] == "no_macro_data"
        assert provider.readiness()["live_llm_invoked"] is False
    finally:
        client.close()
        db.close()
