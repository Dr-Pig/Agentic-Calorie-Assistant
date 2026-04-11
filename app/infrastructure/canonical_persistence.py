from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain import BodyObservation
from ..models import (
    BodyObservationRecord,
    BodyPlanRecord,
    DayBudgetLedgerRecord,
    LedgerEntryRecord,
    LegacyMealLogMapRecord,
    MealItemRecord,
    MealThreadRecord,
    MealVersionRecord,
    ProposalContainerRecord,
    ProposalOptionRecord,
    ProactiveTriggerRecord,
    User,
)
from ..schemas import CommitRequestCandidate, CommitVersionReason, EstimatePayload


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


def _resolved_occurred_at(candidate: CommitRequestCandidate, occurred_at: datetime | None = None) -> datetime:
    chosen = occurred_at or candidate.occurred_at
    if isinstance(chosen, datetime):
        return chosen
    return datetime.now()


def _resolved_local_date(candidate: CommitRequestCandidate, occurred_at: datetime) -> str:
    if isinstance(candidate.local_date, str) and candidate.local_date.strip():
        return candidate.local_date.strip()
    return occurred_at.date().isoformat()


def _resolved_body_observation_time(
    *,
    observed_at: datetime | None = None,
    local_date: str | None = None,
) -> tuple[datetime, str]:
    normalized_observed_at = observed_at or datetime.now()
    normalized_local_date = local_date.strip() if isinstance(local_date, str) and local_date.strip() else normalized_observed_at.date().isoformat()
    return normalized_observed_at, normalized_local_date


def _body_observation_from_record(record: BodyObservationRecord) -> BodyObservation:
    return BodyObservation(
        observation_id=record.id,
        user_id=record.user_id,
        observation_type=record.observation_type,
        value=record.value,
        unit=record.unit,
        observed_at=record.observed_at,
        local_date=record.local_date,
        source=record.source,
        metadata=dict(record.metadata_json or {}),
    )


def _commit_candidate_from_payload(
    *,
    payload: EstimatePayload,
    raw_input: str,
    planner_intent: str,
    request_id: str | None,
) -> CommitRequestCandidate:
    trace_contract = payload.trace_contract or {}
    return CommitRequestCandidate(
        request_id=request_id or payload.request_id,
        planner_intent=planner_intent,
        version_reason="new_intake",
        meal_title=payload.meal_title or raw_input,
        raw_input=raw_input,
        estimated_kcal=payload.estimated_kcal,
        protein_g=payload.protein_g,
        carb_g=payload.carb_g,
        fat_g=payload.fat_g,
        resolution_status="completed_meal",
        occurred_at=trace_contract.get("occurred_at"),
        local_date=str(trace_contract.get("local_date") or ""),
        items=[],
        trace_ref={"request_id": request_id or payload.request_id},
    )


def _legacy_resolved_occurred_at(payload: EstimatePayload, occurred_at: datetime | None = None) -> datetime:
    trace_contract = payload.trace_contract or {}
    candidate = occurred_at or trace_contract.get("occurred_at")
    if isinstance(candidate, datetime):
        return candidate
    return datetime.now()


def _legacy_resolved_local_date(payload: EstimatePayload, occurred_at: datetime) -> str:
    trace_contract = payload.trace_contract or {}
    legacy = trace_contract.get("local_date")
    if isinstance(legacy, str) and legacy.strip():
        return legacy.strip()
    return occurred_at.date().isoformat()


def _item_records_from_payload(version_id: int, payload: EstimatePayload) -> list[MealItemRecord]:
    items: list[MealItemRecord] = []
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
                    protein_g=component.protein_g,
                    carb_g=component.carb_g,
                    fat_g=component.fat_g,
                    evidence_ids_json=list(component.evidence_ids),
                    classification_json={},
                )
            )
    else:
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
                protein_g=payload.protein_g,
                carb_g=payload.carb_g,
                fat_g=payload.fat_g,
                evidence_ids_json=list(payload.evidence_ids_used),
                classification_json={},
            )
        )
    return items


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


