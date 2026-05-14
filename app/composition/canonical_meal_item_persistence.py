from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.composition.canonical_commit_support import (
    canonical_macro_values_from_payload,
    payload_authorizes_macro_persistence,
)
from app.intake.infrastructure.models import MealItemRecord, MealVersionRecord
from app.schemas import CommitRequestCandidate, EstimatePayload


def _item_records_from_payload(version_id: int, payload: EstimatePayload) -> list[MealItemRecord]:
    items: list[MealItemRecord] = []
    macro_persistence_allowed = payload_authorizes_macro_persistence(payload)
    if payload.component_estimates:
        for index, component in enumerate(payload.component_estimates):
            items.append(
                MealItemRecord(
                    meal_version_id=version_id,
                    item_index=index,
                    name=component.name,
                    quantity_hint=component.quantity_hint,
                    source=component.source,
                    evidence_role=component.evidence_role,
                    estimate_basis=component.estimate_basis,
                    confidence_tier=component.confidence_tier,
                    estimated_kcal=component.estimated_kcal,
                    protein_g=component.protein_g if macro_persistence_allowed else 0,
                    carb_g=component.carb_g if macro_persistence_allowed else 0,
                    fat_g=component.fat_g if macro_persistence_allowed else 0,
                    evidence_ids_json=list(component.evidence_ids),
                    classification_json={},
                )
            )
    else:
        protein_g, carb_g, fat_g = canonical_macro_values_from_payload(payload)
        items.append(
            MealItemRecord(
                meal_version_id=version_id,
                item_index=0,
                name=payload.meal_title or "meal",
                quantity_hint=(payload.quantity_hints[0] if payload.quantity_hints else None),
                source="llm",
                evidence_role="unknown",
                estimate_basis="llm_only",
                confidence_tier=str(payload.estimate_confidence_tier or "low"),
                estimated_kcal=payload.estimated_kcal,
                protein_g=protein_g,
                carb_g=carb_g,
                fat_g=fat_g,
                evidence_ids_json=list(payload.evidence_ids_used),
                classification_json={},
            )
        )
    return items


def _item_record_from_candidate_item(version_id: int, item_index: int, item: Any) -> MealItemRecord:
    return MealItemRecord(
        meal_version_id=version_id,
        item_index=item_index,
        name=item.name,
        quantity_hint=item.quantity_hint,
        source=item.source,
        evidence_role=item.evidence_role,
        estimate_basis=item.estimate_basis,
        confidence_tier=item.confidence_tier,
        estimated_kcal=item.estimated_kcal,
        protein_g=item.protein_g,
        carb_g=item.carb_g,
        fat_g=item.fat_g,
        evidence_ids_json=list(item.evidence_ids),
        classification_json=dict(item.classification),
    )


def _item_record_from_candidate_summary(version_id: int, candidate: CommitRequestCandidate) -> MealItemRecord:
    return MealItemRecord(
        meal_version_id=version_id,
        item_index=0,
        name=candidate.meal_title or candidate.raw_input or "meal",
        quantity_hint=None,
        source="llm",
        evidence_role="unknown",
        estimate_basis="llm_only",
        confidence_tier="low",
        estimated_kcal=candidate.estimated_kcal,
        protein_g=candidate.protein_g,
        carb_g=candidate.carb_g,
        fat_g=candidate.fat_g,
        evidence_ids_json=[],
        classification_json={},
    )


def _correction_target_ref(candidate: CommitRequestCandidate) -> dict[str, Any]:
    raw = dict(candidate.trace_ref or {}).get("correction_target_ref")
    return dict(raw) if isinstance(raw, dict) else {}


def _is_item_removal_correction(candidate: CommitRequestCandidate) -> bool:
    return dict(candidate.trace_ref or {}).get("correction_operation") == "remove_item"


