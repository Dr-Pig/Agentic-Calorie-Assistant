from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.composition.calibration_proposal_inbox import (
    load_calibration_proposal_history,
    load_open_calibration_proposal_inbox,
)
from app.composition.calibration_routes import router as calibration_router
from app.composition.canonical_proposal_support import ensure_proposal_artifact_skeleton
from app.database import get_db, get_or_create_user
from app.models import Base
from app.shared.infra.models import ProposalContainerRecord, User


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


def _proposal(
    db: Session,
    *,
    user: User,
    status: str = "open",
    local_date: str = "2026-05-14",
    option_type: str = "budget_adjustment",
    created_at: datetime | None = None,
) -> ProposalContainerRecord:
    proposal = ensure_proposal_artifact_skeleton(
        db,
        user=user,
        proposal_type="calibration",
        metadata={
            "local_date": local_date,
            "proposal_family": option_type,
            "proposal_policy_packet": {
                "decision_mode": "deterministic",
                "plan_mutation_authorized": False,
                "ledger_mutation_authorized": False,
            },
            "trace_envelope": {
                "decision_mode": "deterministic",
                "automatic_calibration_enabled": False,
            },
        },
        options=[
            {
                "option_type": option_type,
                "option_label": option_type,
                "option_summary": f"{option_type} primary",
                "rank_order": 0,
                "is_primary": True,
                "effect_payload_json": {
                    "new_daily_budget_kcal": 2000,
                    "new_estimated_tdee_kcal": 2300,
                },
            },
            {
                "option_type": "monitor_only",
                "option_label": "monitor_only",
                "option_summary": "monitor backup",
                "rank_order": 1,
                "is_primary": False,
                "effect_payload_json": {"plan_change_required": False},
            },
        ],
    )
    proposal.proposal_status = status
    if created_at is not None:
        proposal.created_at = created_at
    db.commit()
    db.refresh(proposal)
    return proposal


def test_open_calibration_proposal_inbox_returns_active_proposals_with_options_sorted() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-inbox-read-model")
    accepted = _proposal(db, user=user, status="accepted", created_at=datetime(2026, 5, 1, 8, 0, 0))
    older_open = _proposal(db, user=user, status="open", created_at=datetime(2026, 5, 2, 8, 0, 0))
    newer_open = _proposal(db, user=user, status="open", created_at=datetime(2026, 5, 3, 8, 0, 0))

    inbox = load_open_calibration_proposal_inbox(db, user_id=user.id)

    assert [proposal.proposal_container_id for proposal in inbox] == [newer_open.id, older_open.id]
    assert accepted.id not in [proposal.proposal_container_id for proposal in inbox]
    assert inbox[0].proposal_type == "calibration"
    assert inbox[0].proposal_status == "open"
    assert inbox[0].metadata["proposal_policy_packet"]["plan_mutation_authorized"] is False
    assert inbox[0].metadata["trace_envelope"]["automatic_calibration_enabled"] is False
    assert [option.rank_order for option in inbox[0].options] == [0, 1]
    assert inbox[0].options[0].proposal_option_id == inbox[0].top_option_id
    assert inbox[0].options[0].effect_payload["new_daily_budget_kcal"] == 2000


