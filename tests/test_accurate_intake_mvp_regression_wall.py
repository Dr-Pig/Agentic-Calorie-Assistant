from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.state_resolver import resolve_intake_state
from app.database import get_or_create_user
from app.intake.application.context_injection_policy import build_manager_context_pack
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.phase_c_same_truth_gate import build_phase_c_same_truth_gate
from app.models import Base
from app.schemas import CommitRequestCandidate, MealItemPayload


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _state(
    *,
    pending_followup: dict[str, object] | None = None,
    recent_committed_meals: list[dict[str, object]] | None = None,
    target_meal_reference: dict[str, object] | None = None,
    current_budget: dict[str, object] | None = None,
    active_body_plan: dict[str, object] | None = None,
    session_summary: dict[str, object] | None = None,
) -> object:
    return SimpleNamespace(
        user_external_id="mvp-user",
        user_id=1,
        local_date="2026-05-02",
        conversation_state=None,
        injected_context={
            "ACTIVE_MEAL": None,
            "PENDING_FOLLOWUP": pending_followup
            if pending_followup is not None
            else {"is_open": False, "meal_thread_id": None, "pending_question": None},
            "RECENT_COMMITTED_MEALS_SUMMARY": recent_committed_meals or [],
            "TARGET_MEAL_REFERENCE": target_meal_reference
            if target_meal_reference is not None
            else {
                "meal_thread_id": None,
                "meal_version_id": None,
                "meal_title": None,
                "target_resolution_source": "none",
                "correction_confidence": "low",
            },
            "CURRENT_BUDGET": current_budget
            if current_budget is not None
            else {
                "local_date": "2026-05-02",
                "budget_kcal": 0,
                "consumed_kcal": 0,
                "remaining_kcal": 0,
                "active_meal_count": 0,
                "has_active_plan": False,
                "has_day_budget_ledger": False,
                "no_plan_posture": "onboarding_required",
                "freshness_status": "current_turn",
            },
            "ACTIVE_BODY_PLAN": active_body_plan
            if active_body_plan is not None
            else {"body_plan_id": None, "goal_type": None, "daily_budget_kcal": 0},
            "SESSION_SUMMARY": session_summary or {},
        },
    )


def test_new_meal_followup_context_attaches_completion_to_same_meal_thread() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="高麗菜、豆皮、甜不辣、王子麵",
        resolved_state=_state(
            pending_followup={
                "is_open": True,
                "meal_thread_id": 77,
                "pending_question": "滷味有哪些品項?",
            },
            target_meal_reference={
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_title": "晚餐滷味",
                "target_resolution_source": "pending_followup_state",
                "correction_confidence": "high",
            },
            session_summary={"latest_assistant_turns": ["滷味有哪些品項?"]},
        ),
    )
    pack = build_manager_context_pack(current_turn_context=context)

    assert context.open_workflow_type == "meal_followup"
    assert context.candidate_attachment_targets == [
        {
            "target_object_type": "meal_thread",
            "target_object_id": "77",
            "source": "pending_followup",
            "confidence": "high",
            "mutation_authority": False,
        }
    ]
    assert "session_atomic_blocks" in pack.manager_context
    assert pack.manager_context["session_atomic_blocks"][0]["role"] == "support_evidence"


def test_drink_refinement_promotes_single_item_target_without_mutation_authority() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="半糖大杯",
        resolved_state=_state(
            recent_committed_meals=[
                {
                    "meal_thread_id": 50,
                    "meal_version_id": 60,
                    "meal_title": "珍珠奶茶",
                    "item_resolution_source": "single_active_item",
                    "meal_item_id": 70,
                    "canonical_name": "珍珠奶茶",
                }
            ],
            target_meal_reference={
                "meal_thread_id": 50,
                "meal_version_id": 60,
                "meal_item_id": 70,
                "canonical_name": "珍珠奶茶",
                "meal_title": "珍珠奶茶",
                "target_resolution_source": "active_meal_view",
                "correction_confidence": "medium",
                "item_resolution_source": "single_active_item",
            },
        ),
    )
    pack = build_manager_context_pack(current_turn_context=context)

    assert context.open_workflow_type == "meal_correction"
    assert pack.manager_context["recent_item_targets"] == [
        {
            "target_object_type": "meal_item",
            "meal_thread_id": 50,
            "meal_version_id": 60,
            "meal_item_id": 70,
            "canonical_name": "珍珠奶茶",
            "source": "active_meal_view",
            "confidence": "medium",
            "item_resolution_source": "single_active_item",
        }
    ]
    assert pack.manager_context["target_resolution_posture"]["mutation_authority"] is False


