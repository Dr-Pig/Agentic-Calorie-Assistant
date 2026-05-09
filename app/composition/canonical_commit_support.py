from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.intake.infrastructure.models import LegacyMealLogMapRecord, MealThreadRecord, MealVersionRecord
from app.schemas import CommitRequestCandidate, CommitVersionReason, EstimatePayload


@dataclass(frozen=True)
class CanonicalCommitTarget:
    meal_thread_id: int | None
    parent_version_id: int | None
    superseded_version_id: int | None
    version_reason: CommitVersionReason
    correction_target_version_id: int | None
    source_log_id: int | None


@dataclass
class CanonicalMealCommitResult:
    meal_thread_id: int
    meal_version_id: int
    active_version_id: int
    local_date: str
    consumed_kcal: int
    created_new_thread: bool
    superseded_version_id: int | None
    ledger_entry_id: int | None


def payload_authorizes_macro_persistence(payload: EstimatePayload) -> bool:
    trace_contract = payload.trace_contract or {}
    return bool(payload.display_macro_breakdown) or trace_contract.get("macro_display_authorized") is not False


def canonical_macro_values_from_payload(payload: EstimatePayload) -> tuple[int, int, int]:
    display_macro = dict(payload.display_macro_breakdown or {})
    if display_macro:
        return (
            int(display_macro.get("protein_g") or 0),
            int(display_macro.get("carb_g") or 0),
            int(display_macro.get("fat_g") or 0),
        )
    if not payload_authorizes_macro_persistence(payload):
        return (0, 0, 0)
    return (int(payload.protein_g or 0), int(payload.carb_g or 0), int(payload.fat_g or 0))


def resolved_occurred_at(candidate: CommitRequestCandidate, occurred_at: datetime | None = None) -> datetime:
    chosen = occurred_at or candidate.occurred_at
    if isinstance(chosen, datetime):
        return chosen
    return datetime.now()


def resolved_local_date(candidate: CommitRequestCandidate, occurred_at: datetime) -> str:
    if isinstance(candidate.local_date, str) and candidate.local_date.strip():
        return candidate.local_date.strip()
    return occurred_at.date().isoformat()


def commit_candidate_from_payload(
    *,
    payload: EstimatePayload,
    raw_input: str,
    manager_intent: str,
    request_id: str | None,
) -> CommitRequestCandidate:
    trace_contract = payload.trace_contract or {}
    protein_g, carb_g, fat_g = canonical_macro_values_from_payload(payload)
    return CommitRequestCandidate(
        request_id=request_id or payload.request_id,
        manager_intent=manager_intent,
        version_reason="new_intake",
        meal_title=payload.meal_title or raw_input,
        raw_input=raw_input,
        estimated_kcal=payload.estimated_kcal,
        protein_g=protein_g,
        carb_g=carb_g,
        fat_g=fat_g,
        resolution_status="completed_meal",
        occurred_at=trace_contract.get("occurred_at"),
        local_date=str(trace_contract.get("local_date") or ""),
        items=[],
        trace_ref={"request_id": request_id or payload.request_id},
    )


def legacy_resolved_occurred_at(payload: EstimatePayload, occurred_at: datetime | None = None) -> datetime:
    trace_contract = payload.trace_contract or {}
    candidate = occurred_at or trace_contract.get("occurred_at")
    if isinstance(candidate, datetime):
        return candidate
    return datetime.now()


def legacy_resolved_local_date(payload: EstimatePayload, occurred_at: datetime) -> str:
    trace_contract = payload.trace_contract or {}
    legacy = trace_contract.get("local_date")
    if isinstance(legacy, str) and legacy.strip():
        return legacy.strip()
    return occurred_at.date().isoformat()


def get_legacy_mapping_for_meal_log(db: Session, meal_log_id: int | None) -> LegacyMealLogMapRecord | None:
    if meal_log_id is None:
        return None
    return db.execute(
        select(LegacyMealLogMapRecord).where(LegacyMealLogMapRecord.meal_log_id == meal_log_id)
    ).scalar_one_or_none()


def resolve_canonical_commit_target(
    db: Session,
    *,
    candidate: CommitRequestCandidate,
    latest_log_id: int | None = None,
) -> CanonicalCommitTarget:
    thread: MealThreadRecord | None = None
    parent_version_id: int | None = None
    superseded_version_id: int | None = None
    correction_target_version_id: int | None = None
    version_reason: CommitVersionReason = candidate.version_reason
    source_log_id = latest_log_id

    if candidate.meal_thread_id is not None:
        thread = db.get(MealThreadRecord, candidate.meal_thread_id)

    if candidate.parent_version_id is not None:
        parent = db.get(MealVersionRecord, candidate.parent_version_id)
        if parent is not None:
            parent_version_id = parent.id
            correction_target_version_id = parent.id
            if thread is None:
                thread = db.get(MealThreadRecord, parent.meal_thread_id)

    if thread is None and latest_log_id is not None:
        existing_map = get_legacy_mapping_for_meal_log(db, latest_log_id)
        if existing_map is not None:
            thread = db.get(MealThreadRecord, existing_map.meal_thread_id)
            source_log_id = latest_log_id
            if parent_version_id is None:
                parent_version_id = existing_map.meal_version_id
            if correction_target_version_id is None:
                correction_target_version_id = existing_map.meal_version_id

    if thread is not None:
        active_version_id = thread.active_version_id
        if parent_version_id is None:
            parent_version_id = active_version_id
        if correction_target_version_id is None:
            correction_target_version_id = parent_version_id
        if version_reason in {"correction", "historical_correction"}:
            if active_version_id is not None and parent_version_id is not None and active_version_id != parent_version_id:
                version_reason = "historical_correction"
                superseded_version_id = active_version_id
            else:
                superseded_version_id = parent_version_id
        else:
            superseded_version_id = None
    else:
        parent_version_id = None

    return CanonicalCommitTarget(
        meal_thread_id=thread.id if thread is not None else None,
        parent_version_id=parent_version_id,
        superseded_version_id=superseded_version_id,
        version_reason=version_reason,
        correction_target_version_id=correction_target_version_id,
        source_log_id=source_log_id,
    )


def load_active_meal_version(db: Session, meal_thread_id: int) -> MealVersionRecord | None:
    thread = db.get(MealThreadRecord, meal_thread_id)
    if thread is None or thread.active_version_id is None:
        return None
    return db.get(MealVersionRecord, thread.active_version_id)
