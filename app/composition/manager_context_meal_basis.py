from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.intake.infrastructure.models import MealItemRecord, MealThreadRecord, MealVersionRecord
from app.shared.infra.models import User


def build_active_meal_estimate_basis(
    db: Session | None,
    *,
    user_external_id: str,
    local_date: str,
) -> dict[str, Any] | None:
    """Return a read-only basis snapshot for the latest active meal on this day."""

    if db is None:
        return None
    user = db.query(User).filter(User.user_id == user_external_id).first()
    if user is None:
        return None
    row = (
        db.execute(
            select(MealThreadRecord, MealVersionRecord)
            .join(MealVersionRecord, MealThreadRecord.active_version_id == MealVersionRecord.id)
            .where(
                MealThreadRecord.user_id == user.id,
                MealVersionRecord.local_date == local_date,
                MealVersionRecord.version_status == "active",
                MealVersionRecord.resolution_status == "completed_meal",
            )
            .order_by(desc(MealVersionRecord.created_at), desc(MealVersionRecord.id))
            .limit(1)
        )
        .first()
    )
    if row is None:
        return None
    thread, version = row
    items = (
        db.execute(
            select(MealItemRecord)
            .where(MealItemRecord.meal_version_id == version.id)
            .order_by(MealItemRecord.item_index.asc(), MealItemRecord.id.asc())
        )
        .scalars()
        .all()
    )
    item_basis = [_item_basis_snapshot(item) for item in items]
    return {
        "meal_thread_id": thread.id,
        "meal_version_id": version.id,
        "meal_title": str(version.meal_title or thread.title or ""),
        "raw_input": str(version.raw_input or ""),
        "version_reason": str(version.version_reason or ""),
        "resolution_status": str(version.resolution_status or ""),
        "source_request_id": version.source_request_id,
        "total_kcal": int(version.total_kcal or 0),
        "macro_summary": {
            "protein_g": int(version.protein_g or 0),
            "carb_g": int(version.carb_g or 0),
            "fat_g": int(version.fat_g or 0),
            "macro_visibility_status": "present"
            if any((version.protein_g, version.carb_g, version.fat_g))
            else "unknown",
        },
        "items": item_basis,
        "truth_owner": "canonical_meal_read_model",
        "read_only": True,
        "mutation_authority": False,
    }


def active_meal_basis_target_candidates(snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return []
    meal_thread_id = snapshot.get("meal_thread_id")
    meal_version_id = snapshot.get("meal_version_id")
    meal_title = snapshot.get("meal_title")
    candidates = [
        {
            "target_object_type": "meal_thread",
            "target_object_id": meal_thread_id,
            "meal_thread_id": meal_thread_id,
            "meal_version_id": meal_version_id,
            "display_name": meal_title,
            "canonical_name": meal_title,
            "estimated_kcal": snapshot.get("total_kcal"),
            "estimate_basis": "active_meal_version_total",
            "source": "canonical_meal_read_model",
            "uniqueness_status": "latest_active_meal",
        }
    ]
    for item in list(snapshot.get("items") or []):
        if not isinstance(item, dict):
            continue
        candidates.append(
            {
                "target_object_type": "meal_item",
                "target_object_id": item.get("meal_item_id"),
                "meal_item_id": item.get("meal_item_id"),
                "meal_thread_id": meal_thread_id,
                "meal_version_id": meal_version_id,
                "display_name": item.get("canonical_name"),
                "canonical_name": item.get("canonical_name"),
                "estimated_kcal": item.get("estimated_kcal"),
                "estimate_basis": item.get("estimate_basis"),
                "confidence_tier": item.get("confidence_tier"),
                "source": item.get("source"),
                "evidence_role": item.get("evidence_role"),
                "uniqueness_status": "active_meal_item",
            }
        )
    return candidates


def _item_basis_snapshot(item: MealItemRecord) -> dict[str, Any]:
    evidence_ids = item.evidence_ids_json if isinstance(item.evidence_ids_json, list) else []
    return {
        "meal_item_id": item.id,
        "item_index": int(item.item_index or 0),
        "canonical_name": str(item.name or ""),
        "quantity_hint": item.quantity_hint,
        "estimated_kcal": int(item.estimated_kcal or 0),
        "estimate_basis": str(item.estimate_basis or ""),
        "confidence_tier": str(item.confidence_tier or ""),
        "source": str(item.source or ""),
        "evidence_role": str(item.evidence_role or ""),
        "protein_g": int(item.protein_g or 0),
        "carb_g": int(item.carb_g or 0),
        "fat_g": int(item.fat_g or 0),
        "evidence_id_count": len(evidence_ids),
        "read_only": True,
        "mutation_authority": False,
    }


__all__ = ["active_meal_basis_target_candidates", "build_active_meal_estimate_basis"]
