from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.budget.infrastructure.models import LedgerEntryRecord
from app.intake.infrastructure.models import LegacyMealLogMapRecord, MealThreadRecord, MealVersionRecord
from app.schemas import CommitRequestCandidate, EstimatePayload
from app.shared.infra.models import User

from .canonical_body_support import (
    recompute_day_budget_ledger,
    should_refresh_day_budget_ledger,
)
from .canonical_commit_support import (
    CanonicalMealCommitResult,
    get_legacy_mapping_for_meal_log,
    resolve_canonical_commit_target,
)
from .canonical_commit_support import (
    commit_candidate_from_payload as _commit_candidate_from_payload,
)
from .canonical_commit_support import (
    resolved_local_date as _resolved_local_date,
)
from .canonical_commit_support import (
    resolved_occurred_at as _resolved_occurred_at,
)
from .canonical_meal_removal_persistence import (
    candidate_requests_whole_meal_removal,
    remove_meal_thread_from_canonical,
)
from .canonical_meal_item_persistence import (
    candidate_with_item_removal_totals,
    item_records_for_candidate,
)
from .phase_c_transaction_ports import PhaseCUnitOfWorkPort


class _SQLAlchemyPhaseCUnitOfWork(PhaseCUnitOfWorkPort):
    def __init__(self, db: Session) -> None:
        self.db = db

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()


def upsert_budget_adjustment_skeleton(
    db: Session,
    *,
    user: User,
    delta_kcal: int,
    local_date: str,
    metadata: dict[str, Any] | None = None,
) -> LedgerEntryRecord:
    entry = LedgerEntryRecord(
        user_id=user.id,
        local_date=local_date,
        entry_type="manual_adjustment",
        source_type="manual",
        source_id=0,
        delta_kcal=delta_kcal,
        metadata_json=dict(metadata or {}),
    )
    db.add(entry)
    db.flush()
    db.commit()
    db.refresh(entry)
    recompute_day_budget_ledger(db, user_id=user.id, local_date=local_date)
    return entry


def commit_meal_payload_to_canonical(
    db: Session,
    *,
    user: User,
    candidate: CommitRequestCandidate | None = None,
    payload: EstimatePayload | None = None,
    raw_input: str | None = None,
    manager_intent: str | None = None,
    request_id: str | None = None,
    latest_log_id: int | None = None,
    persisted_log_id: int | None = None,
    budget_kcal: int | None = None,
) -> CanonicalMealCommitResult | None:
    if candidate is None:
        assert payload is not None
        assert raw_input is not None
        assert manager_intent is not None
        candidate = _commit_candidate_from_payload(
            payload=payload,
            raw_input=raw_input,
            manager_intent=manager_intent,
            request_id=request_id,
        )
    if payload is None:
        assert raw_input is not None or candidate.raw_input
    source_payload = payload
    candidate = candidate_with_item_removal_totals(db, candidate)

    if candidate_requests_whole_meal_removal(candidate):
        return remove_meal_thread_from_canonical(
            db,
            user=user,
            candidate=candidate,
            latest_log_id=latest_log_id,
            persisted_log_id=persisted_log_id,
            budget_kcal=budget_kcal,
        )

    if candidate.estimated_kcal <= 0:
        return None

    uow = _SQLAlchemyPhaseCUnitOfWork(db)
    try:
        occurred_at = _resolved_occurred_at(candidate)
        local_date = _resolved_local_date(candidate, occurred_at)

        target = resolve_canonical_commit_target(
            db,
            candidate=candidate,
            latest_log_id=latest_log_id,
        )
        thread = db.get(MealThreadRecord, target.meal_thread_id) if target.meal_thread_id is not None else None
        created_new_thread = thread is None
        superseded_version_id = target.superseded_version_id

        if thread is None:
            thread = MealThreadRecord(
                user_id=user.id,
                title=candidate.meal_title or candidate.raw_input,
                thread_kind="text_intake",
                updated_at=datetime.now(),
            )
            db.add(thread)
            db.flush()
        else:
            thread.title = candidate.meal_title or thread.title
            thread.updated_at = datetime.now()

        if superseded_version_id is not None:
            superseded_version = db.get(MealVersionRecord, superseded_version_id)
            if superseded_version is not None:
                superseded_version.version_status = "superseded"
                superseded_version.superseded_at = datetime.now()

        version = MealVersionRecord(
            meal_thread_id=thread.id,
            parent_version_id=target.parent_version_id,
            version_reason=candidate.version_reason,
            reason_payload_json={
                "manager_intent": candidate.manager_intent,
                "route_target": (source_payload.route_target if source_payload is not None else None),
                "request_id": candidate.request_id,
                "version_reason": candidate.version_reason,
                "historical_correction_source_version_id": target.correction_target_version_id,
                "superseded_version_id": superseded_version_id,
                "source_log_id": target.source_log_id,
            },
            meal_title=candidate.meal_title or candidate.raw_input,
            raw_input=candidate.raw_input,
            source_request_id=candidate.request_id,
            manager_intent=candidate.manager_intent,
            resolution_status=candidate.resolution_status,
            total_kcal=candidate.estimated_kcal,
            protein_g=candidate.protein_g,
            carb_g=candidate.carb_g,
            fat_g=candidate.fat_g,
            occurred_at=occurred_at,
            local_date=local_date,
        )
        db.add(version)
        db.flush()

        for item in item_records_for_candidate(
            db,
            version_id=version.id,
            candidate=candidate,
            source_payload=source_payload,
        ):
            db.add(item)

        thread.active_version_id = version.id
        db.flush()

        source_log_id = persisted_log_id or latest_log_id
        if source_log_id is not None:
            existing_for_source = get_legacy_mapping_for_meal_log(db, source_log_id)
            if existing_for_source is None:
                db.add(
                    LegacyMealLogMapRecord(
                        meal_log_id=source_log_id,
                        meal_thread_id=thread.id,
                        meal_version_id=version.id,
                    )
                )
            else:
                existing_for_source.meal_thread_id = thread.id
                existing_for_source.meal_version_id = version.id

        entry = LedgerEntryRecord(
            user_id=user.id,
            local_date=local_date,
            entry_type="meal_consumption",
            source_type="meal_version",
            source_id=version.id,
            delta_kcal=candidate.estimated_kcal,
            metadata_json={
                "meal_thread_id": thread.id,
                "meal_title": candidate.meal_title,
                "request_id": candidate.request_id,
            },
        )
        db.add(entry)
        db.flush()

        if should_refresh_day_budget_ledger(
            db,
            user_id=user.id,
            local_date=local_date,
            explicit_budget_kcal=budget_kcal,
        ):
            recompute_day_budget_ledger(
                db,
                user_id=user.id,
                local_date=local_date,
                budget_kcal=budget_kcal,
                commit=False,
            )
        uow.commit()
        db.refresh(version)
        db.refresh(thread)
        db.refresh(entry)

        return CanonicalMealCommitResult(
            meal_thread_id=thread.id,
            meal_version_id=version.id,
            active_version_id=thread.active_version_id or version.id,
            local_date=local_date,
            consumed_kcal=candidate.estimated_kcal,
            created_new_thread=created_new_thread,
            superseded_version_id=superseded_version_id,
            ledger_entry_id=entry.id,
        )
    except BaseException:
        uow.rollback()
        raise
