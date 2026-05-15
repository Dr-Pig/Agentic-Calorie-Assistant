from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.budget.infrastructure.models import LedgerEntryRecord
from app.intake.infrastructure.models import LegacyMealLogMapRecord, MealThreadRecord, MealVersionRecord
from app.schemas import CommitRequestCandidate
from app.shared.contracts.correction_operation import structured_correction_operation
from app.shared.infra.models import User

from .canonical_body_support import recompute_day_budget_ledger, should_refresh_day_budget_ledger
from .canonical_commit_support import (
    CanonicalMealCommitResult,
    get_legacy_mapping_for_meal_log,
    resolve_canonical_commit_target,
    resolved_local_date,
    resolved_occurred_at,
)


def candidate_requests_whole_meal_removal(candidate: CommitRequestCandidate) -> bool:
    trace_ref = dict(candidate.trace_ref or {})
    target_ref = trace_ref.get("correction_target_ref")
    return structured_correction_operation(trace_ref) == "remove_meal" or (
        isinstance(target_ref, dict) and structured_correction_operation(target_ref) == "remove_meal"
    )


def remove_meal_thread_from_canonical(
    db: Session,
    *,
    user: User,
    candidate: CommitRequestCandidate,
    latest_log_id: int | None = None,
    persisted_log_id: int | None = None,
    budget_kcal: int | None = None,
) -> CanonicalMealCommitResult | None:
    try:
        occurred_at = resolved_occurred_at(candidate)
        local_date = resolved_local_date(candidate, occurred_at)
        target = resolve_canonical_commit_target(db, candidate=candidate, latest_log_id=latest_log_id)
        if target.meal_thread_id is None or target.superseded_version_id is None:
            return None
        thread = db.get(MealThreadRecord, target.meal_thread_id)
        if thread is None:
            return None
        superseded_version = db.get(MealVersionRecord, target.superseded_version_id)
        if superseded_version is not None:
            superseded_version.version_status = "superseded"
            superseded_version.superseded_at = datetime.now()

        version = MealVersionRecord(
            meal_thread_id=thread.id,
            parent_version_id=target.parent_version_id,
            version_status="removed",
            version_reason=target.version_reason,
            reason_payload_json={
                "manager_intent": candidate.manager_intent,
                "request_id": candidate.request_id,
                "version_reason": candidate.version_reason,
                "correction_operation": "remove_meal",
                "historical_correction_source_version_id": target.correction_target_version_id,
                "superseded_version_id": target.superseded_version_id,
                "source_log_id": target.source_log_id,
            },
            meal_title=candidate.meal_title or thread.title,
            raw_input=candidate.raw_input,
            source_request_id=candidate.request_id,
            manager_intent=candidate.manager_intent,
            resolution_status="removed_meal",
            total_kcal=0,
            protein_g=0,
            carb_g=0,
            fat_g=0,
            occurred_at=occurred_at,
            local_date=local_date,
        )
        db.add(version)
        db.flush()
        thread.active_version_id = version.id
        thread.updated_at = datetime.now()

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
            delta_kcal=0,
            metadata_json={
                "meal_thread_id": thread.id,
                "meal_title": candidate.meal_title,
                "request_id": candidate.request_id,
                "correction_operation": "remove_meal",
            },
        )
        db.add(entry)
        db.flush()

        if should_refresh_day_budget_ledger(db, user_id=user.id, local_date=local_date, explicit_budget_kcal=budget_kcal):
            recompute_day_budget_ledger(db, user_id=user.id, local_date=local_date, budget_kcal=budget_kcal, commit=False)
        db.commit()
        db.refresh(version)
        db.refresh(thread)
        db.refresh(entry)
        return CanonicalMealCommitResult(
            meal_thread_id=thread.id,
            meal_version_id=version.id,
            active_version_id=thread.active_version_id or version.id,
            local_date=local_date,
            consumed_kcal=0,
            created_new_thread=False,
            superseded_version_id=target.superseded_version_id,
            ledger_entry_id=entry.id,
        )
    except BaseException:
        db.rollback()
        raise
