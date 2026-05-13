from __future__ import annotations

from typing import Any, Mapping


FORBIDDEN_PLANNING_OUTPUT_FIELDS = {
    "allowed_candidate_ids",
    "qualified_candidates",
    "selected_primary",
    "backup_candidates",
    "ranking_result",
}
DESIRED_SOURCE_TYPES = [
    "memory_golden_order",
    "golden_order",
    "nearby_fixture",
    "safe_fallback",
]


class FixtureRecommendationPlanningProvider:
    provider_name = "fixture_recommendation_planning_llm"

    def __init__(self, *, model_profile: str) -> None:
        self.model_profile = model_profile

    def plan(
        self,
        *,
        turn: Mapping[str, Any],
        fixture_inputs: Mapping[str, Any],
        memory_context_pack: Mapping[str, Any],
        pre_meal_planning: Mapping[str, Any] | None = None,
        swap_suggestion: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = _mapping(fixture_inputs.get("recommendation_payload"))
        selected_refs = [
            str(record_id)
            for record_id in memory_context_pack.get("selected_record_ids") or []
        ]
        premeal = _mapping(pre_meal_planning)
        swap = _mapping(swap_suggestion)
        artifact = {
            "artifact_type": "recommendation_planning_fixture_output",
            "artifact_schema_version": "1.0",
            "node": "recommendation_planning",
            "owner": "llm_fixture_provider",
            "decision_mode": "llm_fixture",
            "model_profile": self.model_profile,
            "recommendation_context_result": {
                "user_goal": _user_goal(turn=turn, premeal=premeal, swap=swap),
                "soft_preferences": selected_refs,
                "budget_posture": {
                    "remaining_kcal": _remaining_kcal(payload),
                    "already_logged_kcal": _already_logged_kcal(fixture_inputs),
                },
                "pre_meal_planning": premeal,
                "swap_suggestion": swap,
                "raw_user_text_semantic_inference_performed": False,
            },
            "candidate_spec": {
                "desired_source_types": list(DESIRED_SOURCE_TYPES),
                "memory_record_refs": selected_refs,
                "budget_posture": {
                    "remaining_kcal": _remaining_kcal(payload),
                    "max_candidate_kcal": _remaining_kcal(payload),
                },
                "pre_meal_planning": premeal,
                "swap_suggestion": swap,
                "hard_blockers_must_be_deterministic": True,
            },
        }
        artifact["blockers"] = planning_fixture_output_blockers(artifact)
        return artifact


def planning_fixture_output_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers = [
        f"planning_output.forbidden_field:{field}"
        for field in sorted(FORBIDDEN_PLANNING_OUTPUT_FIELDS)
        if field in artifact
    ]
    context = _mapping(artifact.get("recommendation_context_result"))
    spec = _mapping(artifact.get("candidate_spec"))
    if not str(context.get("user_goal") or ""):
        blockers.append("recommendation_context_result.user_goal_missing")
    if not spec.get("desired_source_types"):
        blockers.append("candidate_spec.desired_source_types_missing")
    return blockers


def _remaining_kcal(payload: Mapping[str, Any]) -> int | None:
    value = _mapping(payload.get("current_budget_view")).get("remaining_kcal")
    return value if isinstance(value, int) else None


def _already_logged_kcal(fixture_inputs: Mapping[str, Any]) -> int | None:
    value = _mapping(fixture_inputs.get("current_budget_view")).get(
        "meal_consumption_total_kcal"
    )
    return value if isinstance(value, int) else None


def _user_goal(
    *,
    turn: Mapping[str, Any],
    premeal: Mapping[str, Any],
    swap: Mapping[str, Any],
) -> str:
    if premeal:
        return "pre_meal_planning"
    if swap:
        return "swap_suggestion"
    return str(turn.get("semantic_intent_fixture") or "")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "FixtureRecommendationPlanningProvider",
    "planning_fixture_output_blockers",
]
