from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
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
    should_refresh_day_budget_ledger,
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
from .phase_c_transaction_ports import PhaseCUnitOfWorkPort
from app.body.infrastructure.models import BodyObservationRecord
from app.budget.infrastructure.models import LedgerEntryRecord
from app.intake.infrastructure.models import (
    LegacyMealLogMapRecord,
    MealItemRecord,
    MealThreadRecord,
    MealVersionRecord,
)
from app.shared.infra.models import User
from app.schemas import CommitRequestCandidate, CommitVersionReason, EstimatePayload


class _SQLAlchemyPhaseCUnitOfWork(PhaseCUnitOfWorkPort):
    def __init__(self, db: Session) -> None:
        self.db = db

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()


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


def _candidate_with_item_removal_totals(db: Session, candidate: CommitRequestCandidate) -> CommitRequestCandidate:
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


def _item_records_for_candidate(
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
                MealItemRecord(
                    meal_version_id=version_id,
                    item_index=new_index,
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
                for new_index, old_item in enumerate(remaining_items)
            ]
        replacements = list(candidate.items)
        if not replacements:
            raise ValueError("correction_replacement_item_missing")
        records: list[MealItemRecord] = []
        for new_index, old_item in enumerate(old_items):
            if old_item.id == target_item.id:
                records.append(_item_record_from_candidate_item(version_id, new_index, replacements[0]))
            else:
                records.append(
                    MealItemRecord(
                        meal_version_id=version_id,
                        item_index=new_index,
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
                )
        return records
    if source_payload is not None:
        return _item_records_from_payload(version_id, source_payload)
    if candidate.items:
        return [_item_record_from_candidate_item(version_id, index, item) for index, item in enumerate(candidate.items)]
    return [_item_record_from_candidate_summary(version_id, candidate)]


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
    return entry


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
    candidate = _candidate_with_item_removal_totals(db, candidate)

    if candidate.estimated_kcal <= 0:
        return None

    uow = _SQLAlchemyPhaseCUnitOfWork(db)
    try:
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

        for item in _item_records_for_candidate(
            db,
            version_id=version.id,
            candidate=candidate,
            source_payload=source_payload,
        ):
            db.add(item)

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

        if should_refresh_day_budget_ledger(
            db,
            user_id=user.id,
            local_date=local_date,
            explicit_budget_kcal=budget_kcal,
        ):
            recompute_day_budget_ledger(
                db,
                user_id=user.id,
                local_date=local_date,
                budget_kcal=budget_kcal,
                commit=False,
            )
        uow.commit()
        db.refresh(version)
        db.refresh(thread)
        db.refresh(entry)

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
    except BaseException:
        uow.rollback()
        raise