def test_multi_item_recent_meal_exposes_candidates_and_ambiguity_without_selected_target() -> None:
    db = _session()
    user = get_or_create_user(db, "mvp-multi-item-context")
    commit_meal_payload_to_canonical(
        db,
        user=user,
        budget_kcal=1800,
        candidate=CommitRequestCandidate(
            request_id="mvp-multi-item",
            manager_intent="food_estimation",
            version_reason="new_intake",
            meal_title="滷味",
            raw_input="滷味高麗菜豆皮",
            estimated_kcal=450,
            resolution_status="completed_meal",
            local_date="2026-05-02",
            items=[
                MealItemPayload(name="高麗菜", estimated_kcal=80),
                MealItemPayload(name="豆皮", estimated_kcal=180),
                MealItemPayload(name="王子麵", estimated_kcal=190),
            ],
        ),
    )

    resolved = resolve_intake_state(
        db,
        user_external_id="mvp-multi-item-context",
        local_date="2026-05-02",
        incoming_user_text="改少一點",
    )
    context = build_current_turn_context_v1(raw_user_input="改少一點", resolved_state=resolved)

    assert context.target_resolution_posture["item_resolution_source"] == "ambiguous_active_items"
    assert context.target_resolution_posture["mutation_authority"] is False
    assert {target["target_object_type"] for target in context.recent_item_targets} == {"meal_item_candidate"}
    assert all(target["selected_target"] is False for target in context.recent_item_targets)
    assert all(target["mutation_authority"] is False for target in context.recent_item_targets)


def test_budget_query_and_no_plan_context_preserve_truth_posture_without_fake_remaining_claim() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="今天還能吃多少?",
        resolved_state=_state(
            current_budget={
                "local_date": "2026-05-02",
                "budget_kcal": 0,
                "consumed_kcal": 0,
                "remaining_kcal": 0,
                "active_meal_count": 1,
                "has_active_plan": False,
                "has_day_budget_ledger": False,
                "no_plan_posture": "onboarding_required",
                "freshness_status": "current_turn",
            },
        ),
    )
    pack = build_manager_context_pack(current_turn_context=context, promotion_mode="budget_query")

    assert pack.manager_context["current_budget_snapshot"]["has_active_plan"] is False
    assert pack.manager_context["current_budget_snapshot"]["has_day_budget_ledger"] is False
    assert pack.manager_context["current_budget_snapshot"]["no_plan_posture"] == "onboarding_required"
    assert pack.manager_context["current_budget_snapshot"]["remaining_kcal"] == 0
    assert "active_body_plan_snapshot" in pack.manager_context


def test_stale_read_model_contradiction_is_hard_fail_diagnostic_not_repair() -> None:
    gate = build_phase_c_same_truth_gate(
        phase_c_trace={
            "mutation_outcome": {
                "canonical_commit_status": "committed",
                "ledger_mutation_status": "updated",
                "canonical_ids": {"meal_thread_id": 10, "meal_version_id": 20},
            },
            "same_truth_read_result": {
                "owner_alignment": "aligned",
                "consistency_flags": [],
                "compared_surfaces": ["persistence_result"],
            },
        },
        persistence_result=SimpleNamespace(canonical_commit={"meal_thread_id": 10, "meal_version_id": 20}),
        state_delta={"canonical_commit": True, "ledger_updated": True},
        sidecar={"state_mutation_summary": {"canonical_commit": True, "ledger_updated": True}},
        state_after=SimpleNamespace(
            current_budget_view=SimpleNamespace(
                model_dump=lambda *, mode="json": {
                    "consumed_kcal": 900,
                    "remaining_kcal": 900,
                    "meals": [{"meal_thread_id": 10, "meal_version_id": 99, "total_kcal": 900}],
                }
            )
        ),
        budget_summary={"predicted_consumed_kcal_after": 900, "predicted_remaining_kcal_after": 900},
    )

    assert gate["status"] == "hard_fail"
    assert "canonical_active_version_mismatch" in gate["consistency_flags"]
