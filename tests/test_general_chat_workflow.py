from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.body.infrastructure.models import BodyObservationRecord, BodyPlanRecord, BodyProfileRecord
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.composition.general_chat_service import build_general_chat_response_pass
from app.models import Base, DayBudgetLedgerRecord, LedgerEntryRecord, MealThreadRecord, MealVersionRecord
from app.schemas import CommitRequestCandidate
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.shared.infra.models import ProposalContainerRecord, ProposalOptionRecord


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _bootstrap_user(db: Session, external_id: str):
    user = get_or_create_user(db, external_id)
    bootstrap = bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=30,
            height_cm=165.0,
            current_weight_kg=58.0,
            activity_level="sedentary",
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            local_date="2026-04-18",
        ),
    )
    return user, bootstrap


def _seed_calibration_history(db: Session, *, external_id: str, local_date: str = "2026-05-14"):
    user = get_or_create_user(db, external_id)
    plan = BodyPlanRecord(
        user_id=user.id,
        plan_status="active",
        plan_label="calibration baseline",
        estimated_tdee=2100,
        daily_budget_kcal=1800,
        safety_floor_kcal=1200,
        target_pace_kg_per_week=0.5,
        metadata_json={"recommended_target_kcal": 1800, "plan_source": "test_baseline", "goal_type": "lose_weight"},
        started_at=datetime(2026, 5, 1, 8, 0, 0),
        created_at=datetime(2026, 5, 1, 8, 0, 0),
    )
    profile = BodyProfileRecord(
        user_id=user.id,
        profile_status="active",
        sex="female",
        age_years=31,
        height_cm=165.0,
        current_weight_kg=70.0,
        activity_level="light",
        goal_type="lose_weight",
        timezone="Asia/Taipei",
        created_at=datetime(2026, 5, 1, 8, 0, 0),
        updated_at=datetime(2026, 5, 1, 8, 0, 0),
    )
    db.add_all([plan, profile])
    db.flush()
    for offset in range(14):
        day = (datetime(2026, 5, 1) + timedelta(days=offset)).date().isoformat()
        thread = MealThreadRecord(
            user_id=user.id,
            title=f"meal {day}",
            thread_kind="text_intake",
            created_at=datetime.fromisoformat(day).replace(hour=12),
            updated_at=datetime.fromisoformat(day).replace(hour=12),
        )
        db.add(thread)
        db.flush()
        version = MealVersionRecord(
            meal_thread_id=thread.id,
            version_status="active",
            version_reason="new_intake",
            meal_title=f"meal {day}",
            raw_input="test meal",
            resolution_status="completed_meal",
            total_kcal=1800,
            protein_g=0,
            carb_g=0,
            fat_g=0,
            occurred_at=datetime.fromisoformat(day).replace(hour=12),
            local_date=day,
            created_at=datetime.fromisoformat(day).replace(hour=13),
        )
        db.add(version)
        db.flush()
        thread.active_version_id = version.id
    for day, value in [
        ("2026-05-01", 70.0),
        ("2026-05-04", 69.7),
        ("2026-05-07", 69.4),
        ("2026-05-10", 69.1),
        ("2026-05-14", 68.8),
    ]:
        observation = BodyObservationRecord(
            user_id=user.id,
            observation_type="weight",
            value=value,
            unit="kg",
            observed_at=datetime.fromisoformat(day).replace(hour=7),
            local_date=day,
            source="manual",
            metadata_json={},
            created_at=datetime.fromisoformat(day).replace(hour=7, minute=5),
        )
        db.add(observation)
    ledger = DayBudgetLedgerRecord(
        user_id=user.id,
        local_date=local_date,
        budget_kcal=1800,
        consumed_kcal=1800,
        adjustment_kcal=0,
        remaining_kcal=0,
    )
    db.add(ledger)
    db.commit()
    return user, plan


def _stored_calibration_action_proposal(
    db: Session,
    *,
    user_id: int,
    local_date: str = "2026-05-14",
    status: str = "open",
    calibration_adjustment_delta_kcal: int | None = -60,
) -> ProposalContainerRecord:
    proposal = ProposalContainerRecord(
        user_id=user_id,
        proposal_type="calibration",
        proposal_status=status,
        metadata_json={"local_date": local_date, "proposal_family": "budget_adjustment"},
    )
    db.add(proposal)
    db.flush()
    effect_payload = {
        "new_daily_budget_kcal": 1650,
        "new_estimated_tdee_kcal": 2050,
        "review_after_days": 14,
        "rationale_summary": "chat action calibration test",
    }
    if calibration_adjustment_delta_kcal is not None:
        effect_payload["calibration_adjustment_delta_kcal"] = calibration_adjustment_delta_kcal
    option = ProposalOptionRecord(
        proposal_container_id=proposal.id,
        option_type="budget_adjustment",
        option_label="Budget adjustment",
        option_summary="Chat action stored proposal option",
        rank_order=0,
        is_primary=True,
        effect_payload_json=effect_payload,
    )
    db.add(option)
    db.flush()
    proposal.top_option_id = option.id
    db.commit()
    db.refresh(proposal)
    return proposal


