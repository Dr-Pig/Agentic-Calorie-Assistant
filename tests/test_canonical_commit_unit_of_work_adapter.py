from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord
from app.composition import canonical_persistence
from app.database import get_or_create_user
from app.intake.infrastructure.models import LegacyMealLogMapRecord, MealThreadRecord, MealVersionRecord
from app.models import Base
from app.schemas import CommitRequestCandidate


class _InjectedFailure(RuntimeError):
    pass


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _candidate(*, request_id: str = "phase-c-uow") -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id=request_id,
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title="rollback sandwich",
        raw_input="rollback sandwich",
        estimated_kcal=420,
        protein_g=18,
        carb_g=32,
        fat_g=14,
        resolution_status="completed_meal",
        local_date="2026-05-02",
    )


def _counts(db: Session) -> dict[str, int]:
    return {
        "threads": len(db.execute(select(MealThreadRecord)).scalars().all()),
        "versions": len(db.execute(select(MealVersionRecord)).scalars().all()),
        "legacy_maps": len(db.execute(select(LegacyMealLogMapRecord)).scalars().all()),
        "ledger_entries": len(db.execute(select(LedgerEntryRecord)).scalars().all()),
        "day_ledgers": len(db.execute(select(DayBudgetLedgerRecord)).scalars().all()),
    }


def test_canonical_commit_rolls_back_canonical_bridge_and_ledger_when_budget_refresh_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = _session()
    user = get_or_create_user(db, "phase-c-uow-budget-refresh")

    def fail_budget_refresh(*args: object, **kwargs: object) -> object:
        raise _InjectedFailure("budget_refresh")

    monkeypatch.setattr(canonical_persistence, "recompute_day_budget_ledger", fail_budget_refresh)

    with pytest.raises(_InjectedFailure):
        canonical_persistence.commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_candidate(),
            budget_kcal=1800,
        )

    assert _counts(db) == {
        "threads": 0,
        "versions": 0,
        "legacy_maps": 0,
        "ledger_entries": 0,
        "day_ledgers": 0,
    }


def test_canonical_commit_rolls_back_same_session_pending_state_when_legacy_bridge_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = _session()
    user = get_or_create_user(db, "phase-c-uow-legacy-bridge")

    def fail_legacy_bridge(*args: object, **kwargs: object) -> object:
        raise _InjectedFailure("legacy_bridge")

    monkeypatch.setattr(canonical_persistence, "get_legacy_mapping_for_meal_log", fail_legacy_bridge)

    with pytest.raises(_InjectedFailure):
        canonical_persistence.commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_candidate(request_id="phase-c-uow-legacy"),
            latest_log_id=999,
            budget_kcal=1800,
        )

    assert _counts(db) == {
        "threads": 0,
        "versions": 0,
        "legacy_maps": 0,
        "ledger_entries": 0,
        "day_ledgers": 0,
    }


def test_canonical_commit_rolls_back_canonical_and_bridge_when_ledger_audit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = _session()
    user = get_or_create_user(db, "phase-c-uow-ledger-audit")

    def fail_ledger_entry(*args: object, **kwargs: object) -> object:
        raise _InjectedFailure("ledger_audit")

    monkeypatch.setattr(canonical_persistence, "LedgerEntryRecord", fail_ledger_entry)

    with pytest.raises(_InjectedFailure):
        canonical_persistence.commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_candidate(request_id="phase-c-uow-ledger"),
            latest_log_id=999,
            budget_kcal=1800,
        )

    assert _counts(db) == {
        "threads": 0,
        "versions": 0,
        "legacy_maps": 0,
        "ledger_entries": 0,
        "day_ledgers": 0,
    }
