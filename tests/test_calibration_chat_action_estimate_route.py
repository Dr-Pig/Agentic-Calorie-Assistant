from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.body.infrastructure.models import BodyObservationRecord, BodyPlanRecord, BodyProfileRecord
from app.composition import intake_routes
from app.database import get_db, get_or_create_user
from app.models import Base, DayBudgetLedgerRecord, LedgerEntryRecord, MealThreadRecord, MealVersionRecord
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


def _seed_calibration_history(db: Session, *, user_external_id: str) -> BodyPlanRecord:
    user = get_or_create_user(db, user_external_id)
    plan = BodyPlanRecord(
        user_id=user.id,
        plan_status="active",
        plan_label="route preview baseline",
        estimated_tdee=2100,
        daily_budget_kcal=1800,
        safety_floor_kcal=1200,
        target_pace_kg_per_week=0.5,
        metadata_json={"recommended_target_kcal": 1800, "plan_source": "test_baseline", "goal_type": "lose_weight"},
        started_at=datetime(2026, 5, 1, 8, 0, 0),
        created_at=datetime(2026, 5, 1, 8, 0, 0),
    )
    profile = BodyProfileRecord(
        user_id=user.id,
        profile_status="active",
        sex="female",
        age_years=31,
        height_cm=165.0,
        current_weight_kg=70.0,
        activity_level="light",
        goal_type="lose_weight",
        timezone="Asia/Taipei",
        created_at=datetime(2026, 5, 1, 8, 0, 0),
        updated_at=datetime(2026, 5, 1, 8, 0, 0),
    )
    db.add_all([plan, profile])
    db.flush()
    for offset in range(14):
        day = (datetime(2026, 5, 1) + timedelta(days=offset)).date().isoformat()
        thread = MealThreadRecord(
            user_id=user.id,
            title=f"meal {day}",
            thread_kind="text_intake",
            created_at=datetime.fromisoformat(day).replace(hour=12),
            updated_at=datetime.fromisoformat(day).replace(hour=12),
        )
        db.add(thread)
        db.flush()
        version = MealVersionRecord(
            meal_thread_id=thread.id,
            version_status="active",
            version_reason="new_intake",
            meal_title=f"meal {day}",
            raw_input="test meal",
            resolution_status="completed_meal",
            total_kcal=1800,
            protein_g=0,
            carb_g=0,
            fat_g=0,
            occurred_at=datetime.fromisoformat(day).replace(hour=12),
            local_date=day,
            created_at=datetime.fromisoformat(day).replace(hour=13),
        )
        db.add(version)
        db.flush()
        thread.active_version_id = version.id
    for day, value in [
        ("2026-05-01", 70.0),
        ("2026-05-04", 69.7),
        ("2026-05-07", 69.4),
        ("2026-05-10", 69.1),
        ("2026-05-14", 68.8),
    ]:
        db.add(
            BodyObservationRecord(
                user_id=user.id,
                observation_type="weight",
                value=value,
                unit="kg",
                observed_at=datetime.fromisoformat(day).replace(hour=7),
                local_date=day,
                source="manual",
                metadata_json={},
                created_at=datetime.fromisoformat(day).replace(hour=7, minute=5),
            )
        )
    db.add(
        DayBudgetLedgerRecord(
            user_id=user.id,
            local_date=ROUTE_LOCAL_DATE,
            budget_kcal=1800,
            consumed_kcal=1800,
            adjustment_kcal=0,
            remaining_kcal=0,
        )
    )
    db.commit()
    db.refresh(plan)
    return plan


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


