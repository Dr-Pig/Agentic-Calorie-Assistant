from __future__ import annotations

from sqlalchemy.orm import Session

from app.body.application.body_observation_service import (
    get_active_body_profile_record,
    load_body_observation_history,
    record_body_observation_skeleton,
    record_body_observation_to_canonical,
)
from app.composition.canonical_persistence import (
    CanonicalMealCommitResult,
    CanonicalCommitTarget,
    commit_meal_payload_to_canonical,
    resolve_canonical_commit_target,
    upsert_budget_adjustment_skeleton,
)
from app.budget.infrastructure.models import LedgerEntryRecord
from app.shared.infra.models import User
from app.schemas import CommitRequestCandidate, CommitVersionReason, EstimatePayload, MealItemPayload


def build_commit_request_candidate(
    *,
    payload: EstimatePayload,
    raw_input: str,
    manager_intent: str,
    request_id: str | None,
    meal_thread_id: int | None = None,
    parent_version_id: int | None = None,
    version_reason: CommitVersionReason | None = None,
) -> CommitRequestCandidate:
    items = [
        MealItemPayload(
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
            evidence_ids=list(item.evidence_ids),
            classification={},
        )
        for item in payload.component_estimates
    ]
    if not items:
        items = [
            MealItemPayload(
                name=payload.meal_title or raw_input,
                quantity_hint=(payload.quantity_hints[0] if payload.quantity_hints else None),
                source="llm",
                evidence_role="unknown",
                estimate_basis="llm_only",
                confidence_tier=str(payload.estimate_confidence_tier or "low"),
                estimated_kcal=payload.estimated_kcal,
                protein_g=payload.protein_g,
                carb_g=payload.carb_g,
                fat_g=payload.fat_g,
                evidence_ids=list(payload.evidence_ids_used),
                classification={},
            )
        ]
    trace_contract = payload.trace_contract or {}
    trace_ref = {
        "request_id": request_id or payload.request_id,
        "route_target": payload.route_target,
        "best_answer_source": payload.best_answer_source,
    }
    resolved_meal_thread_id = meal_thread_id
    correction_target_ref = trace_contract.get("correction_target_ref")
    if isinstance(correction_target_ref, dict):
        trace_ref["correction_target_ref"] = dict(correction_target_ref)
        if resolved_meal_thread_id is None and correction_target_ref.get("meal_thread_id") is not None:
            resolved_meal_thread_id = int(correction_target_ref["meal_thread_id"])
    if trace_contract.get("correction_operation") == "remove_item":
        trace_ref["correction_operation"] = "remove_item"
        items = []
    resolved_version_reason = version_reason or (
        "correction" if parent_version_id is not None or "correction_target_ref" in trace_ref else "new_intake"
    )
    return CommitRequestCandidate(
        request_id=request_id or payload.request_id,
        manager_intent=manager_intent,
        meal_thread_id=resolved_meal_thread_id,
        parent_version_id=parent_version_id,
        version_reason=resolved_version_reason,
        meal_title=payload.meal_title or raw_input,
        raw_input=raw_input,
        estimated_kcal=payload.estimated_kcal,
        protein_g=payload.protein_g,
        carb_g=payload.carb_g,
        fat_g=payload.fat_g,
        resolution_status="completed_meal",
        occurred_at=trace_contract.get("occurred_at"),
        local_date=str(trace_contract.get("local_date") or ""),
        items=items,
        trace_ref=trace_ref,
    )


def commit_request_candidate_to_canonical(
    db: Session,
    *,
    user: User,
    candidate: CommitRequestCandidate,
    latest_log_id: int | None = None,
    persisted_log_id: int | None = None,
    budget_kcal: int | None = None,
) -> CanonicalMealCommitResult | None:
    return commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=candidate,
        latest_log_id=latest_log_id,
        persisted_log_id=persisted_log_id,
        budget_kcal=budget_kcal,
    )


def resolve_commit_candidate_target(
    db: Session,
    *,
    candidate: CommitRequestCandidate,
    latest_log_id: int | None = None,
) -> CanonicalCommitTarget:
    return resolve_canonical_commit_target(
        db,
        candidate=candidate,
        latest_log_id=latest_log_id,
    )


def record_budget_adjustment_to_canonical(
    db: Session,
    *,
    user: User,
    delta_kcal: int,
    local_date: str,
    metadata: dict[str, object] | None = None,
) -> LedgerEntryRecord:
    return upsert_budget_adjustment_skeleton(
        db,
        user=user,
        delta_kcal=delta_kcal,
        local_date=local_date,
        metadata=metadata,
    )