def upsert_observation_skeleton(
    db: Session,
    *,
    user: User,
    value: float,
    unit: str = "kg",
    observation_type: str = "weight",
    source: str = "manual",
    observed_at: datetime | None = None,
    local_date: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> BodyObservationRecord:
    normalized_observed_at, normalized_local_date = _resolved_body_observation_time(
        observed_at=observed_at,
        local_date=local_date,
    )
    record = BodyObservationRecord(
        user_id=user.id,
        observation_type=observation_type,
        value=value,
        unit=unit,
        observed_at=normalized_observed_at,
        local_date=normalized_local_date,
        source=source,
        metadata_json=dict(metadata or {}),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def load_body_observations(
    db: Session,
    *,
    user_id: int,
    local_date: str | None = None,
    observation_type: str | None = "weight",
) -> list[BodyObservation]:
    stmt = select(BodyObservationRecord).where(BodyObservationRecord.user_id == user_id)
    if isinstance(observation_type, str) and observation_type.strip():
        stmt = stmt.where(BodyObservationRecord.observation_type == observation_type.strip())
    if isinstance(local_date, str) and local_date.strip():
        stmt = stmt.where(BodyObservationRecord.local_date == local_date.strip())
    rows = db.execute(
        stmt.order_by(BodyObservationRecord.observed_at.asc(), BodyObservationRecord.id.asc())
    ).scalars().all()
    return [_body_observation_from_record(record) for record in rows]


def ensure_body_plan_skeleton(
    db: Session,
    *,
    user: User,
    estimated_tdee: int = 0,
    daily_budget_kcal: int = 0,
    safety_floor_kcal: int = 0,
) -> BodyPlanRecord:
    active = db.execute(
        select(BodyPlanRecord)
        .where(BodyPlanRecord.user_id == user.id, BodyPlanRecord.plan_status == "active")
        .order_by(BodyPlanRecord.id.desc())
    ).scalars().first()
    if active is not None:
        return active
    record = BodyPlanRecord(
        user_id=user.id,
        estimated_tdee=estimated_tdee,
        daily_budget_kcal=daily_budget_kcal,
        safety_floor_kcal=safety_floor_kcal,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def ensure_proposal_skeleton(
    db: Session,
    *,
    user: User,
    proposal_type: str,
    option_type: str,
    option_label: str,
) -> ProposalContainerRecord:
    proposal = ProposalContainerRecord(user_id=user.id, proposal_type=proposal_type)
    db.add(proposal)
    db.flush()
    option = ProposalOptionRecord(
        proposal_container_id=proposal.id,
        option_type=option_type,
        option_label=option_label,
        is_primary=True,
        rank_order=0,
    )
    db.add(option)
    db.flush()
    proposal.top_option_id = option.id
    db.commit()
    db.refresh(proposal)
    return proposal


def ensure_proactive_trigger_skeleton(
    db: Session,
    *,
    user: User,
    trigger_type: str,
) -> ProactiveTriggerRecord:
    record = ProactiveTriggerRecord(user_id=user.id, trigger_type=trigger_type)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def recompute_day_budget_ledger(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    budget_kcal: int = 0,
) -> DayBudgetLedgerRecord:
    ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user_id,
            DayBudgetLedgerRecord.local_date == local_date,
        )
    ).scalar_one_or_none()
    if ledger is None:
        ledger = DayBudgetLedgerRecord(
            user_id=user_id,
            local_date=local_date,
            budget_kcal=budget_kcal,
        )
        db.add(ledger)
        db.flush()
    active_meal_kcal = db.execute(
        select(MealVersionRecord.total_kcal)
        .join(MealThreadRecord, MealThreadRecord.active_version_id == MealVersionRecord.id)
        .where(
            MealThreadRecord.user_id == user_id,
            MealVersionRecord.local_date == local_date,
            MealVersionRecord.version_status == "active",
            MealVersionRecord.resolution_status == "completed_meal",
        )
    ).scalars().all()
    adjustment_deltas = db.execute(
        select(LedgerEntryRecord.delta_kcal).where(
            LedgerEntryRecord.user_id == user_id,
            LedgerEntryRecord.local_date == local_date,
            LedgerEntryRecord.entry_type != "meal_consumption",
        )
    ).scalars().all()
    consumed = sum(delta for delta in active_meal_kcal if delta > 0)
    adjustments = sum(adjustment_deltas)
    ledger.budget_kcal = budget_kcal
    ledger.consumed_kcal = consumed
    ledger.adjustment_kcal = adjustments
    ledger.remaining_kcal = budget_kcal - consumed - adjustments
    ledger.last_recomputed_at = datetime.now()
    db.commit()
    db.refresh(ledger)
    return ledger


def commit_meal_payload_to_canonical(
    db: Session,
    *,
    user: User,
    candidate: CommitRequestCandidate | None = None,
    payload: EstimatePayload | None = None,
    raw_input: str | None = None,
    planner_intent: str | None = None,
    request_id: str | None = None,
    latest_log_id: int | None = None,
    persisted_log_id: int | None = None,
    budget_kcal: int = 0,
) -> CanonicalMealCommitResult | None:
    if candidate is None:
        assert payload is not None
        assert raw_input is not None
        assert planner_intent is not None
        candidate = _commit_candidate_from_payload(
            payload=payload,
            raw_input=raw_input,
            planner_intent=planner_intent,
            request_id=request_id,
        )
    if payload is None:
        assert raw_input is not None or candidate.raw_input
    source_payload = payload

    if candidate.estimated_kcal <= 0:
        return None

    occurred_at = _resolved_occurred_at(candidate)
    local_date = _resolved_local_date(candidate, occurred_at)

    target = resolve_canonical_commit_target(
        db,
        candidate=candidate,
        latest_log_id=latest_log_id,
    )
    thread = db.get(MealThreadRecord, target.meal_thread_id) if target.meal_thread_id is not None else None
    created_new_thread = thread is None
    superseded_version_id = target.superseded_version_id

    if thread is None:
        thread = MealThreadRecord(
            user_id=user.id,
            title=candidate.meal_title or candidate.raw_input,
            thread_kind="text_intake",
            updated_at=datetime.now(),
        )
        db.add(thread)
        db.flush()
    else:
        thread.title = candidate.meal_title or thread.title
        thread.updated_at = datetime.now()

    if superseded_version_id is not None:
        superseded_version = db.get(MealVersionRecord, superseded_version_id)
        if superseded_version is not None:
            superseded_version.version_status = "superseded"
            superseded_version.superseded_at = datetime.now()

    version = MealVersionRecord(
        meal_thread_id=thread.id,
        parent_version_id=target.parent_version_id,
        version_reason=candidate.version_reason,
        reason_payload_json={
            "planner_intent": candidate.planner_intent,
            "route_target": (source_payload.route_target if source_payload is not None else None),
            "request_id": candidate.request_id,
            "version_reason": candidate.version_reason,
            "historical_correction_source_version_id": target.correction_target_version_id,
            "superseded_version_id": superseded_version_id,
            "source_log_id": target.source_log_id,
        },
        meal_title=candidate.meal_title or candidate.raw_input,
        raw_input=candidate.raw_input,
        source_request_id=candidate.request_id,
        planner_intent=candidate.planner_intent,
        resolution_status=candidate.resolution_status,
        total_kcal=candidate.estimated_kcal,
        protein_g=candidate.protein_g,
        carb_g=candidate.carb_g,
        fat_g=candidate.fat_g,
        occurred_at=occurred_at,
        local_date=local_date,
    )
    db.add(version)
    db.flush()

    if source_payload is not None:
        for item in _item_records_from_payload(version.id, source_payload):
            db.add(item)
    else:
        for index, item in enumerate(candidate.items):
            db.add(
                MealItemRecord(
                    meal_version_id=version.id,
                    item_index=index,
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
            )

    thread.active_version_id = version.id
    db.flush()

    source_log_id = persisted_log_id or latest_log_id
    if source_log_id is not None:
        existing_for_source = get_legacy_mapping_for_meal_log(db, source_log_id)
        if existing_for_source is None:
            db.add(
                LegacyMealLogMapRecord(
                    meal_log_id=source_log_id,
                    meal_thread_id=thread.id,
                    meal_version_id=version.id,
                )
            )
        else:
            existing_for_source.meal_thread_id = thread.id
            existing_for_source.meal_version_id = version.id

    entry = LedgerEntryRecord(
        user_id=user.id,
        local_date=local_date,
        entry_type="meal_consumption",
        source_type="meal_version",
        source_id=version.id,
        delta_kcal=candidate.estimated_kcal,
        metadata_json={
            "meal_thread_id": thread.id,
            "meal_title": candidate.meal_title,
            "request_id": candidate.request_id,
        },
        )
    db.add(entry)
    db.flush()
    db.commit()
    db.refresh(version)
    db.refresh(thread)
    db.refresh(entry)

    recompute_day_budget_ledger(db, user_id=user.id, local_date=local_date, budget_kcal=budget_kcal)

    return CanonicalMealCommitResult(
        meal_thread_id=thread.id,
        meal_version_id=version.id,
        active_version_id=thread.active_version_id or version.id,
        local_date=local_date,
        consumed_kcal=candidate.estimated_kcal,
        created_new_thread=created_new_thread,
        superseded_version_id=superseded_version_id,
        ledger_entry_id=entry.id,
    )