def test_estimate_route_can_preview_calibration_from_history_without_provider_or_plan_mutation(monkeypatch) -> None:
    db = _session()
    user_external_id = "estimate-route-calibration-preview"
    baseline_plan = _seed_calibration_history(db, user_external_id=user_external_id)
    before_body_plan_count = db.query(BodyPlanRecord).count()
    before_ledger_count = db.query(DayBudgetLedgerRecord).count()
    client = _client(db, monkeypatch)

    response = client.post(
        "/estimate",
        json={
            "text": "preview calibration from backend history",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": ROUTE_LOCAL_DATE,
            "calibration_preview_requested": True,
            "persist_calibration_proposal": True,
        },
    )

    payload = response.json()["payload"]
    proposal = db.query(ProposalContainerRecord).one()
    active_plan = db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "active").one()
    assert response.status_code == 200
    assert response.json()["coach_message"].startswith("Calibration preview surfaced")
    assert payload["manager_decision"]["intent_type"] == "calibration"
    assert payload["manager_decision"]["workflow_effect"] == "preview_calibration_proposal_without_plan_mutation"
    assert payload["manager_decision"]["explicit_structured_preview"] is True
    assert payload["state_delta"]["calibration_preview_processed"] is True
    assert payload["state_delta"]["proposal_persisted"] is True
    assert payload["state_delta"]["proposal_container_id"] == proposal.id
    assert payload["state_delta"]["plan_mutated"] is False
    assert payload["state_delta"]["ledger_mutated"] is False
    assert payload["ui_hints"]["mode"] == "general_chat_calibration_preview"
    assert payload["ui_hints"]["proposal_actions_enabled"] is True
    assert payload["ui_hints"]["stored_action_route_contract"] == "/calibration/proposal/stored-action"
    assert payload["required_read_surfaces"] == [
        "CalibrationInputAssembly",
        "CurrentBudgetView",
        "ActiveBodyPlanView",
        "CalibrationProposalPolicyPacket",
    ]
    assert payload["input_assembly"]["trace"]["window_days"] == 14
    assert payload["input_assembly"]["trace"]["body_observation_count"] == 5
    assert payload["proposal_response"]["surfaced"] is True
    assert "reply_text" not in payload["proposal_response"]
    assert "top_option" not in payload["proposal_response"]
    assert "backup_options" not in payload["proposal_response"]
    assert payload["proposal_response"]["proposal_cards"][0]["is_primary"] is True
    assert payload["proposal_response"]["proposal_cards"][0]["stored_action_required"] is True
    assert "proposal_response" not in payload["sidecar"]
    preview_actions = {action["action"]: action for action in payload["proposal_response"]["quick_actions"]}
    assert preview_actions["accept_calibration_proposal"]["requires_proposal_container_id"] is True
    assert preview_actions["accept_calibration_proposal"]["raw_text_authorized_mutation"] is False
    assert preview_actions["accept_calibration_proposal"]["enabled"] is True
    assert preview_actions["accept_calibration_proposal"]["proposal_container_id"] == proposal.id
    assert preview_actions["view_calibration_alternatives"]["mutation_authorized"] is False
    assert payload["proposal_artifact"]["proposal_container_id"] == proposal.id
    assert proposal.proposal_status == "open"
    assert active_plan.id == baseline_plan.id
    assert active_plan.daily_budget_kcal == 1800
    assert db.query(BodyPlanRecord).count() == before_body_plan_count
    assert db.query(DayBudgetLedgerRecord).count() == before_ledger_count
    assert db.query(LedgerEntryRecord).count() == 0


