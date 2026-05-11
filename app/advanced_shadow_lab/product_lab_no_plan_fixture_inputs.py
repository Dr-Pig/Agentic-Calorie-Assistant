from __future__ import annotations

from typing import Any

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)


def build_product_lab_no_plan_fixture_inputs() -> dict[str, Any]:
    return {
        **build_product_lab_fixture_inputs(),
        "no_plan_current_budget_view": {
            "user_id": 1,
            "local_date": "2026-05-14",
            "budget_kcal": 0,
            "consumed_kcal": 650,
            "remaining_kcal": 0,
            "active_meal_count": 1,
        },
        "no_plan_active_body_plan_view": {
            "body_plan_id": None,
            "user_id": 1,
            "plan_status": "inactive",
            "daily_budget_kcal": 0,
            "recommended_target_kcal": 0,
            "profile_status": "missing",
        },
        "no_plan_intake_fixture": {
            "meal_title": "beef noodle soup",
            "estimated_kcal": 650,
            "source_refs": ["fixture:no_plan_beef_noodle"],
        },
    }


__all__ = ["build_product_lab_no_plan_fixture_inputs"]