def test_general_chat_budget_mode_reads_shared_budget_views() -> None:
    db = _session()
    user, bootstrap = _bootstrap_user(db, "general-chat-budget")
    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="general-chat-meal-1",
            manager_intent="food_estimation",
            version_reason="new_intake",
            meal_title="breakfast sandwich",
            raw_input="breakfast sandwich",
            estimated_kcal=420,
            protein_g=18,
            carb_g=32,
            fat_g=14,
            resolution_status="completed_meal",
            local_date="2026-04-18",
        ),
    )
    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="general-chat-meal-2",
            manager_intent="food_estimation",
            version_reason="new_intake",
            meal_title="chicken rice",
            raw_input="chicken rice",
            estimated_kcal=610,
            protein_g=32,
            carb_g=65,
            fat_g=18,
            resolution_status="completed_meal",
            local_date="2026-04-18",
        ),
    )

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-budget",
        raw_user_input="log chicken rice",
        mode="budget_summary",
        local_date="2026-04-18",
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "answer_only"
    assert result.workflow_effect == "answer_budget_summary_without_state_mutation"
    assert result.required_read_surfaces == ["CurrentBudgetView", "ActiveBodyPlanView"]
    assert str(bootstrap.target_result.recommended_target_kcal) in result.reply_text
    assert "1030" in result.reply_text
    assert str(bootstrap.target_result.recommended_target_kcal - 1030) in result.reply_text


def test_general_chat_goal_mode_reads_active_body_plan_view() -> None:
    db = _session()
    _bootstrap_user(db, "general-chat-goal")

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-goal",
        raw_user_input="how many calories are left?",
        mode="goal_summary",
        local_date="2026-04-18",
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "answer_only"
    assert result.workflow_effect == "answer_goal_summary_without_state_mutation"
    assert result.required_read_surfaces == ["ActiveBodyPlanView"]
    assert "lose_weight" in result.reply_text


def test_general_chat_mode_not_raw_text_selects_read_surface() -> None:
    db = _session()
    _bootstrap_user(db, "general-chat-explicit-mode")

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-explicit-mode",
        raw_user_input="how many calories are left?",
        mode="fallback_answer",
        local_date="2026-04-18",
    )

    assert result.disposition == "answer_only"
    assert result.workflow_effect == "answer_general_product_question_without_state_mutation"
    assert result.required_read_surfaces == []


def test_general_chat_has_no_state_mutation_side_effects() -> None:
    db = _session()
    _bootstrap_user(db, "general-chat-no-mutation")
    before_body_plan_count = db.query(BodyPlanRecord).count()
    before_ledger_count = db.query(DayBudgetLedgerRecord).count()
    before_meal_thread_count = db.query(MealThreadRecord).count()

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-no-mutation",
        raw_user_input="any text",
        mode="budget_summary",
        local_date="2026-04-18",
    )

    assert result.disposition == "answer_only"
    assert db.query(BodyPlanRecord).count() == before_body_plan_count
    assert db.query(DayBudgetLedgerRecord).count() == before_ledger_count
    assert db.query(MealThreadRecord).count() == before_meal_thread_count


def test_general_chat_open_workflow_boundary_does_not_silently_enter_intake() -> None:
    db = _session()
    get_or_create_user(db, "general-chat-open-workflow")

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-open-workflow",
        raw_user_input="log chicken rice",
        mode="workflow_handoff",
        local_date="2026-04-18",
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "open_new_workflow"
    assert result.workflow_effect == "handoff_to_formal_workflow"


