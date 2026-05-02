from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.budget.infrastructure.models import LedgerEntryRecord
from app.intake.infrastructure.models import MealItemRecord, MealThreadRecord, MealVersionRecord
from app.shared.domain import CurrentBudgetView


def _item_rows(db: Session, *, version_id: int) -> list[MealItemRecord]:
    return db.execute(
        select(MealItemRecord)
        .where(MealItemRecord.meal_version_id == version_id)
        .order_by(MealItemRecord.item_index.asc(), MealItemRecord.id.asc())
    ).scalars().all()


def _item_payload(item: MealItemRecord) -> dict[str, Any]:
    return {
        "meal_item_id": item.id,
        "name": item.name,
        "estimated_kcal": int(item.estimated_kcal or 0),
    }


def _version_payload(db: Session, version: MealVersionRecord) -> dict[str, Any]:
    return {
        "meal_version_id": version.id,
        "parent_version_id": version.parent_version_id,
        "version_reason": version.version_reason,
        "total_kcal": int(version.total_kcal or 0),
        "items": [_item_payload(item) for item in _item_rows(db, version_id=version.id)],
    }


def _superseded_payload(version: MealVersionRecord) -> dict[str, Any]:
    return {
        "meal_version_id": version.id,
        "total_kcal": int(version.total_kcal or 0),
        "version_reason": version.version_reason,
    }


def _preserved_item_names(db: Session, *, old_version_id: int, new_version_id: int) -> list[str]:
    old_items = {item.name: int(item.estimated_kcal or 0) for item in _item_rows(db, version_id=old_version_id)}
    new_items = {item.name: int(item.estimated_kcal or 0) for item in _item_rows(db, version_id=new_version_id)}
    return [name for name, kcal in old_items.items() if name in new_items and new_items[name] == kcal]


def _meal_threads(db: Session, *, user_id: int, local_date: str) -> list[dict[str, Any]]:
    threads = db.execute(
        select(MealThreadRecord)
        .join(MealVersionRecord, MealThreadRecord.id == MealVersionRecord.meal_thread_id)
        .where(MealThreadRecord.user_id == user_id, MealVersionRecord.local_date == local_date)
        .order_by(MealThreadRecord.id.asc())
    ).scalars().unique().all()
    payloads: list[dict[str, Any]] = []
    for thread in threads:
        active_version = db.get(MealVersionRecord, thread.active_version_id) if thread.active_version_id else None
        superseded_versions = db.execute(
            select(MealVersionRecord)
            .where(
                MealVersionRecord.meal_thread_id == thread.id,
                MealVersionRecord.version_status == "superseded",
            )
            .order_by(MealVersionRecord.id.asc())
        ).scalars().all()
        payloads.append(
            {
                "meal_thread_id": thread.id,
                "active_version_id": thread.active_version_id,
                "title": thread.title,
                "active_version": _version_payload(db, active_version) if active_version is not None else None,
                "superseded_versions": [_superseded_payload(version) for version in superseded_versions],
            }
        )
    return payloads


def _correction_history(db: Session, *, user_id: int, local_date: str) -> list[dict[str, Any]]:
    versions = db.execute(
        select(MealVersionRecord)
        .join(MealThreadRecord, MealThreadRecord.id == MealVersionRecord.meal_thread_id)
        .where(
            MealThreadRecord.user_id == user_id,
            MealVersionRecord.local_date == local_date,
            MealVersionRecord.version_reason == "correction",
            MealVersionRecord.parent_version_id.is_not(None),
        )
        .order_by(MealVersionRecord.id.asc())
    ).scalars().all()
    history: list[dict[str, Any]] = []
    for version in versions:
        old_version = db.get(MealVersionRecord, version.parent_version_id)
        if old_version is None:
            continue
        history.append(
            {
                "meal_thread_id": version.meal_thread_id,
                "old_version_id": old_version.id,
                "new_version_id": version.id,
                "new_total_kcal": int(version.total_kcal or 0),
                "old_total_kcal": int(old_version.total_kcal or 0),
                "non_target_item_names_preserved": _preserved_item_names(
                    db,
                    old_version_id=old_version.id,
                    new_version_id=version.id,
                ),
            }
        )
    return history


def _pending_drafts(db: Session, *, user_id: int, local_date: str) -> list[dict[str, Any]]:
    versions = db.execute(
        select(MealVersionRecord)
        .join(MealThreadRecord, MealThreadRecord.id == MealVersionRecord.meal_thread_id)
        .where(
            MealThreadRecord.user_id == user_id,
            MealVersionRecord.local_date == local_date,
            MealVersionRecord.version_status != "superseded",
            MealVersionRecord.resolution_status.in_(("candidate_meal", "draft_unresolved")),
        )
        .order_by(MealVersionRecord.id.asc())
    ).scalars().all()
    return [
        {
            "meal_thread_id": version.meal_thread_id,
            "meal_version_id": version.id,
            "title": version.meal_title,
            "resolution_status": version.resolution_status,
            "total_kcal": int(version.total_kcal or 0),
            "read_only": True,
        }
        for version in versions
    ]


def _ledger_audit_events(db: Session, *, user_id: int, local_date: str) -> list[dict[str, Any]]:
    entries = db.execute(
        select(LedgerEntryRecord)
        .where(LedgerEntryRecord.user_id == user_id, LedgerEntryRecord.local_date == local_date)
        .order_by(LedgerEntryRecord.id.asc())
    ).scalars().all()
    return [
        {
            "entry_type": entry.entry_type,
            "source_id": entry.source_id,
            "delta_kcal": int(entry.delta_kcal or 0),
            "role": "audit_event",
            "current_truth_owner": False,
        }
        for entry in entries
    ]


def build_accurate_intake_debug_read_model(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    current_budget: CurrentBudgetView,
) -> dict[str, Any]:
    meal_threads = _meal_threads(db, user_id=user_id, local_date=local_date)
    active_version_total = sum(
        int((thread.get("active_version") or {}).get("total_kcal") or 0)
        for thread in meal_threads
    )
    current_budget_consumed = int(current_budget.consumed_kcal or 0)
    same_truth_status = "pass" if active_version_total == current_budget_consumed else "hard_fail"
    return {
        "today_summary": {
            "source_kind": "current_budget_read_model",
            "read_only": True,
            "user_id": user_id,
            "local_date": local_date,
            "budget_kcal": int(current_budget.budget_kcal or 0),
            "consumed_kcal": current_budget_consumed,
            "remaining_kcal": int(current_budget.remaining_kcal or 0),
            "active_meal_count": int(current_budget.active_meal_count or 0),
        },
        "meal_threads": meal_threads,
        "pending_drafts": _pending_drafts(db, user_id=user_id, local_date=local_date),
        "correction_history": _correction_history(db, user_id=user_id, local_date=local_date),
        "ledger_audit_events": _ledger_audit_events(db, user_id=user_id, local_date=local_date),
        "same_truth": {
            "status": same_truth_status,
            "source_truth": "active_meal_versions",
            "debug_model_consumed_kcal": active_version_total,
            "current_budget_consumed_kcal": current_budget_consumed,
        },
    }
