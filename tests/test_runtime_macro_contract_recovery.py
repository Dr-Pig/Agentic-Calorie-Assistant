from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.composition.payload_macro_summary import build_payload_macro_summary
from app.composition.current_budget_read_model import build_current_budget_view
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.intake_manager_tool_batch import macro_summary
from app.composition.payload_builders import build_payload
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealItemRecord
from app.models import Base
from app.shared.contracts.intake_results import EstimatePayload
from app.runtime.application.execution_guard import evaluate_macro_display
from app.schemas import EstimateRequest


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _parsed(**overrides: object) -> dict[str, object]:
    parsed: dict[str, object] = {
        "title": "pearl milk tea",
        "components": ["milk tea", "pearls"],
        "protein_g": 3,
        "carb_g": 80,
        "fat_g": 8,
        "estimated_kcal": 450,
        "uncertainty_factors": ["size and sugar unknown"],
        "followup_question": "What size and sugar level was it?",
        "follow_up_needed": True,
        "response_mode_hint": "rough_estimate_ok",
        "unresolved_info": [],
        "blocking_slots": [],
    }
    parsed.update(overrides)
    return parsed


def _payload(**parsed_overrides: object):
    return build_payload(
        EstimateRequest(text="I had a pearl milk tea"),
        request_id="req-macro-contract",
        parsed=_parsed(**parsed_overrides),
        risk_packet={},
        action_taken="answer_with_uncertainty",
        route_target="direct_answer",
        route_reason="manager_estimate_with_refinement",
        debug_steps=[],
        llm_traces=[],
        retrieval_triggered=False,
        retrieval_query=None,
        retrieved_knowledge=[],
        quality_signals={},
        retry_triggered=False,
        retry_reason=None,
        best_answer_source="llm",
        private_only=False,
        used_search=False,
        search_query=None,
        search_quality=None,
        sources=[],
    )


def test_payload_does_not_surface_llm_hint_macro_breakdown_without_explicit_display_payload() -> None:
    payload = _payload()

    assert payload.protein_g == 3
    assert payload.carb_g == 80
    assert payload.fat_g == 8
    assert payload.raw_macro_breakdown == {}
    assert payload.macro_breakdown == {}
    assert payload.display_macro_breakdown == {}


def test_macro_summary_hides_payload_macros_without_display_macro_breakdown() -> None:
    payload = _payload()

    summary = macro_summary(payload)

    assert summary["display_status"] == "hide"
    assert summary["guard_reason"] == "no_macro_data"
    assert summary["macro_kcal_delta"] == 0


def test_macro_summary_keeps_direct_payload_macro_compatibility_when_not_explicitly_suppressed() -> None:
    payload = EstimatePayload(
        request_id="req-direct-payload",
        meal_title="exact item",
        estimated_kcal=90,
        protein_g=6,
        carb_g=1,
        fat_g=5,
        action_taken="direct_answer",
        route_target="direct_answer",
        source_decision="ready",
        answer_mode="direct_answer",
        trace_contract={},
    )

    summary = build_payload_macro_summary(payload)

    assert summary["display_status"] == "show"
    assert summary["guard_reason"] == "committed_and_aligned"
    assert summary["protein_g"] == 6
    assert summary["carbs_g"] == 1
    assert summary["fat_g"] == 5


def test_macro_summary_hides_shadow_stub_macro_numbers() -> None:
    payload = EstimatePayload(
        request_id="req-shadow-stub",
        meal_title="breakfast shop combo",
        estimated_kcal=400,
        protein_g=18,
        carb_g=42,
        fat_g=12,
        action_taken="direct_answer",
        route_target="direct_answer",
        source_decision="ready",
        answer_mode="direct_answer",
        trace_contract={"shadow_stub": True},
    )

    summary = build_payload_macro_summary(payload)

    assert summary["display_status"] == "hide"
    assert summary["guard_reason"] == "no_macro_data"
    assert summary["macro_kcal_delta"] == 0