def test_estimate_route_calibration_preview_missing_history_is_unavailable_without_mutation(monkeypatch) -> None:
    db = _session()
    user_external_id = "estimate-route-calibration-preview-missing-history"
    client = _client(db, monkeypatch)

    response = client.post(
        "/estimate",
        json={
            "text": "preview calibration from backend history",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": ROUTE_LOCAL_DATE,
            "calibration_preview_requested": True,
            "persist_calibration_proposal": True,
        },
    )

    payload = response.json()["payload"]
    assert response.status_code == 200
    assert payload["manager_decision"]["workflow_effect"] == "calibration_preview_unavailable_without_state_mutation"
    assert payload["state_delta"]["calibration_preview_processed"] is True
    assert payload["state_delta"]["proposal_persisted"] is False
    assert payload["state_delta"]["plan_mutated"] is False
    assert payload["state_delta"]["ledger_mutated"] is False
    assert payload["ui_hints"]["mode"] == "general_chat_calibration_preview_unavailable"
    assert payload["ui_hints"]["plan_mutation_authorized"] is False
    assert payload["ui_hints"]["ledger_mutation_authorized"] is False
    unavailable_reason = payload["ui_hints"]["reason"]
    assert payload["proposal_response"] == {
        "surfaced": False,
        "proposal_family": None,
        "proposal_cards": [],
        "quick_actions": [],
        "ui_hints": {
            "reason": unavailable_reason,
            "proposal_actions_enabled": False,
        },
        "proposal_container_id": None,
        "stored_action_required": True,
        "raw_text_authorized_mutation": False,
    }
    assert db.query(ProposalContainerRecord).count() == 0
    assert db.query(BodyPlanRecord).count() == 0
    assert db.query(DayBudgetLedgerRecord).count() == 0
    assert db.query(LedgerEntryRecord).count() == 0


def test_estimate_route_preview_without_persistence_disables_stored_action_quick_actions(monkeypatch) -> None:
    db = _session()
    user_external_id = "estimate-route-calibration-preview-no-persist"
    _seed_calibration_history(db, user_external_id=user_external_id)
    client = _client(db, monkeypatch)

    response = client.post(
        "/estimate",
        json={
            "text": "preview calibration from backend history",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": ROUTE_LOCAL_DATE,
            "calibration_preview_requested": True,
            "persist_calibration_proposal": False,
        },
    )

    payload = response.json()["payload"]
    preview_actions = {action["action"]: action for action in payload["proposal_response"]["quick_actions"]}
    assert response.status_code == 200
    assert payload["state_delta"]["proposal_persisted"] is False
    assert payload["proposal_artifact"] is None
    assert preview_actions["accept_calibration_proposal"]["enabled"] is False
    assert preview_actions["accept_calibration_proposal"]["disabled_reason"] == "stored_proposal_required"
    assert preview_actions["accept_calibration_proposal"]["proposal_container_id"] is None
    assert preview_actions["accept_calibration_proposal"]["mutation_authorized"] is False
    assert preview_actions["reject_calibration_proposal"]["enabled"] is False
    assert preview_actions["defer_calibration_proposal"]["enabled"] is False
    assert preview_actions["view_calibration_alternatives"]["enabled"] is True
    assert db.query(ProposalContainerRecord).count() == 0
    assert db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "active").one().daily_budget_kcal == 1800
    assert db.query(LedgerEntryRecord).count() == 0


def test_estimate_route_raw_calibration_text_does_not_activate_preview_or_persist_proposal(monkeypatch) -> None:
    db = _session()
    user_external_id = "estimate-route-raw-text-no-preview"
    baseline_plan = _seed_calibration_history(db, user_external_id=user_external_id)
    client = _client(db, monkeypatch)

    response = client.post(
        "/estimate",
        json={
            "text": "should we adjust my target?",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": ROUTE_LOCAL_DATE,
            "persist_calibration_proposal": True,
        },
    )

    payload = response.json()["payload"]
    active_plan = db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "active").one()
    assert response.status_code == 200
    assert payload["manager_decision"]["intent_type"] == "manager_unavailable"
    assert payload["manager_decision"]["workflow_effect"] == "safe_failure"
    assert db.query(ProposalContainerRecord).count() == 0
    assert active_plan.id == baseline_plan.id
    assert active_plan.daily_budget_kcal == 1800
    assert db.query(LedgerEntryRecord).count() == 0


