from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.body.infrastructure.models import BodyPlanRecord
from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord
from app.composition.canonical_body_support import recompute_day_budget_ledger
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.current_budget_read_model import build_current_budget_view
from app.database import get_or_create_user
from app.models import Base
from app.schemas import CommitRequestCandidate


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_budget_adjustment_math_maps_signed_layers_to_legacy_runtime_adjustment() -> None:
    from app.budget.application.effective_budget_math import summarize_budget_adjustment_layers

    summary = summarize_budget_adjustment_layers(
        [
            SimpleNamespace(entry_type="manual_adjustment", delta_kcal=120),
            SimpleNamespace(entry_type="calibration_adjustment", delta_kcal=-50),
            SimpleNamespace(entry_type="rescue_overlay", delta_kcal=-30),
            SimpleNamespace(entry_type="calibration_adjustment", delta_kcal=20),
        ]
    )

    assert summary.manual_adjustment_total_kcal == 120
    assert summary.calibration_adjustment_total_kcal == -30
    assert summary.rescue_overlay_total_kcal == -30
    assert summary.signed_effective_budget_delta_kcal == -180
    assert summary.runtime_adjustment_total_kcal == 180
    assert summary.unclassified_adjustment_total_kcal == 0
    assert summary.sign_policy == "type_aware_signed_layers_to_legacy_subtractive_adjustment"


def test_recompute_day_budget_ledger_uses_type_aware_adjustment_math() -> None:
    db = _session()
    user = get_or_create_user(db, "type-aware-adjustment-user")
    db.add(
        BodyPlanRecord(
            user_id=user.id,
            plan_status="active",
            plan_label="baseline",
            estimated_tdee=2200,
            daily_budget_kcal=1800,
            safety_floor_kcal=1200,
            metadata_json={"plan_source": "test"},
            started_at=datetime(2026, 5, 9, 8, 0, 0),
            created_at=datetime(2026, 5, 9, 8, 0, 0),
        )
    )
    db.commit()

    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="type-aware-meal",
            manager_intent="food_estimation",
            version_reason="new_intake",
            meal_title="lunch",
            raw_input="lunch",
            estimated_kcal=600,
            protein_g=20,
            carb_g=60,
            fat_g=10,
            resolution_status="completed_meal",
            local_date="2026-05-09",
        ),
    )
    db.add_all(
        [
            LedgerEntryRecord(
                user_id=user.id,
                local_date="2026-05-09",
                entry_type="manual_adjustment",
                source_type="system",
                source_id=None,
                delta_kcal=120,
                metadata_json={},
            ),
            LedgerEntryRecord(
                user_id=user.id,
                local_date="2026-05-09",
                entry_type="calibration_adjustment",
                source_type="proposal_option",
                source_id=1,
                delta_kcal=-50,
                metadata_json={},
            ),
            LedgerEntryRecord(
                user_id=user.id,
                local_date="2026-05-09",
                entry_type="rescue_overlay",
                source_type="rescue_plan",
                source_id=2,
                delta_kcal=-30,
                metadata_json={},
            ),
        ]
    )
    db.commit()

    ledger = recompute_day_budget_ledger(db, user_id=user.id, local_date="2026-05-09")
    current_budget = build_current_budget_view(db, user_id=user.id, local_date="2026-05-09")

    assert ledger.budget_kcal == 1800
    assert ledger.consumed_kcal == 600
    assert ledger.adjustment_kcal == 200
    assert ledger.remaining_kcal == 1000
    assert current_budget.adjustment_kcal == 200
    assert current_budget.remaining_kcal == 1000
    assert len(db.execute(select(DayBudgetLedgerRecord)).scalars().all()) == 1
