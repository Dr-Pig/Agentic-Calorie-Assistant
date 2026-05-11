from __future__ import annotations

from typing import Any

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)


def build_product_lab_exercise_fixture_inputs(mode: str) -> dict[str, Any]:
    payload = build_product_lab_fixture_inputs()
    payload["exercise_current_budget_view"] = {
        "base_budget_kcal": 1400,
        "effective_budget_kcal": 1400,
        "meal_consumption_total_kcal": 800,
    }
    payload["active_body_plan_view"] = {
        **dict(payload["active_body_plan_view"]),
        "current_weight_kg": 56,
        "estimated_tdee": 1900,
    }
    payload["exercise_context"] = _exercise_context(mode)
    return payload


def _exercise_context(mode: str) -> dict[str, Any]:
    if mode == "running_30m_met":
        return {
            "source_refs": ["turn:lab-exercise-turn:user"],
            "semantic_extraction": {
                "decision_mode": "llm_fixture_output",
                "exercise_action": "create_exercise",
                "exercise_type": "running",
                "duration_minutes": 30,
                "calculation_basis": "met_formula",
                "occurred_at_interpretation": "today",
                "raw_user_text_semantic_inference_performed": False,
            },
        }
    if mode == "user_asserted_300":
        return {
            "source_refs": ["turn:lab-exercise-turn:user"],
            "semantic_extraction": {
                "decision_mode": "llm_fixture_output",
                "exercise_action": "create_exercise",
                "exercise_type": "strength_training",
                "duration_minutes": 45,
                "calculation_basis": "user_asserted",
                "user_asserted_kcal": 300,
                "occurred_at_interpretation": "today",
                "raw_user_text_semantic_inference_performed": False,
            },
        }
    if mode == "unknown_exercise":
        return {
            "source_refs": ["turn:lab-exercise-turn:user"],
            "semantic_extraction": {
                "decision_mode": "llm_fixture_output",
                "exercise_action": "cannot_extract",
                "occurred_at_interpretation": "today",
                "raw_user_text_semantic_inference_performed": False,
                "clarification_question": "可以告訴我運動類型和大概多久嗎？",
            },
        }
    raise ValueError(f"unsupported_product_lab_exercise_fixture:{mode}")


__all__ = ["build_product_lab_exercise_fixture_inputs"]
