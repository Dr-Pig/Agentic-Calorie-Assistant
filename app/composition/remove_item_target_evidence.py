"""Remove-item target evidence helpers for intake execution."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.composition.request_runtime_context import load_request_runtime_context
from app.intake.application.target_evidence_artifacts import TargetEvidenceArtifact
from app.intake.infrastructure.models import MealItemRecord
from app.shared.contracts.common import EstimateRequest
from app.shared.contracts.correction_operation import (
    structured_correction_operation,
    structured_payload_requests_remove_item,
)
from app.shared.contracts.correction_target import validate_correction_target_ref
from app.shared.contracts.intake import EstimatePayload


def remove_item_target_evidence_ready(*, manager_payload: dict[str, Any], correction_target: dict[str, Any]) -> bool:
    if str(manager_payload.get("final_action") or "") != "correction_applied":
        return False
    target_operation = structured_correction_operation(correction_target)
    if not structured_payload_requests_remove_item(manager_payload) and target_operation != "remove_item":
        return False
    return validate_correction_target_ref(correction_target).get("resolved") is True


def _remaining_item_totals_after_target_removal(
    db: Session,
    *,
    target_item_id: int | None,
) -> dict[str, Any]:
    if target_item_id is None:
        return {
            "estimated_kcal": 0,
            "protein_g": 0,
            "carb_g": 0,
            "fat_g": 0,
            "remaining_item_names": [],
            "removed_item_name": None,
        }
    target_item = db.get(MealItemRecord, target_item_id)
    if target_item is None:
        return {
            "estimated_kcal": 0,
            "protein_g": 0,
            "carb_g": 0,
            "fat_g": 0,
            "remaining_item_names": [],
            "removed_item_name": None,
        }
    old_items = db.execute(
        select(MealItemRecord)
        .where(MealItemRecord.meal_version_id == target_item.meal_version_id)
        .order_by(MealItemRecord.item_index.asc())
    ).scalars().all()
    remaining_items = [old_item for old_item in old_items if old_item.id != target_item.id]
    return {
        "estimated_kcal": sum(int(item.estimated_kcal or 0) for item in remaining_items),
        "protein_g": sum(int(item.protein_g or 0) for item in remaining_items),
        "carb_g": sum(int(item.carb_g or 0) for item in remaining_items),
        "fat_g": sum(int(item.fat_g or 0) for item in remaining_items),
        "remaining_item_names": [str(item.name or "") for item in remaining_items],
        "removed_item_name": str(target_item.name or ""),
    }


def build_remove_item_target_evidence_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    request_id: str,
    correction_target: dict[str, Any],
    manager_semantic_decision: dict[str, Any],
) -> TargetEvidenceArtifact:
    request = EstimateRequest(text=raw_user_input, allow_search=False, user_id=user_external_id)
    runtime_context = load_request_runtime_context(
        request=request,
        db=db,
        provider=type("TargetEvidenceRemovalProvider", (), {"readiness": lambda self: {"configured": False}})(),
    )
    target_validation = validate_correction_target_ref(correction_target)
    canonical_name = str(target_validation.get("canonical_name") or correction_target.get("canonical_name") or "").strip()
    remaining_totals = _remaining_item_totals_after_target_removal(
        db,
        target_item_id=target_validation.get("meal_item_id"),
    )
    payload = EstimatePayload(
        request_id=request_id,
        meal_title=f"remove {canonical_name}".strip() or "remove item",
        estimated_kcal=int(remaining_totals["estimated_kcal"]),
        protein_g=int(remaining_totals["protein_g"]),
        carb_g=int(remaining_totals["carb_g"]),
        fat_g=int(remaining_totals["fat_g"]),
        source_decision="ready",
        answer_mode="direct_answer",
        action_taken="correction_applied",
        route_target="direct_answer",
        reply_text="Removed the selected item.",
        trace_contract={
            "local_date": local_date,
            "occurred_at": f"{local_date}T12:00:00+08:00",
            "timezone": "Asia/Taipei",
            "correction_operation": "remove_item",
            "correction_operation_source": "manager_structured_decision",
            "correction_target_ref": {
                "meal_thread_id": target_validation.get("meal_thread_id"),
                "meal_item_id": target_validation.get("meal_item_id"),
                "canonical_name": canonical_name,
            },
            "canonical_remaining_item_totals": remaining_totals,
            "target_evidence_contract": {
                "evidence_type": "target_evidence",
                "source": "resolve_correction_target",
                "nutrition_evidence_required": False,
                "nutrition_evidence_present": False,
                "target_evidence_is_nutrition_evidence": False,
                "kcal_source": "canonical_remaining_items",
                "placeholder_kcal_used": False,
                "manager_semantic_decision": dict(manager_semantic_decision or {}),
            },
        },
    )
    return TargetEvidenceArtifact(request=request, runtime_context=runtime_context, payload=payload)
