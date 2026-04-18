from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from ..domain import BodyObservation
from ..infrastructure.canonical_persistence import (
    CanonicalMealCommitResult,
    CanonicalCommitTarget,
    commit_meal_payload_to_canonical,
    ensure_proposal_artifact_skeleton,
    ensure_body_plan_skeleton,
    ensure_proactive_trigger_skeleton,
    ensure_proposal_skeleton,
    load_body_observations,
    recompute_day_budget_ledger,
    resolve_canonical_commit_target,
    upsert_observation_skeleton,
    upsert_budget_adjustment_skeleton,
    load_active_body_profile_record,
)
from ..models import LedgerEntryRecord, User, BodyProfileRecord
from ..schemas import CommitRequestCandidate, CommitVersionReason, EstimatePayload, MealItemPayload


def build_commit_request_candidate(
    *,
    payload: EstimatePayload,
    raw_input: str,
    planner_intent: str,
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
        planner_intent=planner_intent,
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


def apply_rescue_overlay_skeleton(
    db: Session,
    *,
    user: User,
    local_date: str,
    delta_kcal: int,
    source_id: int | None = None,
    source_type: str = "rescue_plan",
    budget_kcal: int | None = None,
    metadata: dict[str, object] | None = None,
) -> LedgerEntryRecord:
    entry = LedgerEntryRecord(
        user_id=user.id,
        local_date=local_date,
        entry_type="rescue_overlay",
        source_type=source_type,
        source_id=source_id,
        delta_kcal=delta_kcal,
        metadata_json=dict(metadata or {}),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    recompute_day_budget_ledger(db, user_id=user.id, local_date=local_date, budget_kcal=budget_kcal)
    return entry


def apply_proposal_acceptance_skeleton(
    db: Session,
    *,
    user: User,
    proposal_type: str,
    option_type: str,
    option_label: str,
    estimated_tdee: int = 0,
    daily_budget_kcal: int = 0,
    safety_floor_kcal: int = 0,
) -> dict[str, int | None]:
    proposal = ensure_proposal_skeleton(
        db,
        user=user,
        proposal_type=proposal_type,
        option_type=option_type,
        option_label=option_label,
    )
    proposal.proposal_status = "accepted"
    proposal.accepted_at = datetime.now()
    body_plan = ensure_body_plan_skeleton(
        db,
        user=user,
        estimated_tdee=estimated_tdee,
        daily_budget_kcal=daily_budget_kcal,
        safety_floor_kcal=safety_floor_kcal,
    )
    body_plan.estimated_tdee = estimated_tdee or body_plan.estimated_tdee
    body_plan.daily_budget_kcal = daily_budget_kcal or body_plan.daily_budget_kcal
    body_plan.safety_floor_kcal = safety_floor_kcal or body_plan.safety_floor_kcal
    db.commit()
    db.refresh(proposal)
    db.refresh(body_plan)
    return {
        "proposal_container_id": proposal.id,
        "body_plan_id": body_plan.id,
        "top_option_id": proposal.top_option_id,
    }


def persist_proposal_artifact_skeleton(
    db: Session,
    *,
    user: User,
    proposal_type: str,
    options: list[dict[str, object]],
    metadata: dict[str, object] | None = None,
) -> dict[str, int | None]:
    proposal = ensure_proposal_artifact_skeleton(
        db,
        user=user,
        proposal_type=proposal_type,
        options=options,
        metadata=metadata,
    )
    return {
        "proposal_container_id": proposal.id,
        "top_option_id": proposal.top_option_id,
        "option_count": len(proposal.options),
    }


def apply_proposal_decision_skeleton(
    db: Session,
    *,
    proposal_container_id: int,
    decision: str,
    metadata_patch: dict[str, object] | None = None,
) -> dict[str, object]:
    from ..models import ProposalContainerRecord

    proposal = db.get(ProposalContainerRecord, proposal_container_id)
    if proposal is None:
        raise ValueError(f"proposal_container_id={proposal_container_id} not found")

    if decision not in {"accepted", "rejected", "deferred_pending_reminder", "closed_expired"}:
        raise ValueError(f"unsupported proposal decision: {decision}")

    proposal.proposal_status = decision
    if decision == "accepted":
        proposal.accepted_at = datetime.now()

    merged_metadata = dict(proposal.metadata_json or {})
    merged_metadata.update(metadata_patch or {})
    proposal.metadata_json = merged_metadata
    db.commit()
    db.refresh(proposal)
    return {
        "proposal_container_id": proposal.id,
        "proposal_status": proposal.proposal_status,
        "top_option_id": proposal.top_option_id,
        "metadata": dict(proposal.metadata_json or {}),
    }


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


def record_proactive_trigger_skeleton(
    db: Session,
    *,
    user: User,
    trigger_type: str,
) -> int:
    trigger = ensure_proactive_trigger_skeleton(db, user=user, trigger_type=trigger_type)
    return trigger.id
