from __future__ import annotations

from typing import Any

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_planned_event_fixture_inputs,
)


def build_product_lab_planned_event_all_day_fixture_inputs() -> dict[str, Any]:
    fixture = build_product_lab_planned_event_fixture_inputs()
    fixture["planned_event_guidance_context"] = {
        "event_id": "event-company-dinner-1",
        "event_label": "company dinner",
        "event_local_date": "2026-05-11",
        "remaining_kcal": 1200,
        "suggested_reserve_kcal": 600,
        "lunch_cap_kcal": 400,
        "source_refs": ["planned_event:event-company-dinner-1"],
    }
    return fixture


__all__ = ["build_product_lab_planned_event_all_day_fixture_inputs"]