def test_macro_summary_uses_explicit_display_macro_breakdown_when_present() -> None:
    payload = _payload(
        answer_payload={
            "display_macro_breakdown": {
                "protein_g": 20,
                "carb_g": 50,
                "fat_g": 18,
                "macro_source": "derived_consistent",
            }
        }
    )

    summary = macro_summary(payload)

    assert summary["display_status"] == "show"
    assert summary["guard_reason"] == "committed_and_aligned"
    assert summary["protein_g"] == 20
    assert summary["carbs_g"] == 50
    assert summary["fat_g"] == 18


def test_commit_does_not_promote_hidden_payload_macro_hint_to_current_budget_truth() -> None:
    db = _session()
    user = get_or_create_user(db, "macro-hidden-commit-boundary")
    payload = _payload(
        protein_g=20,
        carb_g=50,
        fat_g=18,
        estimated_kcal=450,
        follow_up_needed=False,
        followup_question="",
        uncertainty_factors=[],
        component_breakdown=[
            {"name": "milk tea", "estimated_kcal": 270, "protein_g": 15, "carb_g": 35, "fat_g": 12},
            {"name": "pearls", "estimated_kcal": 180, "protein_g": 5, "carb_g": 15, "fat_g": 6},
        ],
    )
    payload.trace_contract["local_date"] = "2026-05-09"

    commit_meal_payload_to_canonical(
        db,
        user=user,
        payload=payload,
        raw_input="I had a pearl milk tea",
        manager_intent="food_estimation",
        request_id=payload.request_id,
        budget_kcal=1200,
    )

    current_budget = build_current_budget_view(db, user_id=user.id, local_date="2026-05-09")

    assert current_budget.consumed_kcal == 450
    assert current_budget.consumed_protein == 0
    assert current_budget.consumed_carbs == 0
    assert current_budget.consumed_fat == 0
    assert current_budget.show_macro is False
    assert current_budget.macro_guard_reason == "no_macro_data"
    item_rows = db.query(MealItemRecord).order_by(MealItemRecord.item_index.asc()).all()
    assert [(item.protein_g, item.carb_g, item.fat_g) for item in item_rows] == [(0, 0, 0), (0, 0, 0)]


def test_commit_promotes_explicit_display_macro_breakdown_to_current_budget_truth() -> None:
    db = _session()
    user = get_or_create_user(db, "macro-authorized-commit-boundary")
    payload = _payload(
        protein_g=3,
        carb_g=80,
        fat_g=8,
        estimated_kcal=450,
        follow_up_needed=False,
        followup_question="",
        uncertainty_factors=[],
        answer_payload={
            "display_macro_breakdown": {
                "protein_g": 20,
                "carb_g": 50,
                "fat_g": 18,
                "macro_source": "display_authorized_evidence",
            }
        },
    )
    payload.trace_contract["local_date"] = "2026-05-09"

    commit_meal_payload_to_canonical(
        db,
        user=user,
        payload=payload,
        raw_input="I had a pearl milk tea",
        manager_intent="food_estimation",
        request_id=payload.request_id,
        budget_kcal=1200,
    )

    current_budget = build_current_budget_view(db, user_id=user.id, local_date="2026-05-09")

    assert current_budget.consumed_kcal == 450
    assert current_budget.consumed_protein == 20
    assert current_budget.consumed_carbs == 50
    assert current_budget.consumed_fat == 18
    assert current_budget.show_macro is True
    assert current_budget.macro_guard_reason == "committed_and_aligned"


def test_evaluate_macro_display_uses_canonical_guard_reason_names() -> None:
    missing = evaluate_macro_display(
        estimated_kcal=0,
        protein_g=0,
        carb_g=0,
        fat_g=0,
    )
    aligned = evaluate_macro_display(
        estimated_kcal=450,
        protein_g=20,
        carb_g=50,
        fat_g=18,
    )
    misaligned = evaluate_macro_display(
        estimated_kcal=450,
        protein_g=3,
        carb_g=20,
        fat_g=4,
    )

    assert missing.display_status == "hide"
    assert missing.guard_reason == "no_macro_data"
    assert aligned.display_status == "show"
    assert aligned.guard_reason == "committed_and_aligned"
    assert misaligned.display_status == "hide"
    assert misaligned.guard_reason == "macro_alignment_fail"
