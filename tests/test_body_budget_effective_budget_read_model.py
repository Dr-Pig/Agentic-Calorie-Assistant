from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord
from app.composition.current_budget_read_model import build_current_budget_view
from app.composition.today_routes import router as today_router
from app.database import get_db, get_or_create_user
from app.models import Base


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
    app.include_router(today_router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _seed_adjusted_day(db: Session) -> int:
    user = get_or_create_user(db, "effective-budget-user")
    ledger = DayBudgetLedgerRecord(
        user_id=user.id,
        local_date="2026-05-08",
        budget_kcal=1800,
        consumed_kcal=0,
        adjustment_kcal=170,
        remaining_kcal=1630,
    )
    db.add(ledger)
    db.flush()
    db.add_all(
        [
            LedgerEntryRecord(
                user_id=user.id,
                local_date="2026-05-08",
                entry_type="manual_adjustment",
                source_type="system",
                source_id=None,
                delta_kcal=120,
                metadata_json={"reason": "test manual compression"},
            ),
            LedgerEntryRecord(
                user_id=user.id,
                local_date="2026-05-08",
                entry_type="calibration_adjustment",
                source_type="proposal_option",
                source_id=42,
                delta_kcal=-50,
                metadata_json={"reason": "test accepted calibration layer"},
            ),
        ]
    )
    db.commit()
    return user.id


def test_effective_budget_read_model_layers_entries_and_preserves_current_budget_truth() -> None:
    db = _session()
    user_id = _seed_adjusted_day(db)
    before_ledgers = db.execute(select(DayBudgetLedgerRecord)).scalars().all()
    before_entries = db.execute(select(LedgerEntryRecord)).scalars().all()

    from app.composition.body_budget_effective_budget import build_body_budget_effective_budget_view

    current_budget = build_current_budget_view(db, user_id=user_id, local_date="2026-05-08")
    view = build_body_budget_effective_budget_view(db, user_id=user_id, local_date="2026-05-08")

    assert view["source_kind"] == "body_budget_effective_budget_view"
    assert view["read_only"] is True
    assert view["truth_owner"] == "budget_composition_effective_budget_read_model"
    assert view["ledger_present"] is True
    assert view["base_budget_kcal"] == 1800
    assert view["consumed_kcal"] == current_budget.consumed_kcal
    assert view["runtime_adjustment_total_kcal"] == current_budget.adjustment_kcal == 170
    assert view["runtime_effective_budget_kcal"] == 1630
    assert view["remaining_kcal"] == current_budget.remaining_kcal == 1630
    assert view["remaining_formula"] == "runtime_effective_budget_kcal - consumed_kcal"
    assert view["adjustment_layers"]["manual_adjustment_total_kcal"] == 120
    assert view["adjustment_layers"]["calibration_adjustment_total_kcal"] == -50
    assert view["adjustment_layers"]["rescue_overlay_total_kcal"] == 0
    assert view["adjustment_layers"]["signed_effective_budget_delta_kcal"] == -170
    assert view["adjustment_layers"]["runtime_adjustment_total_from_entries_kcal"] == 170
    assert view["adjustment_layers"]["known_adjustment_entry_total_kcal"] == 70
    assert view["adjustment_layers"]["unclassified_adjustment_total_kcal"] == 0
    assert view["entry_breakdown"] == [
        {
            "ledger_entry_id": before_entries[0].id,
            "entry_type": "manual_adjustment",
            "source_type": "system",
            "source_id": None,
            "delta_kcal": 120,
        },
        {
            "ledger_entry_id": before_entries[1].id,
            "entry_type": "calibration_adjustment",
            "source_type": "proposal_option",
            "source_id": 42,
            "delta_kcal": -50,
        },
    ]
    assert view["sign_policy"]["current_runtime_policy"] == "type_aware_signed_layers_to_legacy_subtractive_adjustment"
    assert view["sign_policy"]["canonical_l3m_policy"] == "base_budget_plus_signed_rescue_and_calibration_layers"
    assert view["sign_policy"]["canonical_l3m_formula_enabled"] is True
    assert view["calibration_adjustment_ledger_entry_enabled"] is True
    assert view["rescue_enabled"] is False
    assert view["recommendation_enabled"] is False
    assert view["proactive_enabled"] is False
    assert db.execute(select(DayBudgetLedgerRecord)).scalars().all() == before_ledgers
    assert db.execute(select(LedgerEntryRecord)).scalars().all() == before_entries


def test_today_effective_budget_route_returns_backend_owned_read_model() -> None:
    db = _session()
    client = _client(db)
    _seed_adjusted_day(db)

    response = client.get(
        "/today/effective-budget",
        params={"user_id": "effective-budget-user", "local_date": "2026-05-08"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_kind"] == "body_budget_effective_budget_view"
    assert payload["base_budget_kcal"] == 1800
    assert payload["runtime_effective_budget_kcal"] == 1630
    assert payload["remaining_kcal"] == 1630
    assert payload["adjustment_layers"]["calibration_adjustment_total_kcal"] == -50
    assert payload["sign_policy"]["canonical_l3m_formula_enabled"] is True


def test_bodybudget_plce_matrix_lists_effective_budget_as_backend_owned_read_model() -> None:
    matrix = Path("docs/specs/UI_CANONICAL_TRUTH_SURFACE_MATRIX.md")
    text = matrix.read_text(encoding="utf-8-sig")

    assert "`body_budget_effective_budget_view`" in text
    assert "/today/effective-budget" in text
    assert "app.composition.body_budget_effective_budget.build_body_budget_effective_budget_view" in text
    assert "Do not calculate effective budget, adjustment layer totals, or sign policy in PL/CE" in text
