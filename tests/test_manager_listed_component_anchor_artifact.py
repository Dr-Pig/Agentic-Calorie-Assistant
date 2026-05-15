from __future__ import annotations

from app.nutrition.application.local_component_stub_catalog import (
    component_estimates_from_manager_listed_items,
    optional_refinement_for_manager_listed_items,
)


def test_manager_listed_component_red_tea_exposes_modifier_refinement_as_evidence_metadata() -> None:
    refinement = optional_refinement_for_manager_listed_items(["鐵板麵", "紅茶"])

    assert refinement == {
        "optional_refinement_allowed": True,
        "optional_refinement_targets": ["紅茶"],
        "optional_refinement_question": "如果紅茶的糖度或杯型不同，可以補充，我會幫你修正。",
    }


def test_manager_listed_component_phrase_keeps_red_tea_anchor_and_optional_refinement() -> None:
    listed_items = [
        "\u9435\u677f\u9eb5",
        "\u8c6c\u8089\u7247",
        "\u8377\u5305\u86cb",
        "\u4e00\u676f\u7d05\u8336",
    ]

    estimates = component_estimates_from_manager_listed_items(listed_items)
    refinement = optional_refinement_for_manager_listed_items(listed_items)

    assert estimates is not None
    assert [(item.name, item.estimated_kcal) for item in estimates] == [
        ("\u9435\u677f\u9eb5", 430),
        ("\u65e9\u9910\u5e97\u8c6c\u8089\u7247", 130),
        ("\u8377\u5305\u86cb", 90),
        ("\u7d05\u8336", 120),
    ]
    assert refinement is not None
    assert refinement["optional_refinement_allowed"] is True
    assert refinement["optional_refinement_targets"] == ["\u7d05\u8336"]


def test_manager_listed_component_half_teppan_modifier_uses_manager_owned_item_text() -> None:
    estimates = component_estimates_from_manager_listed_items(["鐵板麵 (一半)", "荷包蛋"])

    assert estimates is not None
    assert [(item.name, item.estimated_kcal) for item in estimates] == [
        ("鐵板麵半份", 210),
        ("荷包蛋", 90),
    ]
