from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.body.infrastructure.models import BodyObservationRecord, BodyPlanRecord, BodyProfileRecord
from app.budget.infrastructure.models import DayBudgetLedgerRecord
from app.composition.calibration_routes import router as calibration_router
from app.database import get_db, get_or_create_user
from app.intake.infrastructure.models import MealThreadRecord, MealVersionRecord
from app.models import Base
from app.shared.infra.models import ProposalContainerRecord, ProposalOptionRecord, User


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _client(db: Session) -> TestClient:
    app = FastAPI()
    app.include_router(calibration_router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _active_body_plan(
    db: Session,
    *,
    user_id: int,
    estimated_tdee: int = 2100,
    daily_budget_kcal: int = 1800,
) -> BodyPlanRecord:
    plan = BodyPlanRecord(
        user_id=user_id,
        plan_status="active",
        plan_label="route baseline",
        estimated_tdee=estimated_tdee,
        daily_budget_kcal=daily_budget_kcal,
        safety_floor_kcal=1200,
        target_pace_kg_per_week=0.5,
        metadata_json={"recommended_target_kcal": daily_budget_kcal, "plan_source": "test_baseline"},
        started_at=datetime(2026, 5, 1, 8, 0, 0),
        created_at=datetime(2026, 5, 1, 8, 0, 0),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _active_profile(db: Session, *, user_id: int, timezone: str = "Asia/Taipei") -> BodyProfileRecord:
    profile = BodyProfileRecord(
        user_id=user_id,
        profile_status="active",
        sex="female",
        age_years=31,
        height_cm=165.0,
        current_weight_kg=70.0,
        activity_level="light",
        goal_type="lose_weight",
        timezone=timezone,
        created_at=datetime(2026, 5, 1, 8, 0, 0),
        updated_at=datetime(2026, 5, 1, 8, 0, 0),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _weight(db: Session, *, user_id: int, local_date: str, value: float) -> BodyObservationRecord:
    observed_date = datetime.fromisoformat(local_date)
    observation = BodyObservationRecord(
        user_id=user_id,
        observation_type="weight",
        value=value,
        unit="kg",
        observed_at=observed_date.replace(hour=7),
        local_date=local_date,
        source="manual",
        metadata_json={},
        created_at=observed_date.replace(hour=7, minute=5),
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


def _meal(db: Session, *, user_id: int, local_date: str, kcal: int = 1800) -> MealVersionRecord:
    thread = MealThreadRecord(
        user_id=user_id,
        title=f"meal {local_date}",
        thread_kind="text_intake",
        created_at=datetime.fromisoformat(local_date).replace(hour=12),
        updated_at=datetime.fromisoformat(local_date).replace(hour=12),
    )
    db.add(thread)
    db.flush()
    version = MealVersionRecord(
        meal_thread_id=thread.id,
        version_status="active",
        version_reason="new_intake",
        meal_title=f"meal {local_date}",
        raw_input="test meal",
        resolution_status="completed_meal",
        total_kcal=kcal,
        protein_g=0,
        carb_g=0,
        fat_g=0,
        occurred_at=datetime.fromisoformat(local_date).replace(hour=12),
        local_date=local_date,
        created_at=datetime.fromisoformat(local_date).replace(hour=13),
    )
    db.add(version)
    db.flush()
    thread.active_version_id = version.id
    db.commit()
    db.refresh(version)
    return version


def _calibration_effect_payload(*, budget: int = 2000) -> dict[str, object]:
    return {
        "new_daily_budget_kcal": budget,
        "new_estimated_tdee_kcal": 2100,
        "review_after_days": 14,
        "rationale_summary": "route test calibration effect",
    }


def test_calibration_preview_route_preserves_existing_fields_and_adds_diagnostic_packet() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-preview-route")
    _active_body_plan(db, user_id=user.id)

    response = client.post(
        "/calibration/proposal/preview",
        json={
            "user_id": "calibration-preview-route",
            "local_date": "2026-05-04",
            "current_budget_status": "over_budget",
            "rescue_recovery_viability": "non_viable",
            "model_inputs": {
                "body_plan_estimated_tdee_kcal": 2100,
                "observation_window_days": 21,
                "body_observation_count": 9,
                "intake_coverage": 0.93,
                "operating_expenditure_shift_kcal": 340,
                "trend_mismatch_consistency": 0.9,
                "trend_volatility": 0.1,
                "logging_gap_ratio": 0.05,
                "late_logged_meal_ratio": 0.05,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert {"calibration_result", "gate_result", "response"} <= set(payload)
    assert {"diagnostic", "proposal_policy_packet", "trace_envelope"} <= set(payload)
    assert payload["calibration_result"]["calibration_posture"] == "high_confidence_mismatch"
    assert payload["gate_result"]["proposal_eligibility"] is True
    assert payload["response"]["proposal_family"] == "budget_adjustment"
    assert payload["proposal_policy_packet"]["proposal_family"] == "budget_adjustment"
    assert payload["proposal_policy_packet"]["plan_change_required"] is True
    assert payload["proposal_policy_packet"]["plan_mutation_authorized"] is False
    assert payload["proposal_policy_packet"]["ledger_mutation_authorized"] is False
    assert payload["trace_envelope"]["automatic_calibration_enabled"] is False
    assert payload["trace_envelope"]["live_tool_calling"] is False
    assert payload["diagnostic"]["proposal_policy_packet"] == payload["proposal_policy_packet"]
    assert payload["diagnostic"]["trace_envelope"] == payload["trace_envelope"]
    assert db.execute(select(ProposalContainerRecord)).scalars().all() == []
    assert db.execute(select(DayBudgetLedgerRecord)).scalars().all() == []


def test_calibration_preview_can_persist_open_proposal_artifact_without_plan_mutation() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-persist-preview")
    baseline_plan = _active_body_plan(db, user_id=user.id)

    response = client.post(
        "/calibration/proposal/preview",
        json={
            "user_id": "calibration-persist-preview",
            "local_date": "2026-05-04",
            "current_budget_status": "over_budget",
            "rescue_recovery_viability": "non_viable",
            "persist_proposal": True,
            "model_inputs": {
                "body_plan_estimated_tdee_kcal": 2100,
                "observation_window_days": 21,
                "body_observation_count": 9,
                "intake_coverage": 0.93,
                "operating_expenditure_shift_kcal": 340,
                "trend_mismatch_consistency": 0.9,
                "trend_volatility": 0.1,
                "logging_gap_ratio": 0.05,
                "late_logged_meal_ratio": 0.05,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    proposal_id = payload["proposal_artifact"]["proposal_container_id"]
    proposal = db.get(ProposalContainerRecord, proposal_id)
    assert proposal is not None
    assert proposal.proposal_type == "calibration"
    assert proposal.proposal_status == "open"
    assert proposal.metadata_json["local_date"] == "2026-05-04"
    assert proposal.metadata_json["proposal_policy_packet"]["plan_mutation_authorized"] is False

    options = db.execute(
        select(ProposalOptionRecord).where(ProposalOptionRecord.proposal_container_id == proposal_id)
    ).scalars().all()
    assert len(options) >= 1
    assert proposal.top_option_id == options[0].id
    assert options[0].option_type == "budget_adjustment"
    assert options[0].effect_payload_json["new_daily_budget_kcal"] == 2000

    active_plan = db.execute(select(BodyPlanRecord).where(BodyPlanRecord.plan_status == "active")).scalar_one()
    assert active_plan.id == baseline_plan.id
    assert active_plan.daily_budget_kcal == 1800
    assert db.execute(select(DayBudgetLedgerRecord)).scalars().all() == []


def test_calibration_preview_from_history_assembles_inputs_and_does_not_mutate_plan_or_ledger() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-preview-from-history")
    baseline_plan = _active_body_plan(db, user_id=user.id)
    _active_profile(db, user_id=user.id)
    for offset in range(14):
        _meal(db, user_id=user.id, local_date=(datetime(2026, 5, 1) + timedelta(days=offset)).date().isoformat())
    for local_date, value in [
        ("2026-05-01", 70.0),
        ("2026-05-04", 69.7),
        ("2026-05-07", 69.4),
        ("2026-05-10", 69.1),
        ("2026-05-14", 68.8),
    ]:
        _weight(db, user_id=user.id, local_date=local_date, value=value)

    response = client.post(
        "/calibration/proposal/preview-from-history",
        json={
            "user_id": "calibration-preview-from-history",
            "local_date": "2026-05-14",
            "current_budget_status": "over_budget",
            "rescue_recovery_viability": "non_viable",
            "persist_proposal": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["calibration_result"]["calibration_posture"] == "high_confidence_mismatch"
    assert payload["input_assembly"]["model_inputs"]["operating_expenditure_shift_kcal"] == 411
    assert payload["input_assembly"]["trace"]["window_start_date"] == "2026-05-01"
    assert payload["input_assembly"]["trace"]["window_end_date"] == "2026-05-14"
    assert payload["input_assembly"]["trace"]["intake_coverage_confidence"] == "weak_proxy"
    assert payload["proposal_artifact"]["proposal_container_id"] is not None

    active_plan = db.execute(select(BodyPlanRecord).where(BodyPlanRecord.plan_status == "active")).scalar_one()
    assert active_plan.id == baseline_plan.id
    assert active_plan.daily_budget_kcal == 1800
    assert db.execute(select(DayBudgetLedgerRecord)).scalars().all() == []


def test_calibration_preview_from_history_reports_request_validation_separately_from_state_conflict() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-preview-from-history-errors")

    invalid_window = client.post(
        "/calibration/proposal/preview-from-history",
        json={
            "user_id": "calibration-preview-from-history-errors",
            "local_date": "2026-05-14",
            "window_days": 0,
        },
    )
    missing_plan = client.post(
        "/calibration/proposal/preview-from-history",
        json={
            "user_id": "calibration-preview-from-history-errors",
            "local_date": "2026-05-14",
        },
    )

    assert user.id is not None
    assert invalid_window.status_code == 422
    assert missing_plan.status_code == 409
    assert missing_plan.json()["detail"] == "active_body_plan_required_for_calibration_input_assembly"


def test_calibration_preview_from_history_uses_latest_active_plan_and_profile_when_duplicates_exist() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-preview-from-history-duplicate-active")
    _active_body_plan(db, user_id=user.id, estimated_tdee=2000, daily_budget_kcal=1700)
    _active_body_plan(db, user_id=user.id, estimated_tdee=2100, daily_budget_kcal=1800)
    _active_profile(db, user_id=user.id, timezone="UTC")
    _active_profile(db, user_id=user.id, timezone="Asia/Taipei")
    for offset in range(14):
        _meal(db, user_id=user.id, local_date=(datetime(2026, 5, 1) + timedelta(days=offset)).date().isoformat())
    for local_date, value in [
        ("2026-05-01", 70.0),
        ("2026-05-04", 69.7),
        ("2026-05-07", 69.4),
        ("2026-05-10", 69.1),
        ("2026-05-14", 68.8),
    ]:
        _weight(db, user_id=user.id, local_date=local_date, value=value)

    response = client.post(
        "/calibration/proposal/preview-from-history",
        json={
            "user_id": "calibration-preview-from-history-duplicate-active",
            "local_date": "2026-05-14",
            "current_budget_status": "over_budget",
            "rescue_recovery_viability": "non_viable",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["input_assembly"]["model_inputs"]["body_plan_estimated_tdee_kcal"] == 2100
    assert payload["input_assembly"]["trace"]["timezone"] == "Asia/Taipei"
    assert payload["response"]["ui_hints"]["active_daily_budget_kcal"] == 1800


def test_stored_calibration_accept_uses_persisted_option_and_updates_same_proposal() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-stored-accept")
    baseline_plan = _active_body_plan(db, user_id=user.id)
    preview = client.post(
        "/calibration/proposal/preview",
        json={
            "user_id": "calibration-stored-accept",
            "local_date": "2026-05-04",
            "current_budget_status": "over_budget",
            "rescue_recovery_viability": "non_viable",
            "persist_proposal": True,
            "model_inputs": {
                "body_plan_estimated_tdee_kcal": 2100,
                "observation_window_days": 21,
                "body_observation_count": 9,
                "intake_coverage": 0.93,
                "operating_expenditure_shift_kcal": 340,
                "trend_mismatch_consistency": 0.9,
                "trend_volatility": 0.1,
                "logging_gap_ratio": 0.05,
                "late_logged_meal_ratio": 0.05,
            },
        },
    )
    proposal_id = preview.json()["proposal_artifact"]["proposal_container_id"]

    response = client.post(
        "/calibration/proposal/stored-action",
        json={
            "user_id": "calibration-stored-accept",
            "proposal_container_id": proposal_id,
            "action": "accept_calibration_proposal",
            "accepted_at": "2026-05-04T10:30:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["proposal_container_id"] == proposal_id
    assert payload["proposal_status"] == "accepted"
    assert payload["effective_from"] == "2026-05-04"
    assert payload["state_delta"] == {
        "proposal_status": "accepted",
        "body_plan_id": payload["body_plan_id"],
        "effective_from": "2026-05-04",
        "plan_mutated": True,
        "ledger_mutated": True,
    }
    assert payload["current_budget_view"]["budget_kcal"] == 2000
    assert payload["active_body_plan_view"]["daily_budget_kcal"] == 2000

    proposals = db.execute(select(ProposalContainerRecord)).scalars().all()
    plans = db.execute(select(BodyPlanRecord).order_by(BodyPlanRecord.id.asc())).scalars().all()
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
    assert len(proposals) == 1
    assert proposals[0].id == proposal_id
    assert proposals[0].proposal_status == "accepted"
    assert len(plans) == 2
    assert plans[0].id == baseline_plan.id
    assert plans[0].plan_status == "superseded"
    assert plans[1].plan_status == "active"
    assert plans[1].daily_budget_kcal == 2000
    assert ledger.budget_kcal == 2000


@pytest.mark.parametrize(
    ("action", "expected_status"),
    [
        ("reject_calibration_proposal", "rejected"),
        ("defer_calibration_proposal", "dismissed"),
    ],
)
def test_stored_calibration_reject_or_defer_returns_no_mutation_state_delta(
    action: str,
    expected_status: str,
) -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, f"calibration-stored-{expected_status}")
    baseline_plan = _active_body_plan(db, user_id=user.id)
    preview = client.post(
        "/calibration/proposal/preview",
        json={
            "user_id": user.user_id,
            "local_date": "2026-05-04",
            "current_budget_status": "over_budget",
            "rescue_recovery_viability": "non_viable",
            "persist_proposal": True,
            "model_inputs": {
                "body_plan_estimated_tdee_kcal": 2100,
                "observation_window_days": 21,
                "body_observation_count": 9,
                "intake_coverage": 0.93,
                "operating_expenditure_shift_kcal": 340,
                "trend_mismatch_consistency": 0.9,
                "trend_volatility": 0.1,
                "logging_gap_ratio": 0.05,
                "late_logged_meal_ratio": 0.05,
            },
        },
    )
    proposal_id = preview.json()["proposal_artifact"]["proposal_container_id"]

    response = client.post(
        "/calibration/proposal/stored-action",
        json={
            "user_id": user.user_id,
            "proposal_container_id": proposal_id,
            "action": action,
            "accepted_at": "2026-05-04T10:30:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["proposal_container_id"] == proposal_id
    assert payload["proposal_status"] == expected_status
    assert payload["body_plan_id"] is None
    assert payload["state_delta"] == {
        "proposal_status": expected_status,
        "body_plan_id": None,
        "effective_from": "2026-05-04",
        "plan_mutated": False,
        "ledger_mutated": False,
    }
    proposal = db.get(ProposalContainerRecord, proposal_id)
    assert proposal is not None
    assert proposal.proposal_status == expected_status
    assert proposal.accepted_at is None
    active_plan = db.execute(select(BodyPlanRecord).where(BodyPlanRecord.plan_status == "active")).scalar_one()
    assert active_plan.id == baseline_plan.id
    assert active_plan.daily_budget_kcal == 1800
    assert db.execute(select(DayBudgetLedgerRecord)).scalars().all() == []


@pytest.mark.parametrize("invalid_accepted_at", ["not-a-date", "2026-05-04"])
def test_calibration_action_rejects_invalid_accepted_at_without_mutation(invalid_accepted_at: str) -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, f"calibration-action-invalid-accepted-at-{invalid_accepted_at}")
    baseline_plan = _active_body_plan(db, user_id=user.id)

    response = client.post(
        "/calibration/proposal/action",
        json={
            "user_id": user.user_id,
            "local_date": "2026-05-04",
            "proposal_family": "budget_adjustment",
            "effect_payload": _calibration_effect_payload(),
            "action": "accept_calibration_proposal",
            "accepted_at": invalid_accepted_at,
        },
    )

    assert response.status_code == 422
    active_plan = db.execute(select(BodyPlanRecord).where(BodyPlanRecord.plan_status == "active")).scalar_one()
    assert active_plan.id == baseline_plan.id
    assert active_plan.daily_budget_kcal == 1800
    assert db.execute(select(ProposalContainerRecord)).scalars().all() == []
    assert db.execute(select(DayBudgetLedgerRecord)).scalars().all() == []


@pytest.mark.parametrize("invalid_accepted_at", ["not-a-date", "2026-05-04"])
def test_stored_calibration_action_rejects_invalid_accepted_at_without_mutation(invalid_accepted_at: str) -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, f"stored-calibration-action-invalid-accepted-at-{invalid_accepted_at}")
    baseline_plan = _active_body_plan(db, user_id=user.id)
    preview = client.post(
        "/calibration/proposal/preview",
        json={
            "user_id": user.user_id,
            "local_date": "2026-05-04",
            "current_budget_status": "over_budget",
            "rescue_recovery_viability": "non_viable",
            "persist_proposal": True,
            "model_inputs": {
                "body_plan_estimated_tdee_kcal": 2100,
                "observation_window_days": 21,
                "body_observation_count": 9,
                "intake_coverage": 0.93,
                "operating_expenditure_shift_kcal": 340,
                "trend_mismatch_consistency": 0.9,
                "trend_volatility": 0.1,
                "logging_gap_ratio": 0.05,
                "late_logged_meal_ratio": 0.05,
            },
        },
    )
    proposal_id = preview.json()["proposal_artifact"]["proposal_container_id"]

    response = client.post(
        "/calibration/proposal/stored-action",
        json={
            "user_id": user.user_id,
            "proposal_container_id": proposal_id,
            "action": "accept_calibration_proposal",
            "accepted_at": invalid_accepted_at,
        },
    )

    assert response.status_code == 422
    proposal = db.get(ProposalContainerRecord, proposal_id)
    assert proposal is not None
    assert proposal.proposal_status == "open"
    assert proposal.accepted_at is None
    active_plan = db.execute(select(BodyPlanRecord).where(BodyPlanRecord.plan_status == "active")).scalar_one()
    assert active_plan.id == baseline_plan.id
    assert active_plan.daily_budget_kcal == 1800
    assert db.execute(select(DayBudgetLedgerRecord)).scalars().all() == []


def test_stored_calibration_accept_rejects_already_accepted_proposal_without_second_plan() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-stored-accept-once")
    baseline_plan = _active_body_plan(db, user_id=user.id)
    preview = client.post(
        "/calibration/proposal/preview",
        json={
            "user_id": "calibration-stored-accept-once",
            "local_date": "2026-05-04",
            "current_budget_status": "over_budget",
            "rescue_recovery_viability": "non_viable",
            "persist_proposal": True,
            "model_inputs": {
                "body_plan_estimated_tdee_kcal": 2100,
                "observation_window_days": 21,
                "body_observation_count": 9,
                "intake_coverage": 0.93,
                "operating_expenditure_shift_kcal": 340,
                "trend_mismatch_consistency": 0.9,
                "trend_volatility": 0.1,
                "logging_gap_ratio": 0.05,
                "late_logged_meal_ratio": 0.05,
            },
        },
    )
    proposal_id = preview.json()["proposal_artifact"]["proposal_container_id"]
    action_payload = {
        "user_id": "calibration-stored-accept-once",
        "proposal_container_id": proposal_id,
        "action": "accept_calibration_proposal",
        "accepted_at": "2026-05-04T10:30:00",
    }

    first = client.post("/calibration/proposal/stored-action", json=action_payload)
    second = client.post("/calibration/proposal/stored-action", json=action_payload)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "stored calibration proposal is not actionable: accepted"
    proposals = db.execute(select(ProposalContainerRecord)).scalars().all()
    plans = db.execute(select(BodyPlanRecord).order_by(BodyPlanRecord.id.asc())).scalars().all()
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
    assert len(proposals) == 1
    assert proposals[0].proposal_status == "accepted"
    assert len(plans) == 2
    assert plans[0].id == baseline_plan.id
    assert plans[0].plan_status == "superseded"
    assert plans[1].plan_status == "active"
    assert plans[1].daily_budget_kcal == 2000
    assert ledger.budget_kcal == 2000


def test_calibration_expiry_bookkeeping_route_expires_stale_open_proposals_without_plan_or_ledger_mutation() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-expiry-route")
    baseline_plan = _active_body_plan(db, user_id=user.id)
    preview = client.post(
        "/calibration/proposal/preview",
        json={
            "user_id": "calibration-expiry-route",
            "local_date": "2026-05-04",
            "current_budget_status": "over_budget",
            "rescue_recovery_viability": "non_viable",
            "persist_proposal": True,
            "model_inputs": {
                "body_plan_estimated_tdee_kcal": 2100,
                "observation_window_days": 21,
                "body_observation_count": 9,
                "intake_coverage": 0.93,
                "operating_expenditure_shift_kcal": 340,
                "trend_mismatch_consistency": 0.9,
                "trend_volatility": 0.1,
                "logging_gap_ratio": 0.05,
                "late_logged_meal_ratio": 0.05,
            },
        },
    )
    proposal_id = preview.json()["proposal_artifact"]["proposal_container_id"]
    proposal = db.get(ProposalContainerRecord, proposal_id)
    assert proposal is not None
    proposal.metadata_json = {
        **dict(proposal.metadata_json or {}),
        "expires_at": "2026-05-04T09:00:00",
    }
    db.commit()
    before_plan_count = len(db.execute(select(BodyPlanRecord)).scalars().all())
    before_ledger_count = len(db.execute(select(DayBudgetLedgerRecord)).scalars().all())

    response = client.post(
        "/calibration/proposals/expire-stale",
        json={
            "user_id": "calibration-expiry-route",
            "now_at": "2026-05-04T10:30:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "expired_count": 1,
        "expired_proposal_container_ids": [proposal_id],
    }
    db.refresh(proposal)
    assert proposal.proposal_status == "expired"
    assert proposal.accepted_at is None
    assert proposal.metadata_json["expired_at"] == "2026-05-04T10:30:00"
    plans = db.execute(select(BodyPlanRecord).order_by(BodyPlanRecord.id.asc())).scalars().all()
    assert len(plans) == before_plan_count
    assert plans[0].id == baseline_plan.id
    assert plans[0].plan_status == "active"
    assert len(db.execute(select(DayBudgetLedgerRecord)).scalars().all()) == before_ledger_count


def test_calibration_expiry_bookkeeping_route_does_not_create_unknown_user() -> None:
    db = _session()
    client = _client(db)

    response = client.post(
        "/calibration/proposals/expire-stale",
        json={
            "user_id": "calibration-expiry-unknown-user",
            "now_at": "2026-05-04T10:30:00",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "expired_count": 0,
        "expired_proposal_container_ids": [],
    }
    assert db.query(User).count() == 0


def test_calibration_preview_blocks_duplicate_when_open_stored_proposal_exists() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-duplicate-open")
    _active_body_plan(db, user_id=user.id)
    request_payload = {
        "user_id": "calibration-duplicate-open",
        "local_date": "2026-05-04",
        "current_budget_status": "over_budget",
        "rescue_recovery_viability": "non_viable",
        "persist_proposal": True,
        "model_inputs": {
            "body_plan_estimated_tdee_kcal": 2100,
            "observation_window_days": 21,
            "body_observation_count": 9,
            "intake_coverage": 0.93,
            "operating_expenditure_shift_kcal": 340,
            "trend_mismatch_consistency": 0.9,
            "trend_volatility": 0.1,
            "logging_gap_ratio": 0.05,
            "late_logged_meal_ratio": 0.05,
        },
    }

    first = client.post("/calibration/proposal/preview", json=request_payload)
    second = client.post("/calibration/proposal/preview", json=request_payload)

    assert first.status_code == 200
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["gate_result"]["proposal_eligibility"] is False
    assert any(
        "similar calibration proposal is still open" in reason
        for reason in second_payload["gate_result"]["gate_rationale"]
    )
    assert second_payload["response"]["surfaced"] is False
    assert second_payload["proposal_artifact"] is None
    proposals = db.execute(select(ProposalContainerRecord)).scalars().all()
    assert len(proposals) == 1
    assert proposals[0].proposal_status == "open"
