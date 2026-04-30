from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from ...shared.domain import BodyObservation
from app.shared.infra.canonical_persistence import (
    CanonicalMealCommitResult,
    CanonicalCommitTarget,
    commit_meal_payload_to_canonical,
    load_body_observations,
    resolve_canonical_commit_target,
    upsert_observation_skeleton,
    upsert_budget_adjustment_skeleton,
    load_active_body_profile_record,
)
from ...models import BodyProfileRecord, LedgerEntryRecord, User
from ...schemas import CommitRequestCandidate, CommitVersionReason, EstimatePayload, MealItemPayload


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
    return CommitRequestCandidate(
        request_id=request_id or payload.request_id,
        manager_intent=manager_intent,
        meal_thread_id=meal_thread_id,
        parent_version_id=parent_version_id,
        version_reason=version_reason or ("correction" if parent_version_id is not None else "new_intake"),
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
        trace_ref={
            "request_id": request_id or payload.request_id,
            "route_target": payload.route_target,
            "best_answer_source": payload.best_answer_source,
        },
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


def record_body_observation_skeleton(
    db: Session,
    *,
    user: User,
    value: float,
    unit: str = "kg",
    observation_type: str = "weight",
    source: str = "manual",
    observed_at: datetime | None = None,
    local_date: str | None = None,
    metadata: dict[str, object] | None = None,
) -> int:
    observation = upsert_observation_skeleton(
        db,
        user=user,
        value=value,
        unit=unit,
        observation_type=observation_type,
        source=source,
        observed_at=observed_at,
        local_date=local_date,
        metadata=metadata,
    )
    return observation.id


def record_body_observation_to_canonical(
    db: Session,
    *,
    user: User,
    value: float,
    unit: str = "kg",
    observation_type: str = "weight",
    source: str = "manual",
    observed_at: datetime | None = None,
    local_date: str | None = None,
    metadata: dict[str, object] | None = None,
) -> BodyObservation:
    observation = upsert_observation_skeleton(
        db,
        user=user,
        value=value,
        unit=unit,
        observation_type=observation_type,
        source=source,
        observed_at=observed_at,
        local_date=local_date,
        metadata=metadata,
    )
    return BodyObservation(
        observation_id=observation.id,
        user_id=observation.user_id,
        observation_type=observation.observation_type,
        value=observation.value,
        unit=observation.unit,
        observed_at=observation.observed_at,
        local_date=observation.local_date,
        source=observation.source,
        metadata=dict(observation.metadata_json or {}),
    )


def load_body_observation_history(
    db: Session,
    *,
    user_id: int,
    local_date: str | None = None,
    observation_type: str | None = "weight",
) -> list[BodyObservation]:
    return load_body_observations(
        db,
        user_id=user_id,
        local_date=local_date,
        observation_type=observation_type,
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


def get_active_body_profile_record(
    db: Session,
    *,
    user_id: int,
) -> BodyProfileRecord | None:
    return load_active_body_profile_record(db, user_id=user_id)
