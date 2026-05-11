from __future__ import annotations

from typing import Any

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)


def build_product_lab_weekly_insight_fixture_inputs(
    *, mode: str = "enough_coverage"
) -> dict[str, Any]:
    fixture = build_product_lab_fixture_inputs()
    fixture["weekly_insight_fixture_payload"] = _weekly_payload(mode)
    fixture["user_control_models"] = {
        **dict(fixture.get("user_control_models") or {}),
        "weekly_insight": _controls("new_weekly_insight_window"),
    }
    return fixture


def _weekly_payload(mode: str) -> dict[str, Any]:
    meal_logs = _meal_logs(7 if mode != "low_coverage" else 2)
    return {
        "fixture_input_used": True,
        "real_dogfood_export_used": False,
        "user_id": "fixture-user",
        "week_id": "2026-W19",
        "week_start_date": "2026-05-04",
        "week_end_date": "2026-05-10",
        "generated_at": "2026-05-11T08:00:00+08:00",
        "meal_logs": meal_logs,
        "body_observations": [
            {
                "trace_id": "body-week-start",
                "observed_at": "2026-05-04T07:30:00+08:00",
                "weight_kg": 56.4,
            },
            {
                "trace_id": "body-week-end",
                "observed_at": "2026-05-10T07:35:00+08:00",
                "weight_kg": 56.1,
            },
        ],
        "budget_summaries": _budget_summaries(),
        "swap_opportunities": [
            {
                "opportunity_id": "swap-drink-1",
                "summary": "Swap one sweet drink for unsweetened tea on heavy days.",
                "estimated_delta_kcal": -120,
                "source_refs": ["meal_log:meal-2026-05-07"],
            }
        ],
    }


def _meal_logs(count: int) -> list[dict[str, Any]]:
    days = ["04", "05", "06", "07", "08", "09", "10"]
    sources = ["lunch", "snack", "drink", "dinner", "lunch", "dinner", "drink"]
    kcal = [520, 180, 240, 760, 610, 680, 220]
    return [
        {
            "trace_id": f"meal-2026-05-{day}",
            "meal_id": f"m-{day}",
            "logged_at": f"2026-05-{day}T12:15:00+08:00",
            "item_names": [f"fixture item {index + 1}"],
            "calorie_source": sources[index],
            "estimated_kcal": kcal[index],
        }
        for index, day in enumerate(days[:count])
    ]


def _budget_summaries() -> list[dict[str, Any]]:
    actuals = [1700, 1780, 1750, 2100, 1690, 1810, 1750]
    return [
        {
            "trace_id": f"budget-2026-05-{day}",
            "date": f"2026-05-{day}",
            "target_kcal": 1800,
            "actual_kcal": actual,
            "overshoot_kcal": max(0, actual - 1800),
        }
        for day, actual in zip(["04", "05", "06", "07", "08", "09", "10"], actuals)
    ]


def _controls(next_signal: str) -> dict[str, Any]:
    return {
        "dismiss_reason_choices": [
            "not_relevant_now",
            "already_handled",
            "too_frequent",
        ],
        "snooze_window": {"kind": "duration", "minutes": 1440},
        "undo_scope": "candidate_instance",
        "next_signal_required": next_signal,
    }


__all__ = ["build_product_lab_weekly_insight_fixture_inputs"]
