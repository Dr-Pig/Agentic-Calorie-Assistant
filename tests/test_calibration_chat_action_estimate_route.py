from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.body.infrastructure.models import BodyPlanRecord
from app.composition import intake_routes
from app.database import get_db, get_or_create_user
from app.models import Base, LedgerEntryRecord
from app.routes import router
from app.shared.infra.models import ProposalContainerRecord, ProposalOptionRecord


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


ROUTE_LOCAL_DATE = "2026-05-14"


class FixedRouteDateTime(datetime):
    @classmethod
    def now(cls, tz=None):  # noqa: ANN001
        return cls(2026, 5, 14, 10, 30, 0, tzinfo=tz)


def _client(db: Session, monkeypatch) -> TestClient:
    class ProviderShouldNotRun:
        async def generate(self, *_args, **_kwargs):  # pragma: no cover - failure sentinel
            raise AssertionError("explicit calibration action route must not invoke manager provider")

    monkeypatch.setattr(intake_routes, "manager_provider", ProviderShouldNotRun())
    monkeypatch.setattr(intake_routes, "search_provider", None)
    monkeypatch.setattr(intake_routes, "extract_provider", None)
    monkeypatch.setattr(intake_routes, "datetime", FixedRouteDateTime)

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _seed_stored_calibration_proposal(db: Session, *, user_external_id: str) -> int:
    user = get_or_create_user(db, user_external_id)
    plan = BodyPlanRecord(
        user_id=user.id,
        plan_status="active",
        plan_label="route action baseline",
        estimated_tdee=2100,
        daily_budget_kcal=1800,
        safety_floor_kcal=1200,
        target_pace_kg_per_week=0.5,
        metadata_json={"recommended_target_kcal": 1800, "plan_source": "test_baseline"},
        started_at=datetime(2026, 5, 1, 8, 0, 0),
        created_at=datetime(2026, 5, 1, 8, 0, 0),
    )
    db.add(plan)
    db.flush()
    proposal = ProposalContainerRecord(
        user_id=user.id,
        proposal_type="calibration",
        proposal_status="open",
        metadata_json={"local_date": ROUTE_LOCAL_DATE, "proposal_family": "budget_adjustment"},
    )
    db.add(proposal)
    db.flush()
    option = ProposalOptionRecord(
        proposal_container_id=proposal.id,
        option_type="budget_adjustment",
        option_label="Budget adjustment",
        option_summary="Route action stored proposal option",
        rank_order=0,
        is_primary=True,
        effect_payload_json={
            "new_daily_budget_kcal": 1650,
            "new_estimated_tdee_kcal": 2050,
            "calibration_adjustment_delta_kcal": -60,
            "review_after_days": 14,
            "rationale_summary": "route action calibration test",
        },
    )
    db.add(option)
    db.flush()
    proposal.top_option_id = option.id
    db.commit()
    return int(proposal.id)


def test_estimate_route_accepts_explicit_calibration_action_without_provider_or_raw_text_routing(monkeypatch) -> None:
    db = _session()
    user_external_id = "estimate-route-calibration-action-accept"
    proposal_id = _seed_stored_calibration_proposal(db, user_external_id=user_external_id)
    client = _client(db, monkeypatch)

    response = client.post(
        "/estimate",
        json={
            "text": "apply selected calibration proposal",
            "allow_search": False,
            "user_id": user_external_id,
            "calibration_proposal_container_id": proposal_id,
            "calibration_action": "accept_calibration_proposal",
        },
    )

    payload = response.json()["payload"]
    proposal = db.get(ProposalContainerRecord, proposal_id)
    ledger_entry = db.query(LedgerEntryRecord).one()
    active_plans = db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "active").all()
    superseded_plans = db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "superseded").all()
    assert response.status_code == 200
    assert response.json()["coach_message"].startswith("Calibration proposal accepted.")
    assert payload["manager_decision"]["intent_type"] == "calibration"
    assert payload["manager_decision"]["workflow_effect"] == "apply_calibration_proposal_action_with_state_mutation"
    assert payload["calibration_action_result"]["proposal_status"] == "accepted"
    assert payload["ui_hints"]["mode"] == "general_chat_calibration_action"
    assert payload["ui_hints"]["plan_mutation_authorized"] is True
    assert payload["required_read_surfaces"] == [
        "calibration_proposal_inbox",
        "CurrentBudgetView",
        "ActiveBodyPlanView",
        "body_budget_effective_budget_view",
    ]
    assert proposal is not None
    assert proposal.proposal_status == "accepted"
    assert len(active_plans) == 1
    assert active_plans[0].daily_budget_kcal == 1650
    assert len(superseded_plans) == 1
    assert ledger_entry.entry_type == "calibration_adjustment"
    assert ledger_entry.delta_kcal == -60


def test_estimate_route_calibration_action_requires_explicit_proposal_target(monkeypatch) -> None:
    db = _session()
    user_external_id = "estimate-route-calibration-action-missing-target"
    _seed_stored_calibration_proposal(db, user_external_id=user_external_id)
    client = _client(db, monkeypatch)

    response = client.post(
        "/estimate",
        json={
            "text": "accept it",
            "allow_search": False,
            "user_id": user_external_id,
            "calibration_action": "accept_calibration_proposal",
        },
    )

    payload = response.json()["payload"]
    active_plan = db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "active").one()
    assert response.status_code == 200
    assert payload["manager_decision"]["workflow_effect"] == "calibration_action_unavailable_without_state_mutation"
    assert payload["ui_hints"]["reason"] == "missing_explicit_proposal_container_id_or_action"
    assert active_plan.daily_budget_kcal == 1800
    assert db.query(LedgerEntryRecord).count() == 0