def test_estimate_route_open_calibration_proposal_without_explicit_action_is_ignored_without_mutation(
    monkeypatch,
) -> None:
    db = _session()
    user_external_id = "estimate-route-open-proposal-raw-action"
    proposal_id = _seed_stored_calibration_proposal(db, user_external_id=user_external_id)
    client = _client(db, monkeypatch)

    response = client.post(
        "/estimate",
        json={
            "text": "apply that calibration proposal",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": ROUTE_LOCAL_DATE,
            "persist_calibration_proposal": True,
        },
    )

    payload = response.json()["payload"]
    proposal = db.get(ProposalContainerRecord, proposal_id)
    active_plan = db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "active").one()
    assert response.status_code == 200
    assert payload["manager_decision"]["intent_type"] == "manager_unavailable"
    assert payload["manager_decision"]["workflow_effect"] == "safe_failure"
    assert proposal is not None
    assert proposal.proposal_status == "open"
    assert active_plan.daily_budget_kcal == 1800
    assert db.query(LedgerEntryRecord).count() == 0


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
            "calibration_preview_requested": True,
            "persist_calibration_proposal": True,
            "calibration_proposal_container_id": proposal_id,
            "calibration_action": "accept_calibration_proposal",
            "calibration_action_accepted_at": "2026-05-14T10:30:00",
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
    assert payload["calibration_action_result"]["effective_from"] == ROUTE_LOCAL_DATE
    assert payload["ui_hints"]["mode"] == "general_chat_calibration_action"
    assert payload["ui_hints"]["effective_from"] == ROUTE_LOCAL_DATE
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
    assert ledger_entry.local_date == ROUTE_LOCAL_DATE
    assert ledger_entry.delta_kcal == -60


def test_estimate_route_accept_after_local_cutoff_applies_next_day_from_backend(monkeypatch) -> None:
    db = _session()
    user_external_id = "estimate-route-calibration-action-accept-after-cutoff"
    proposal_id = _seed_stored_calibration_proposal(db, user_external_id=user_external_id)
    client = _client(db, monkeypatch)

    response = client.post(
        "/estimate",
        json={
            "text": "apply selected calibration proposal",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": ROUTE_LOCAL_DATE,
            "calibration_proposal_container_id": proposal_id,
            "calibration_action": "accept_calibration_proposal",
            "calibration_action_accepted_at": "2026-05-14T11:30:00",
        },
    )

    payload = response.json()["payload"]
    ledger = db.query(DayBudgetLedgerRecord).one()
    ledger_entry = db.query(LedgerEntryRecord).one()
    assert response.status_code == 200
    assert payload["calibration_action_result"]["proposal_status"] == "accepted"
    assert payload["calibration_action_result"]["effective_from"] == "2026-05-15"
    assert payload["calibration_action_result"]["current_budget_view"]["budget_kcal"] == 1650
    assert payload["ui_hints"]["effective_from"] == "2026-05-15"
    assert ledger.local_date == "2026-05-15"
    assert ledger.budget_kcal == 1650
    assert ledger_entry.local_date == "2026-05-15"
    assert ledger_entry.delta_kcal == -60


def test_estimate_route_rejects_invalid_calibration_action_accepted_at_without_mutation(monkeypatch) -> None:
    for invalid_accepted_at in ["not-a-date", ROUTE_LOCAL_DATE]:
        db = _session()
        user_external_id = f"estimate-route-invalid-accepted-at-{invalid_accepted_at}"
        proposal_id = _seed_stored_calibration_proposal(db, user_external_id=user_external_id)
        client = _client(db, monkeypatch)

        response = client.post(
            "/estimate",
            json={
                "text": "apply selected calibration proposal",
                "allow_search": False,
                "user_id": user_external_id,
                "local_date": ROUTE_LOCAL_DATE,
                "calibration_proposal_container_id": proposal_id,
                "calibration_action": "accept_calibration_proposal",
                "calibration_action_accepted_at": invalid_accepted_at,
            },
        )

        proposal = db.get(ProposalContainerRecord, proposal_id)
        active_plan = db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "active").one()
        assert response.status_code == 422
        assert proposal is not None
        assert proposal.proposal_status == "open"
        assert active_plan.daily_budget_kcal == 1800
        assert db.query(BodyPlanRecord).count() == 1
        assert db.query(DayBudgetLedgerRecord).count() == 0
        assert db.query(LedgerEntryRecord).count() == 0


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
