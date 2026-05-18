from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.intake.infrastructure.models import MealItemRecord, MealThreadRecord, MealVersionRecord
from app.runtime.application.execution_guard import evaluate_macro_display
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
    macro_summary = _macro_summary_snapshot(version, item_basis)
    return {
        "meal_thread_id": thread.id,
        "meal_version_id": version.id,
        "meal_title": str(version.meal_title or thread.title or ""),
        "raw_input": str(version.raw_input or ""),
        "version_reason": str(version.version_reason or ""),
        "resolution_status": str(version.resolution_status or ""),
        "source_request_id": version.source_request_id,
        "total_kcal": int(version.total_kcal or 0),
        "macro_summary": macro_summary,
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
    macro_snapshot = _item_macro_snapshot(item, evidence_ids=evidence_ids)
    return {
        "meal_item_id": item.id,
        "item_index": int(item.item_index or 0),
        "canonical_name": str(item.name or ""),
        "quantity_hint": item.quantity_hint,
        "estimated_kcal": int(item.estimated_kcal or 0),
        "estimate_basis": _context_estimate_basis(item),
        "confidence_tier": str(item.confidence_tier or ""),
        "source": _context_source(item),
        "evidence_role": str(item.evidence_role or ""),
        **macro_snapshot,
        "evidence_id_count": len(evidence_ids),
        "read_only": True,
        "mutation_authority": False,
    }


def _item_macro_snapshot(item: MealItemRecord, *, evidence_ids: list[Any]) -> dict[str, Any]:
    has_macro_values = any((item.protein_g, item.carb_g, item.fat_g))
    if not has_macro_values:
        return _hidden_macro_snapshot("no_macro_data")
    if not evidence_ids:
        return _hidden_macro_snapshot("unsupported_macro_source")
    display = evaluate_macro_display(
        estimated_kcal=int(item.estimated_kcal or 0),
        protein_g=int(item.protein_g or 0),
        carb_g=int(item.carb_g or 0),
        fat_g=int(item.fat_g or 0),
    )
    if display.display_status != "show":
        return _hidden_macro_snapshot(
            display.guard_reason,
            macro_kcal=display.macro_kcal,
            macro_kcal_delta=display.macro_kcal_delta,
        )
    return {
        "protein_g": int(item.protein_g or 0),
        "carb_g": int(item.carb_g or 0),
        "fat_g": int(item.fat_g or 0),
        "macro_visibility_status": "visible",
        "macro_display_status": "show",
        "macro_guard_reason": display.guard_reason,
        "macro_kcal": display.macro_kcal,
        "macro_kcal_delta": display.macro_kcal_delta,
        "macro_source_basis": "canonical_item_evidence",
    }


def _hidden_macro_snapshot(
    reason: str,
    *,
    macro_kcal: int = 0,
    macro_kcal_delta: int = 0,
) -> dict[str, Any]:
    return {
        "protein_g": None,
        "carb_g": None,
        "fat_g": None,
        "macro_visibility_status": "hidden_missing_source",
        "macro_display_status": "hide",
        "macro_guard_reason": reason,
        "macro_kcal": macro_kcal,
        "macro_kcal_delta": macro_kcal_delta,
        "macro_source_basis": "unavailable",
    }


def _context_estimate_basis(item: MealItemRecord) -> str:
    estimate_basis = str(item.estimate_basis or "")
    source = str(item.source or "")
    if estimate_basis in {"llm_only", "llm_hint"} or source in {"llm", "llm_hint"}:
        return "rough_estimate_without_source"
    return estimate_basis


def _context_source(item: MealItemRecord) -> str:
    source = str(item.source or "")
    if source in {"llm", "llm_hint"}:
        return "unverified_estimate"
    return source


def _macro_summary_snapshot(version: MealVersionRecord, item_basis: list[dict[str, Any]]) -> dict[str, Any]:
    has_macro_values = any((version.protein_g, version.carb_g, version.fat_g))
    if not has_macro_values:
        return {
            "protein_g": None,
            "carb_g": None,
            "fat_g": None,
            "macro_visibility_status": "unknown",
            "macro_guard_reason": "no_macro_data",
            "macro_display_status": "hide",
            "macro_kcal": 0,
            "macro_kcal_delta": 0,
            "macro_source_basis": "unavailable",
        }
    if not any(item.get("macro_visibility_status") == "visible" for item in item_basis):
        failed_item_reasons = {
            str(item.get("macro_guard_reason") or "")
            for item in item_basis
            if isinstance(item, dict)
        }
        if "macro_alignment_fail" in failed_item_reasons:
            display = evaluate_macro_display(
                estimated_kcal=int(version.total_kcal or 0),
                protein_g=int(version.protein_g or 0),
                carb_g=int(version.carb_g or 0),
                fat_g=int(version.fat_g or 0),
            )
            return {
                "protein_g": None,
                "carb_g": None,
                "fat_g": None,
                "macro_visibility_status": "hidden_missing_source",
                "macro_guard_reason": "macro_alignment_fail",
                "macro_display_status": "hide",
                "macro_kcal": display.macro_kcal,
                "macro_kcal_delta": display.macro_kcal_delta,
                "macro_source_basis": "canonical_item_evidence",
            }
        return {
            "protein_g": None,
            "carb_g": None,
            "fat_g": None,
            "macro_visibility_status": "hidden_missing_source",
            "macro_guard_reason": "unsupported_macro_source",
            "macro_display_status": "hide",
            "macro_kcal": 0,
            "macro_kcal_delta": 0,
            "macro_source_basis": "unavailable",
        }
    display = evaluate_macro_display(
        estimated_kcal=int(version.total_kcal or 0),
        protein_g=int(version.protein_g or 0),
        carb_g=int(version.carb_g or 0),
        fat_g=int(version.fat_g or 0),
    )
    if display.display_status != "show":
        return {
            "protein_g": None,
            "carb_g": None,
            "fat_g": None,
            "macro_visibility_status": "hidden_missing_source",
            "macro_guard_reason": display.guard_reason,
            "macro_display_status": "hide",
            "macro_kcal": display.macro_kcal,
            "macro_kcal_delta": display.macro_kcal_delta,
            "macro_source_basis": "canonical_item_evidence",
        }
    return {
        "protein_g": int(version.protein_g or 0),
        "carb_g": int(version.carb_g or 0),
        "fat_g": int(version.fat_g or 0),
        "macro_visibility_status": "present",
        "macro_guard_reason": display.guard_reason,
        "macro_display_status": "show",
        "macro_kcal": display.macro_kcal,
        "macro_kcal_delta": display.macro_kcal_delta,
        "macro_source_basis": "canonical_item_evidence",
    }


__all__ = ["active_meal_basis_target_candidates", "build_active_meal_estimate_basis"]
