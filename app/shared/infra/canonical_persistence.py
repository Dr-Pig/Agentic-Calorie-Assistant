from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from .canonical_body_support import (
    body_observation_from_record as _body_observation_from_record,
    ensure_body_plan_skeleton,
    load_active_body_plan_record,
    load_active_body_profile_record,
    load_body_observations,
    recompute_day_budget_ledger,
    resolve_active_budget_kcal,
    resolved_body_observation_time as _resolved_body_observation_time,
    upsert_observation_skeleton,
)
from .canonical_commit_support import (
    CanonicalCommitTarget,
    CanonicalMealCommitResult,
    commit_candidate_from_payload as _commit_candidate_from_payload,
    get_legacy_mapping_for_meal_log,
    legacy_resolved_local_date as _legacy_resolved_local_date,
    legacy_resolved_occurred_at as _legacy_resolved_occurred_at,
    load_active_meal_version,
    resolve_canonical_commit_target,
    resolved_local_date as _resolved_local_date,
    resolved_occurred_at as _resolved_occurred_at,
)
from .canonical_proposal_support import (
    ensure_proactive_trigger_skeleton,
    ensure_proposal_artifact_skeleton,
    ensure_proposal_skeleton,
)
from app.models import (
    BodyObservationRecord,
    LedgerEntryRecord,
    LegacyMealLogMapRecord,
    MealItemRecord,
    MealThreadRecord,
    MealVersionRecord,
    User,
)
from app.schemas import CommitRequestCandidate, CommitVersionReason, EstimatePayload


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


def upsert_budget_adjustment_skeleton(
    db: Session,
    *,
    user: User,
    delta_kcal: int,
    local_date: str,
    metadata: dict[str, Any] | None = None,
) -> LedgerEntryRecord:
    entry = LedgerEntryRecord(
        user_id=user.id,
        local_date=local_date,
        entry_type="manual_adjustment",
        source_type="manual",
        source_id=0,
        delta_kcal=delta_kcal,
        metadata_json=dict(metadata or {}),
    )
    db.add(entry)
    db.flush()
    db.commit()
    db.refresh(entry)
    recompute_day_budget_ledger(db, user_id=user.id, local_date=local_date)
    return record


def commit_meal_payload_to_canonical(
    db: Session,
    *,
    user: User,
    candidate: CommitRequestCandidate | None = None,
    payload: EstimatePayload | None = None,
    raw_input: str | None = None,
    manager_intent: str | None = None,
    request_id: str | None = None,
    latest_log_id: int | None = None,
    persisted_log_id: int | None = None,
    budget_kcal: int | None = None,
) -> CanonicalMealCommitResult | None:
    if candidate is None:
        assert payload is not None
        assert raw_input is not None
        assert manager_intent is not None
        candidate = _commit_candidate_from_payload(
            payload=payload,
            raw_input=raw_input,
            manager_intent=manager_intent,
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
            "manager_intent": candidate.manager_intent,
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
        manager_intent=candidate.manager_intent,
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