def test_open_calibration_proposals_route_is_read_only_for_unknown_user() -> None:
    db = _session()
    client = _client(db)

    response = client.get("/calibration/proposals/open", params={"user_id": "missing-calibration-inbox-user"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "missing-calibration-inbox-user",
        "open_count": 0,
        "proposals": [],
    }
    assert db.execute(select(User).where(User.user_id == "missing-calibration-inbox-user")).scalar_one_or_none() is None


def test_open_calibration_proposals_route_returns_mirror_payload_without_mutation() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-inbox-route")
    proposal = _proposal(db, user=user, status="open", local_date="2026-05-14")

    response = client.get("/calibration/proposals/open", params={"user_id": "calibration-inbox-route"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "calibration-inbox-route"
    assert payload["open_count"] == 1
    proposal_payload = payload["proposals"][0]
    assert proposal_payload["proposal_container_id"] == proposal.id
    assert proposal_payload["local_date"] == "2026-05-14"
    assert proposal_payload["proposal_family"] == "budget_adjustment"
    assert proposal_payload["options"][0]["is_primary"] is True
    assert proposal_payload["options"][0]["effect_payload"]["new_daily_budget_kcal"] == 2000
    assert "user_id" not in proposal_payload
    assert "metadata" not in proposal_payload
    assert "proposal_policy_packet" not in proposal_payload
    assert "trace_envelope" not in proposal_payload
    assert db.get(ProposalContainerRecord, proposal.id).proposal_status == "open"


def test_calibration_proposal_history_returns_canonical_statuses_sorted() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-history-read-model")
    accepted = _proposal(db, user=user, status="accepted", created_at=datetime(2026, 5, 1, 8, 0, 0))
    dismissed = _proposal(db, user=user, status="dismissed", created_at=datetime(2026, 5, 2, 8, 0, 0))
    expired = _proposal(db, user=user, status="expired", created_at=datetime(2026, 5, 3, 8, 0, 0))
    legacy = _proposal(db, user=user, status="deferred_pending_reminder", created_at=datetime(2026, 5, 4, 8, 0, 0))

    history = load_calibration_proposal_history(db, user_id=user.id)

    assert [proposal.proposal_container_id for proposal in history] == [expired.id, dismissed.id, accepted.id]
    assert legacy.id not in [proposal.proposal_container_id for proposal in history]
    assert all(proposal.proposal_type == "calibration" for proposal in history)
    assert history[0].proposal_status == "expired"
    assert history[0].metadata["trace_envelope"]["automatic_calibration_enabled"] is False
    assert history[0].options[0].effect_payload["new_daily_budget_kcal"] == 2000


def test_calibration_proposal_history_route_projects_safe_read_only_payload() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-history-route")
    proposal = _proposal(db, user=user, status="expired", created_at=datetime(2026, 5, 3, 8, 0, 0))
    proposal.metadata_json = {
        **dict(proposal.metadata_json or {}),
        "expired_at": "2026-05-04T10:30:00",
        "expiry_reason": "expires_at_reached",
    }
    db.commit()

    response = client.get("/calibration/proposals/history", params={"user_id": "calibration-history-route"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "calibration-history-route"
    assert payload["history_count"] == 1
    item = payload["proposals"][0]
    assert item == {
        "proposal_container_id": proposal.id,
        "proposal_type": "calibration",
        "proposal_status": "expired",
        "top_option_id": proposal.top_option_id,
        "local_date": "2026-05-14",
        "proposal_family": "budget_adjustment",
        "created_at": "2026-05-03T08:00:00",
        "accepted_at": None,
        "expired_at": "2026-05-04T10:30:00",
        "expiry_reason": "expires_at_reached",
        "primary_option_type": "budget_adjustment",
        "primary_option_label": "budget_adjustment",
        "primary_option_summary": "budget_adjustment primary",
    }
    assert "user_id" not in item
    assert "metadata" not in item
    assert "proposal_policy_packet" not in item
    assert "trace_envelope" not in item
    assert "options" not in item
    assert "effect_payload" not in item
    assert db.get(ProposalContainerRecord, proposal.id).proposal_status == "expired"


def test_calibration_proposal_history_route_is_read_only_for_unknown_user() -> None:
    db = _session()
    client = _client(db)

    response = client.get("/calibration/proposals/history", params={"user_id": "missing-calibration-history-user"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "missing-calibration-history-user",
        "history_count": 0,
        "proposals": [],
    }
    assert db.execute(select(User).where(User.user_id == "missing-calibration-history-user")).scalar_one_or_none() is None
