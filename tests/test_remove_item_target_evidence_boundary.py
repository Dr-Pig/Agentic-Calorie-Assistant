from __future__ import annotations

from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.budget.infrastructure.models import DayBudgetLedgerRecord
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.remove_item_target_evidence import build_remove_item_target_evidence_artifact
from app.composition.intake_manager_tool_batch import nutrition_tool_output
from app.composition.intake_persistence_tools import persist_meal_log_tool
from app.database import get_or_create_user
from app.intake.application.target_evidence_artifacts import TargetEvidenceArtifact
from app.intake.infrastructure.models import MealItemRecord, MealVersionRecord
from app.models import Base
from app.nutrition.application.estimate_artifacts import EstimatedNutritionArtifact
from app.runtime.agent.founder_live_manager_contract import founder_live_manager_contract_constraints
from app.schemas import CommitRequestCandidate, MealItemPayload
from app.shared.infra.models import MealLog


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _initial_candidate() -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="remove-target-evidence-initial",
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title="chicken rice and soup",
        raw_input="chicken rice and soup",
        estimated_kcal=650,
        protein_g=35,
        carb_g=70,
        fat_g=18,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=[
            MealItemPayload(name="chicken rice", estimated_kcal=500, protein_g=32, carb_g=65, fat_g=15),
            MealItemPayload(name="soup", estimated_kcal=150, protein_g=3, carb_g=5, fat_g=3),
        ],
    )


def _items_for_version(db: Session, version_id: int) -> list[MealItemRecord]:
    return db.execute(
        select(MealItemRecord)
        .where(MealItemRecord.meal_version_id == version_id)
        .order_by(MealItemRecord.item_index.asc())
    ).scalars().all()


def _seed_two_item_meal(db: Session) -> tuple[int, MealItemRecord]:
    user = get_or_create_user(db, "remove-target-evidence-user")
    initial = commit_meal_payload_to_canonical(db, user=user, candidate=_initial_candidate(), budget_kcal=1800)
    assert initial is not None
    soup = next(item for item in _items_for_version(db, initial.meal_version_id) if item.name == "soup")
    return initial.meal_thread_id, soup


def _resolved_target(*, meal_thread_id: int, item: MealItemRecord) -> dict[str, object]:
    return {
        "meal_thread_id": meal_thread_id,
        "meal_item_id": item.id,
        "canonical_name": item.name,
        "observed_canonical_name": item.name,
        "target_resolution_source": "manager_target_proposal_validated",
    }


def test_remove_item_target_evidence_uses_non_nutrition_artifact_and_canonical_remaining_totals() -> None:
    db = _session()
    meal_thread_id, soup = _seed_two_item_meal(db)

    artifact = build_remove_item_target_evidence_artifact(
        db,
        user_external_id="remove-target-evidence-user",
        raw_user_input="remove soup",
        local_date="2026-05-02",
        request_id="remove-target-evidence-turn",
        correction_target=_resolved_target(meal_thread_id=meal_thread_id, item=soup),
        manager_semantic_decision={
            "current_turn_intent": "correct_meal",
            "final_action_candidate": "correction_applied",
            "target_attachment": {"operation": "remove_item", "canonical_name": "soup"},
        },
    )

    assert isinstance(artifact, TargetEvidenceArtifact)
    assert not isinstance(artifact, EstimatedNutritionArtifact)
    assert artifact.payload.estimated_kcal == 500
    assert artifact.payload.protein_g == 32
    assert artifact.payload.trace_contract["target_evidence_contract"] == {
        "evidence_type": "target_evidence",
        "source": "resolve_correction_target",
        "nutrition_evidence_required": False,
        "nutrition_evidence_present": False,
        "target_evidence_is_nutrition_evidence": False,
        "kcal_source": "canonical_remaining_items",
        "placeholder_kcal_used": False,
        "manager_semantic_decision": {
            "current_turn_intent": "correct_meal",
            "final_action_candidate": "correction_applied",
            "target_attachment": {"operation": "remove_item", "canonical_name": "soup"},
        },
    }
    assert artifact.payload.trace_contract["canonical_remaining_item_totals"] == {
        "estimated_kcal": 500,
        "protein_g": 32,
        "carb_g": 65,
        "fat_g": 15,
        "remaining_item_names": ["chicken rice"],
        "removed_item_name": "soup",
    }


def test_remove_item_target_evidence_persistence_does_not_use_placeholder_kcal_for_legacy_or_canonical_truth() -> None:
    db = _session()
    meal_thread_id, soup = _seed_two_item_meal(db)
    artifact = build_remove_item_target_evidence_artifact(
        db,
        user_external_id="remove-target-evidence-user",
        raw_user_input="remove soup",
        local_date="2026-05-02",
        request_id="remove-target-evidence-turn",
        correction_target=_resolved_target(meal_thread_id=meal_thread_id, item=soup),
        manager_semantic_decision={
            "current_turn_intent": "correct_meal",
            "final_action_candidate": "correction_applied",
            "target_attachment": {"operation": "remove_item", "canonical_name": "soup"},
        },
    )

    result = persist_meal_log_tool(
        db,
        artifact=artifact,
        request_id="remove-target-evidence-turn",
        final_action="correction_applied",
        manager_semantic_decision={"current_turn_intent": "correct_meal"},
    )

    assert result.canonical_commit is not None
    assert result.canonical_commit["consumed_kcal"] == 500
    persisted_log = db.get(MealLog, result.persisted_log_id)
    assert persisted_log is not None
    assert persisted_log.kcal == 500
    active_version = db.get(MealVersionRecord, result.canonical_commit["meal_version_id"])
    assert active_version is not None
    assert active_version.total_kcal == 500
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
    assert ledger.consumed_kcal == 500


def test_remove_item_target_evidence_tool_output_cannot_be_counted_as_nutrition_payload() -> None:
    db = _session()
    meal_thread_id, soup = _seed_two_item_meal(db)
    target = _resolved_target(meal_thread_id=meal_thread_id, item=soup)
    artifact = build_remove_item_target_evidence_artifact(
        db,
        user_external_id="remove-target-evidence-user",
        raw_user_input="remove soup",
        local_date="2026-05-02",
        request_id="remove-target-evidence-turn",
        correction_target=target,
        manager_semantic_decision={
            "current_turn_intent": "correct_meal",
            "final_action_candidate": "correction_applied",
            "target_attachment": {"operation": "remove_item", "canonical_name": "soup"},
        },
    )

    output = nutrition_tool_output(
        raw_user_input="remove soup",
        nutrition_artifact=artifact,
        correction_target=target,
        budget_summary=None,
    )

    assert output["tool_name"] == "estimate_nutrition"
    assert output["evidence"]["nutrition_payload"] is None
    assert output["evidence"]["target_evidence_payload"] == {
        "evidence_type": "target_evidence",
        "source": "resolve_correction_target",
        "operation": "remove_item",
        "nutrition_evidence_present": False,
        "target_evidence_is_nutrition_evidence": False,
        "canonical_remaining_item_totals": {
            "estimated_kcal": 500,
            "protein_g": 32,
            "carb_g": 65,
            "fat_g": 15,
            "remaining_item_names": ["chicken rice"],
            "removed_item_name": "soup",
        },
    }

    constraints = founder_live_manager_contract_constraints(
        "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
        tool_results=[output],
    )
    assert constraints["manager_contract_evidence_state"]["nutrition_evidence_present"] is False
