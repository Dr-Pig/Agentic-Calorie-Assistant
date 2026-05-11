from __future__ import annotations

from typing import Any, Mapping

from app.body.application.exercise_estimator import estimate_exercise_kcal
from app.body.contracts.exercise_event import ExerciseEstimateInput


def estimate_exercise_packet(
    extraction: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    return estimate_exercise_kcal(
        _estimate_input(extraction, fixture_inputs)
    ).model_dump(mode="json")


def build_lab_exercise_event(
    extraction: Mapping[str, Any],
    estimate: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    exercise_type = str(extraction.get("exercise_type") or "")
    duration = int(float(extraction.get("duration_minutes") or 0))
    return {
        "event_id": f"lab-exercise:{exercise_type}:{duration}",
        "exercise_type": exercise_type,
        "duration_minutes": duration,
        "estimated_kcal_burned": int(estimate.get("estimated_kcal") or 0),
        "calculation_basis": str(estimate.get("estimation_basis") or ""),
        "occurred_at_interpretation": str(
            extraction.get("occurred_at_interpretation") or ""
        ),
        "source_refs": [str(ref) for ref in context.get("source_refs") or []],
        "lab_local_only": True,
        "canonical_persistence_requested": False,
    }


def build_lab_exercise_ledger_entry(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ledger_entry_id": f"lab-ledger:{event.get('event_id') or ''}",
        "ledger_entry_type": "exercise_bonus",
        "source_event_id": str(event.get("event_id") or ""),
        "delta_kcal": int(event.get("estimated_kcal_burned") or 0),
        "lab_local_only": True,
        "canonical_persistence_requested": False,
    }


def build_lab_exercise_today_projection(
    fixture_inputs: Mapping[str, Any],
    exercise_bonus_kcal: int,
) -> dict[str, int]:
    budget = _mapping(
        fixture_inputs.get("exercise_current_budget_view")
        or fixture_inputs.get("current_budget_view")
    )
    base = _int(budget.get("base_budget_kcal"))
    previous_effective = _int(budget.get("effective_budget_kcal")) or base
    consumed = _int(budget.get("meal_consumption_total_kcal"))
    projected_effective = previous_effective + exercise_bonus_kcal
    return {
        "base_budget_kcal": base,
        "previous_effective_budget_kcal": previous_effective,
        "exercise_bonus_total_kcal": exercise_bonus_kcal,
        "projected_effective_budget_kcal": projected_effective,
        "meal_consumption_total_kcal": consumed,
        "projected_remaining_kcal": projected_effective - consumed,
    }


def build_lab_exercise_chat_reply(
    event: Mapping[str, Any],
    projection: Mapping[str, int],
) -> dict[str, Any]:
    exercise_label = _exercise_label(str(event.get("exercise_type") or ""))
    duration = int(event.get("duration_minutes") or 0)
    kcal = int(event.get("estimated_kcal_burned") or 0)
    effective = int(projection.get("projected_effective_budget_kcal") or 0)
    remaining = int(projection.get("projected_remaining_kcal") or 0)
    return {
        "message_kind": "exercise_budget_confirmation",
        "copy": (
            f"{exercise_label} {duration} \u5206\u9418\u6d88\u8017\u7d04 {kcal} kcal\uff0c"
            f"\u4eca\u5929\u6709\u6548\u9810\u7b97\u8abf\u6574\u70ba {effective} kcal\uff0c"
            f"\u9084\u5269\u7d04 {remaining} kcal\u3002"
        ),
        "canonical_commit_requested": False,
    }


def _estimate_input(
    extraction: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
) -> ExerciseEstimateInput:
    basis = str(extraction.get("calculation_basis") or "met_formula")
    duration = float(extraction.get("duration_minutes") or 0)
    exercise_type = str(extraction.get("exercise_type") or "other")
    if basis == "user_asserted":
        return ExerciseEstimateInput(
            exercise_type=exercise_type,  # type: ignore[arg-type]
            duration_minutes=duration,
            estimation_basis="user_asserted",
            user_asserted_kcal=int(extraction.get("user_asserted_kcal") or 0),
        )
    return ExerciseEstimateInput(
        exercise_type=exercise_type,  # type: ignore[arg-type]
        duration_minutes=duration,
        body_weight_kg=_body_weight_kg(fixture_inputs),
        estimation_basis="met_formula",
    )


def _body_weight_kg(fixture_inputs: Mapping[str, Any]) -> float:
    body = _mapping(fixture_inputs.get("active_body_plan_view"))
    return float(body.get("current_weight_kg") or 70)


def _exercise_label(exercise_type: str) -> str:
    return {
        "running": "\u8dd1\u6b65",
        "walking": "\u8d70\u8def",
        "cycling": "\u9a0e\u8eca",
        "strength_training": "\u91cd\u8a13",
    }.get(exercise_type, "\u904b\u52d5")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = [
    "build_lab_exercise_chat_reply",
    "build_lab_exercise_event",
    "build_lab_exercise_ledger_entry",
    "build_lab_exercise_today_projection",
    "estimate_exercise_packet",
]
