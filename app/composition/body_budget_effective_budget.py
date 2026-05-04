from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord
from app.composition.current_budget_read_model import build_current_budget_view


_KNOWN_ADJUSTMENT_ENTRY_TYPES = {
    "manual_adjustment",
    "calibration_adjustment",
    "rescue_overlay",
}


def _ledger_present(db: Session, *, user_id: int, local_date: str) -> bool:
    ledger_id = db.execute(
        select(DayBudgetLedgerRecord.id).where(
            DayBudgetLedgerRecord.user_id == user_id,
            DayBudgetLedgerRecord.local_date == local_date,
        )
    ).scalar_one_or_none()
    return ledger_id is not None


def _ledger_entries(db: Session, *, user_id: int, local_date: str) -> list[LedgerEntryRecord]:
    return list(
        db.execute(
            select(LedgerEntryRecord)
            .where(
                LedgerEntryRecord.user_id == user_id,
                LedgerEntryRecord.local_date == local_date,
                LedgerEntryRecord.entry_type != "meal_consumption",
            )
            .order_by(LedgerEntryRecord.id.asc())
        ).scalars().all()
    )


def _sum_entry_type(entries: list[LedgerEntryRecord], entry_type: str) -> int:
    return sum(int(entry.delta_kcal or 0) for entry in entries if entry.entry_type == entry_type)


def _entry_breakdown(entries: list[LedgerEntryRecord]) -> list[dict[str, Any]]:
    return [
        {
            "ledger_entry_id": entry.id,
            "entry_type": entry.entry_type,
            "source_type": entry.source_type,
            "source_id": entry.source_id,
            "delta_kcal": int(entry.delta_kcal or 0),
        }
        for entry in entries
    ]


def build_body_budget_effective_budget_view(
    db: Session,
    *,
    user_id: int,
    local_date: str,
) -> dict[str, Any]:
    current_budget = build_current_budget_view(db, user_id=user_id, local_date=local_date)
    ledger_present = _ledger_present(db, user_id=user_id, local_date=local_date)
    entries = _ledger_entries(db, user_id=user_id, local_date=local_date)

    base_budget_kcal = int(current_budget.budget_kcal or 0)
    consumed_kcal = int(current_budget.consumed_kcal or 0)
    runtime_adjustment_total = int(current_budget.adjustment_kcal or 0)
    remaining_kcal = int(current_budget.remaining_kcal or 0)
    runtime_effective_budget = remaining_kcal + consumed_kcal if ledger_present else 0

    manual_adjustment_total = _sum_entry_type(entries, "manual_adjustment")
    calibration_adjustment_total = _sum_entry_type(entries, "calibration_adjustment")
    rescue_overlay_total = _sum_entry_type(entries, "rescue_overlay")
    known_adjustment_total = manual_adjustment_total + calibration_adjustment_total + rescue_overlay_total
    all_adjustment_entries_total = sum(int(entry.delta_kcal or 0) for entry in entries)

    return {
        "source_kind": "body_budget_effective_budget_view",
        "read_only": True,
        "truth_owner": "budget_composition_effective_budget_read_model",
        "user_id": user_id,
        "local_date": local_date,
        "ledger_present": ledger_present,
        "base_budget_kcal": base_budget_kcal,
        "consumed_kcal": consumed_kcal,
        "runtime_adjustment_total_kcal": runtime_adjustment_total,
        "runtime_effective_budget_kcal": runtime_effective_budget,
        "remaining_kcal": remaining_kcal,
        "remaining_formula": "runtime_effective_budget_kcal - consumed_kcal",
        "adjustment_layers": {
            "manual_adjustment_total_kcal": manual_adjustment_total,
            "calibration_adjustment_total_kcal": calibration_adjustment_total,
            "rescue_overlay_total_kcal": rescue_overlay_total,
            "known_adjustment_entry_total_kcal": known_adjustment_total,
            "all_adjustment_entry_total_kcal": all_adjustment_entries_total,
            "unclassified_adjustment_total_kcal": all_adjustment_entries_total - known_adjustment_total,
        },
        "entry_breakdown": _entry_breakdown(entries),
        "sign_policy": {
            "current_runtime_policy": "positive_adjustment_reduces_available_budget",
            "canonical_l3m_policy": "base_budget_plus_signed_rescue_and_calibration_layers",
            "canonical_l3m_formula_enabled": False,
            "migration_required_before_calibration_adjustment_ledger_entries": True,
        },
        "calibration_adjustment_ledger_entry_enabled": False,
        "automatic_calibration_enabled": False,
        "rescue_enabled": False,
        "recommendation_enabled": False,
        "proactive_enabled": False,
        "live_tool_calling": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }


__all__ = ["build_body_budget_effective_budget_view"]
