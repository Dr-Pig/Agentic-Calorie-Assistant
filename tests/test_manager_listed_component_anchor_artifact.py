from __future__ import annotations

from app.composition.intake_estimation_tools import manager_semantic_decision_from_tool_arguments
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


def test_top_level_tool_arguments_preserve_manager_owned_listed_items() -> None:
    semantic_decision = manager_semantic_decision_from_tool_arguments(
        {
            "listed_items": ["\u767d\u98ef\u534a\u7897", "\u96de\u817f\u4e00\u652f"],
            "retrieval_goal": "listed_item_lookup",
        }
    )

    assert semantic_decision is not None
    assert semantic_decision.listed_items == ["\u767d\u98ef\u534a\u7897", "\u96de\u817f\u4e00\u652f"]
    assert semantic_decision.retrieval_goal == "listed_item_lookup"
    assert semantic_decision.semantic_authority_source == "manager_tool_arguments"


def test_common_self_use_basket_components_have_component_anchors() -> None:
    estimates = component_estimates_from_manager_listed_items(
        [
            "\u767d\u98ef\u534a\u7897",
            "\u96de\u817f\u4e00\u652f",
            "\u9752\u83dc\u5169\u6a23",
            "\u6ef7\u86cb\u4e00\u9846",
        ]
    )

    assert estimates is not None
    assert [(item.name, item.estimated_kcal) for item in estimates] == [
        ("\u767d\u98ef\u534a\u7897", 180),
        ("\u96de\u817f\u4e00\u652f", 260),
        ("\u9752\u83dc\u5169\u6a23", 80),
        ("\u6ef7\u86cb\u4e00\u9846", 80),
    ]
    assert sum(item.estimated_kcal for item in estimates) == 600


def test_manager_listed_component_half_teppan_modifier_uses_manager_owned_item_text() -> None:
    estimates = component_estimates_from_manager_listed_items(["鐵板麵 (一半)", "荷包蛋"])

    assert estimates is not None
    assert [(item.name, item.estimated_kcal) for item in estimates] == [
        ("鐵板麵半份", 210),
        ("荷包蛋", 90),
    ]