def candidate_with_item_removal_totals(db: Session, candidate: CommitRequestCandidate) -> CommitRequestCandidate:
    if not _is_item_removal_correction(candidate):
        return candidate
    target_ref = _correction_target_ref(candidate)
    target_item_id = target_ref.get("meal_item_id")
    if target_item_id is None:
        return candidate
    target_item = db.get(MealItemRecord, target_item_id)
    if target_item is None:
        return candidate
    old_items = db.execute(
        select(MealItemRecord)
        .where(MealItemRecord.meal_version_id == target_item.meal_version_id)
        .order_by(MealItemRecord.item_index.asc())
    ).scalars().all()
    remaining_items = [old_item for old_item in old_items if old_item.id != target_item.id]
    if not remaining_items:
        return candidate
    return candidate.model_copy(
        update={
            "estimated_kcal": sum(int(item.estimated_kcal or 0) for item in remaining_items),
            "protein_g": sum(int(item.protein_g or 0) for item in remaining_items),
            "carb_g": sum(int(item.carb_g or 0) for item in remaining_items),
            "fat_g": sum(int(item.fat_g or 0) for item in remaining_items),
            "items": [],
        }
    )


def _item_record_from_existing_item(
    version_id: int,
    item_index: int,
    old_item: MealItemRecord,
) -> MealItemRecord:
    return MealItemRecord(
        meal_version_id=version_id,
        item_index=item_index,
        name=old_item.name,
        quantity_hint=old_item.quantity_hint,
        source=old_item.source,
        evidence_role=old_item.evidence_role,
        estimate_basis=old_item.estimate_basis,
        confidence_tier=old_item.confidence_tier,
        estimated_kcal=old_item.estimated_kcal,
        protein_g=old_item.protein_g,
        carb_g=old_item.carb_g,
        fat_g=old_item.fat_g,
        evidence_ids_json=list(old_item.evidence_ids_json or []),
        classification_json=dict(old_item.classification_json or {}),
    )


def item_records_for_candidate(
    db: Session,
    *,
    version_id: int,
    candidate: CommitRequestCandidate,
    source_payload: EstimatePayload | None,
) -> list[MealItemRecord]:
    target_ref = _correction_target_ref(candidate)
    target_item_id = target_ref.get("meal_item_id")
    if candidate.version_reason in {"correction", "historical_correction"} and target_item_id is None:
        raise ValueError("correction_requires_explicit_item_target")
    if candidate.version_reason in {"correction", "historical_correction"} and target_item_id is not None:
        target_item = db.get(MealItemRecord, target_item_id)
        if target_item is None:
            raise ValueError("correction_target_item_missing")
        target_version = db.get(MealVersionRecord, target_item.meal_version_id)
        if target_version is None or target_version.meal_thread_id != candidate.meal_thread_id:
            raise ValueError("correction_target_item_thread_mismatch")
        expected_name = str(target_ref.get("canonical_name") or "").strip()
        if expected_name and expected_name.casefold() != str(target_item.name or "").strip().casefold():
            raise ValueError("correction_canonical_name_mismatch")
        old_items = db.execute(
            select(MealItemRecord)
            .where(MealItemRecord.meal_version_id == target_item.meal_version_id)
            .order_by(MealItemRecord.item_index.asc())
        ).scalars().all()
        if _is_item_removal_correction(candidate):
            remaining_items = [old_item for old_item in old_items if old_item.id != target_item.id]
            if not remaining_items:
                raise ValueError("item_removal_cannot_empty_meal_thread")
            return [
                _item_record_from_existing_item(version_id, new_index, old_item)
                for new_index, old_item in enumerate(remaining_items)
            ]
        replacements = list(candidate.items)
        if not replacements:
            raise ValueError("correction_replacement_item_missing")
        records: list[MealItemRecord] = []
        new_index = 0
        for old_item in old_items:
            if old_item.id == target_item.id:
                for replacement in replacements:
                    records.append(_item_record_from_candidate_item(version_id, new_index, replacement))
                    new_index += 1
            else:
                records.append(_item_record_from_existing_item(version_id, new_index, old_item))
                new_index += 1
        return records
    if source_payload is not None:
        return _item_records_from_payload(version_id, source_payload)
    if candidate.items:
        return [_item_record_from_candidate_item(version_id, index, item) for index, item in enumerate(candidate.items)]
    return [_item_record_from_candidate_summary(version_id, candidate)]
