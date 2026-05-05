from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FoodDBActivationScenarioCase:
    turn_id: str
    packet_posture: str
    evidence_queries: tuple[str, ...] = ()
    required_anchor_ids: tuple[str, ...] = ()
    required_modifier_compatibility: tuple[tuple[str, str], ...] = ()
    expected_retrieval_boundary: str | None = None


Case = FoodDBActivationScenarioCase
FOODDB_LOCAL_ACTIVATION_SCENARIO_CASES: tuple[FoodDBActivationScenarioCase, ...] = (
    Case(
        "breakfast_tea_egg_latte",
        "fooddb_packet_required",
        ("\u8336\u8449\u86cb", "\u62ff\u9435"),
        ("single_item_tea_egg", "custom_drink_latte"),
    ),
    Case(
        "lunch_chicken_bento",
        "fooddb_packet_required",
        ("\u96de\u817f\u4fbf\u7576",),
        ("generic_meal_chicken_bento",),
    ),
    Case(
        "lunch_rice_less_correction",
        "fooddb_packet_required",
        ("\u96de\u817f\u4fbf\u7576\u5c11\u98ef",),
        ("generic_meal_chicken_bento",),
        (("rice_portion", "compatible_via_normalized_equivalent"),),
    ),
    Case(
        "bubble_tea_first_value",
        "fooddb_packet_required",
        ("\u73cd\u5976",),
        ("custom_drink_boba_milk_tea",),
    ),
    Case(
        "bubble_tea_half_sugar_large_refinement",
        "fooddb_packet_required",
        ("\u5927\u676f\u534a\u7cd6\u73cd\u5976",),
        ("custom_drink_boba_milk_tea",),
        (("cup_size", "compatible"), ("sugar_level", "compatible")),
    ),
    Case(
        "dinner_luwei_bare_draft",
        "followup_no_mutation_no_fooddb_estimate",
        ("\u6211\u5403\u6ef7\u5473",),
        expected_retrieval_boundary="bare_basket_ask_followup_no_estimate",
    ),
    Case(
        "dinner_luwei_listed_commit",
        "fooddb_packet_required",
        ("\u6ef7\u5473\u6709\u8c46\u5e72\u3001\u6d77\u5e36\u3001\u8ca2\u4e38",),
        ("listed_item_kelp", "listed_item_meatball", "listed_item_tofu_dried"),
        expected_retrieval_boundary="listed_basket_component_recall",
    ),
    Case("dinner_remove_gongwan", "target_evidence_only_no_fooddb_lookup"),
    Case("today_consumed_remaining_query", "read_only_query_no_fooddb_lookup"),
)


__all__ = [
    "FOODDB_LOCAL_ACTIVATION_SCENARIO_CASES",
    "FoodDBActivationScenarioCase",
]