def test_general_chat_calibration_preview_defaults_to_no_proposal_persistence() -> None:
    db = _session()
    _, baseline_plan = _seed_calibration_history(db, external_id="general-chat-calibration-preview-default")
    before_body_plan_count = db.query(BodyPlanRecord).count()
    before_ledger_count = db.query(DayBudgetLedgerRecord).count()

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-calibration-preview-default",
        raw_user_input="should we adjust my target?",
        mode="calibration_preview",
        local_date="2026-05-14",
    )

    assert result.disposition == "answer_only"
    assert result.workflow_effect == "preview_calibration_proposal_without_plan_mutation"
    assert result.required_read_surfaces == [
        "CalibrationInputAssembly",
        "CurrentBudgetView",
        "ActiveBodyPlanView",
        "CalibrationProposalPolicyPacket",
    ]
    assert result.ui_hints["mode"] == "general_chat_calibration_preview"
    assert result.ui_hints["proposal_surface"] is True
    assert result.ui_hints["proposal_actions_enabled"] is False
    assert result.input_assembly is not None
    assert result.input_assembly["trace"]["window_days"] == 14
    assert result.input_assembly["trace"]["meal_day_count"] == 14
    assert result.input_assembly["trace"]["body_observation_count"] == 5
    assert result.input_assembly["trace"]["raw_body_observation_count"] == 5
    assert result.proposal_artifact is None
    active_plan = db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "active").one()
    assert active_plan.id == baseline_plan.id
    assert db.query(BodyPlanRecord).count() == before_body_plan_count
    assert db.query(DayBudgetLedgerRecord).count() == before_ledger_count
    assert db.query(ProposalContainerRecord).count() == 0


def test_general_chat_calibration_preview_can_persist_open_proposal_without_plan_or_ledger_mutation() -> None:
    db = _session()
    user, baseline_plan = _seed_calibration_history(
        db,
        external_id="general-chat-calibration-preview-persist",
    )
    before_body_plan_count = db.query(BodyPlanRecord).count()
    before_ledger_count = db.query(DayBudgetLedgerRecord).count()

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-calibration-preview-persist",
        raw_user_input="should we adjust my target?",
        mode="calibration_preview",
        local_date="2026-05-14",
        persist_calibration_proposal=True,
    )

    assert result.workflow_effect == "preview_calibration_proposal_without_plan_mutation"
    assert result.ui_hints["proposal_actions_enabled"] is True
    assert result.ui_hints["root_route_activation"] == "active"
    assert result.ui_hints["stored_action_route_contract"] == "/calibration/proposal/stored-action"
    assert result.proposal_response is not None
    assert result.proposal_response["surfaced"] is True
    assert result.proposal_response["proposal_cards"][0]["is_primary"] is True
    assert "reply_text" not in result.proposal_response
    assert "top_option" not in result.proposal_response
    assert "backup_options" not in result.proposal_response
    actions_by_id = {action["action"]: action for action in result.proposal_response["quick_actions"]}
    assert actions_by_id["accept_calibration_proposal"]["requires_proposal_container_id"] is True
    assert actions_by_id["accept_calibration_proposal"]["raw_text_authorized_mutation"] is False
    assert actions_by_id["accept_calibration_proposal"]["enabled"] is True
    assert result.proposal_artifact is not None
    proposal_id = result.proposal_artifact["proposal_container_id"]
    assert actions_by_id["accept_calibration_proposal"]["proposal_container_id"] == proposal_id
    proposal = db.get(ProposalContainerRecord, proposal_id)
    assert proposal is not None
    assert proposal.user_id == user.id
    assert proposal.proposal_type == "calibration"
    assert proposal.proposal_status == "open"
    assert proposal.metadata_json["local_date"] == "2026-05-14"
    active_plan = db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "active").one()
    assert active_plan.id == baseline_plan.id
    assert active_plan.daily_budget_kcal == 1800
    assert db.query(BodyPlanRecord).count() == before_body_plan_count
    assert db.query(DayBudgetLedgerRecord).count() == before_ledger_count


def test_general_chat_calibration_preview_does_not_duplicate_existing_open_proposal() -> None:
    db = _session()
    _seed_calibration_history(
        db,
        external_id="general-chat-calibration-preview-existing-open",
    )

    first = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-calibration-preview-existing-open",
        raw_user_input="should we adjust my target?",
        mode="calibration_preview",
        local_date="2026-05-14",
        persist_calibration_proposal=True,
    )
    second = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-calibration-preview-existing-open",
        raw_user_input="should we adjust my target?",
        mode="calibration_preview",
        local_date="2026-05-14",
        persist_calibration_proposal=True,
    )

    assert first.proposal_artifact is not None
    assert second.proposal_artifact is None
    assert second.ui_hints["proposal_actions_enabled"] is False
    assert db.query(ProposalContainerRecord).count() == 1


def test_general_chat_raw_text_does_not_activate_calibration_preview_without_explicit_mode() -> None:
    db = _session()
    _seed_calibration_history(db, external_id="general-chat-calibration-raw-text")

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-calibration-raw-text",
        raw_user_input="should we adjust my target?",
        mode="fallback_answer",
        local_date="2026-05-14",
        persist_calibration_proposal=True,
    )

    assert result.workflow_effect == "answer_general_product_question_without_state_mutation"
    assert result.input_assembly is None
    assert result.proposal_artifact is None
    assert db.query(ProposalContainerRecord).count() == 0


