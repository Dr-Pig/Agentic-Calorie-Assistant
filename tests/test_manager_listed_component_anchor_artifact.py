from __future__ import annotations

from app.nutrition.application.local_component_stub_catalog import (
    optional_refinement_for_manager_listed_items,
)


def test_manager_listed_component_red_tea_exposes_modifier_refinement_as_evidence_metadata() -> None:
    refinement = optional_refinement_for_manager_listed_items(["鐵板麵", "紅茶"])

    assert refinement == {
        "optional_refinement_allowed": True,
        "optional_refinement_targets": ["紅茶"],
        "optional_refinement_question": "如果紅茶的糖度或杯型不同，可以補充，我會幫你修正。",
    }
