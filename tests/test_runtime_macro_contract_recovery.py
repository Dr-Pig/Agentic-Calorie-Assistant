from __future__ import annotations

from app.composition.payload_macro_summary import build_payload_macro_summary
from app.composition.intake_manager_tool_batch import macro_summary
from app.composition.payload_builders import build_payload
from app.shared.contracts.intake_results import EstimatePayload
from app.runtime.application.execution_guard import evaluate_macro_display
from app.schemas import EstimateRequest


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