def test_general_chat_calibration_action_accepts_explicit_stored_proposal_in_chat_surface() -> None:
    db = _session()
    user, _ = _seed_calibration_history(db, external_id="general-chat-calibration-action-accept")
    proposal = _stored_calibration_action_proposal(db, user_id=user.id, calibration_adjustment_delta_kcal=-60)

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-calibration-action-accept",
        raw_user_input="套用這個方案",
        mode="calibration_action",
        local_date="2026-05-14",
        calibration_proposal_container_id=proposal.id,
        calibration_action="accept_calibration_proposal",
        accepted_at=datetime(2026, 5, 14, 10, 30, 0),
    )

    proposal_after = db.get(ProposalContainerRecord, proposal.id)
    entry = db.query(LedgerEntryRecord).one()
    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "answer_only"
    assert result.workflow_effect == "apply_calibration_proposal_action_with_state_mutation"
    assert result.ui_hints["mode"] == "general_chat_calibration_action"
    assert result.ui_hints["proposal_status"] == "accepted"
    assert result.ui_hints["proposal_container_id"] == proposal.id
    assert result.calibration_action_result is not None
    assert result.calibration_action_result["current_budget_view"]["budget_kcal"] == 1650
    assert result.calibration_action_result["current_budget_view"]["adjustment_kcal"] == 60
    assert proposal_after is not None
    assert proposal_after.proposal_status == "accepted"
    assert entry.entry_type == "calibration_adjustment"
    assert entry.delta_kcal == -60


def test_general_chat_calibration_action_rejects_explicit_stored_proposal_without_plan_or_ledger_mutation() -> None:
    db = _session()
    user, baseline_plan = _seed_calibration_history(db, external_id="general-chat-calibration-action-reject")
    proposal = _stored_calibration_action_proposal(db, user_id=user.id, calibration_adjustment_delta_kcal=-60)

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-calibration-action-reject",
        raw_user_input="先維持不變",
        mode="calibration_action",
        local_date="2026-05-14",
        calibration_proposal_container_id=proposal.id,
        calibration_action="reject_calibration_proposal",
        accepted_at=datetime(2026, 5, 14, 10, 30, 0),
    )

    active_plan = db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "active").one()
    proposal_after = db.get(ProposalContainerRecord, proposal.id)
    assert result.workflow_effect == "apply_calibration_proposal_action_without_plan_mutation"
    assert result.ui_hints["proposal_status"] == "rejected"
    assert active_plan.id == baseline_plan.id
    assert proposal_after is not None
    assert proposal_after.proposal_status == "rejected"
    assert db.query(LedgerEntryRecord).count() == 0


def test_general_chat_calibration_action_defer_dismisses_current_proposal_without_plan_or_ledger_mutation() -> None:
    db = _session()
    user, baseline_plan = _seed_calibration_history(db, external_id="general-chat-calibration-action-defer")
    proposal = _stored_calibration_action_proposal(db, user_id=user.id, calibration_adjustment_delta_kcal=-60)

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-calibration-action-defer",
        raw_user_input="decide later",
        mode="calibration_action",
        local_date="2026-05-14",
        calibration_proposal_container_id=proposal.id,
        calibration_action="defer_calibration_proposal",
        accepted_at=datetime(2026, 5, 14, 10, 30, 0),
    )

    active_plan = db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "active").one()
    proposal_after = db.get(ProposalContainerRecord, proposal.id)
    assert result.workflow_effect == "apply_calibration_proposal_action_without_plan_mutation"
    assert result.ui_hints["proposal_status"] == "dismissed"
    assert active_plan.id == baseline_plan.id
    assert proposal_after is not None
    assert proposal_after.proposal_status == "dismissed"
    assert db.query(LedgerEntryRecord).count() == 0


def test_general_chat_calibration_action_requires_explicit_proposal_target() -> None:
    db = _session()
    user, baseline_plan = _seed_calibration_history(db, external_id="general-chat-calibration-action-missing")
    _stored_calibration_action_proposal(db, user_id=user.id, calibration_adjustment_delta_kcal=-60)

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-calibration-action-missing",
        raw_user_input="好",
        mode="calibration_action",
        local_date="2026-05-14",
        calibration_action="accept_calibration_proposal",
        accepted_at=datetime(2026, 5, 14, 10, 30, 0),
    )

    active_plan = db.query(BodyPlanRecord).filter(BodyPlanRecord.plan_status == "active").one()
    assert result.workflow_effect == "calibration_action_unavailable_without_state_mutation"
    assert result.ui_hints["reason"] == "missing_explicit_proposal_container_id_or_action"
    assert active_plan.id == baseline_plan.id
    assert db.query(LedgerEntryRecord).count() == 0
