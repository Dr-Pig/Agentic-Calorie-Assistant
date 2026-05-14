from __future__ import annotations

from collections.abc import Sequence

from app.shared.contracts.intake import ComponentEstimate

_TEPPAN_NOODLE = "\u9435\u677f\u9eb5"
_FRIED_EGG = "\u8377\u5305\u86cb"
_PORK_SLICES = "\u8c6c\u8089\u7247"
_BREAKFAST_PORK_SLICES = "\u65e9\u9910\u5e97\u8c6c\u8089\u7247"
_BLACK_TEA = "\u7d05\u8336"
_CHICKEN_RICE = "\u96de\u8089\u98ef"
_CHICKEN_RICE_SMALL = "\u96de\u8089\u98ef\u5c11\u4e00\u9ede"
_SOUP = "\u6e6f"
_BUBBLE_MILK_TEA = "\u73cd\u73e0\u5976\u8336"
_BUBBLE_MILK_TEA_HALF_LARGE = "\u534a\u7cd6\u5927\u676f\u73cd\u73e0\u5976\u8336"
_DRIED_TOFU = "\u8c46\u5e72"
_KELP = "\u6d77\u5e36"
_PORK_BALL = "\u8ca2\u4e38"

_COMPONENT_FACTS = {
    _TEPPAN_NOODLE: {
        "quantity_hint": "1 serving",
        "estimated_kcal": 430,
        "protein_g": 12,
        "carb_g": 68,
        "fat_g": 14,
    },
    _FRIED_EGG: {
        "quantity_hint": "1 egg",
        "estimated_kcal": 90,
        "protein_g": 7,
        "carb_g": 1,
        "fat_g": 7,
    },
    _BREAKFAST_PORK_SLICES: {
        "quantity_hint": "1 breakfast portion",
        "estimated_kcal": 130,
        "protein_g": 13,
        "carb_g": 2,
        "fat_g": 8,
    },
    _BLACK_TEA: {
        "quantity_hint": "1 cup",
        "estimated_kcal": 120,
        "protein_g": 0,
        "carb_g": 30,
        "fat_g": 0,
    },
    _CHICKEN_RICE: {
        "quantity_hint": "1 bowl",
        "estimated_kcal": 500,
        "protein_g": 30,
        "carb_g": 64,
        "fat_g": 15,
    },
    _CHICKEN_RICE_SMALL: {
        "quantity_hint": "smaller portion",
        "estimated_kcal": 320,
        "protein_g": 24,
        "carb_g": 42,
        "fat_g": 9,
    },
    _SOUP: {
        "quantity_hint": "1 bowl",
        "estimated_kcal": 150,
        "protein_g": 5,
        "carb_g": 6,
        "fat_g": 4,
    },
    _BUBBLE_MILK_TEA: {
        "quantity_hint": "1 cup",
        "estimated_kcal": 450,
        "protein_g": 4,
        "carb_g": 80,
        "fat_g": 12,
    },
    _BUBBLE_MILK_TEA_HALF_LARGE: {
        "quantity_hint": "half sugar large cup",
        "estimated_kcal": 520,
        "protein_g": 4,
        "carb_g": 92,
        "fat_g": 14,
    },
    _DRIED_TOFU: {
        "quantity_hint": "1 piece",
        "estimated_kcal": 120,
        "protein_g": 9,
        "carb_g": 8,
        "fat_g": 6,
    },
    _KELP: {
        "quantity_hint": "1 serving",
        "estimated_kcal": 35,
        "protein_g": 1,
        "carb_g": 7,
        "fat_g": 0,
    },
    _PORK_BALL: {
        "quantity_hint": "1 piece",
        "estimated_kcal": 80,
        "protein_g": 5,
        "carb_g": 7,
        "fat_g": 4,
    },
}

_ALIASES = {
    _PORK_SLICES: _BREAKFAST_PORK_SLICES,
}


def component_estimates_from_manager_listed_items(
    listed_items: Sequence[str] | None,
) -> list[ComponentEstimate] | None:
    estimates: list[ComponentEstimate] = []
    for item in listed_items or []:
        canonical = _ALIASES.get(str(item).strip(), str(item).strip())
        facts = _COMPONENT_FACTS.get(canonical)
        if facts is None:
            continue
        estimates.append(
            ComponentEstimate(
                name=canonical,
                source="lookup",
                evidence_role="ingredient_anchor",
                estimate_basis="anchored",
                confidence_tier="medium",
                reason="manager_listed_item_component_stub",
                evidence_ids=[f"local_component_stub:{canonical}"],
                **facts,
            )
        )
    return estimates or None
