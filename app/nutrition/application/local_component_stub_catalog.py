from __future__ import annotations

from collections.abc import Sequence

from app.shared.contracts.intake import ComponentEstimate

_TEPPAN_NOODLE = "\u9435\u677f\u9eb5"
_TEPPAN_NOODLE_HALF = "\u9435\u677f\u9eb5\u534a\u4efd"
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
_WHITE_RICE_HALF_BOWL = "\u767d\u98ef\u534a\u7897"
_WHITE_RICE_ONE_BOWL = "\u767d\u98ef\u4e00\u7897"
_CHICKEN_LEG_ONE = "\u96de\u817f\u4e00\u652f"
_GREENS_TWO_SERVINGS = "\u9752\u83dc\u5169\u6a23"
_BRAISED_EGG_ONE = "\u6ef7\u86cb\u4e00\u9846"

_COMPONENT_FACTS = {
    _TEPPAN_NOODLE: {
        "quantity_hint": "1 serving",
        "estimated_kcal": 430,
        "protein_g": 12,
        "carb_g": 68,
        "fat_g": 14,
    },
    _TEPPAN_NOODLE_HALF: {
        "quantity_hint": "half serving",
        "estimated_kcal": 210,
        "protein_g": 6,
        "carb_g": 34,
        "fat_g": 7,
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
        "optional_refinement": {
            "optional_refinement_allowed": True,
            "optional_refinement_targets": [_BLACK_TEA],
            "optional_refinement_question": "如果紅茶的糖度或杯型不同，可以補充，我會幫你修正。",
        },
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
    _WHITE_RICE_HALF_BOWL: {
        "quantity_hint": "half bowl",
        "estimated_kcal": 180,
        "protein_g": 3,
        "carb_g": 40,
        "fat_g": 0,
    },
    _WHITE_RICE_ONE_BOWL: {
        "quantity_hint": "1 bowl",
        "estimated_kcal": 360,
        "protein_g": 6,
        "carb_g": 80,
        "fat_g": 1,
    },
    _CHICKEN_LEG_ONE: {
        "quantity_hint": "1 piece",
        "estimated_kcal": 260,
        "protein_g": 24,
        "carb_g": 5,
        "fat_g": 16,
    },
    _GREENS_TWO_SERVINGS: {
        "quantity_hint": "2 vegetable servings",
        "estimated_kcal": 80,
        "protein_g": 4,
        "carb_g": 12,
        "fat_g": 3,
    },
    _BRAISED_EGG_ONE: {
        "quantity_hint": "1 egg",
        "estimated_kcal": 80,
        "protein_g": 7,
        "carb_g": 1,
        "fat_g": 5,
    },
}

_ALIASES = {
    _PORK_SLICES: _BREAKFAST_PORK_SLICES,
    "\u534a\u7897\u767d\u98ef": _WHITE_RICE_HALF_BOWL,
    "\u767d\u98ef\u534a\u4efd": _WHITE_RICE_HALF_BOWL,
    "\u767d\u98ef": _WHITE_RICE_ONE_BOWL,
    "\u767d\u98ef\u4e00\u4efd": _WHITE_RICE_ONE_BOWL,
    "\u96de\u817f": _CHICKEN_LEG_ONE,
    "\u96de\u817f\u4e00\u652f": _CHICKEN_LEG_ONE,
    "\u9e21\u817f": _CHICKEN_LEG_ONE,
    "\u9e21\u817f\u4e00\u652f": _CHICKEN_LEG_ONE,
    "\u9752\u83dc": _GREENS_TWO_SERVINGS,
    "\u70d9\u9752\u83dc": _GREENS_TWO_SERVINGS,
    "\u6ef7\u86cb": _BRAISED_EGG_ONE,
    "\u5364\u86cb": _BRAISED_EGG_ONE,
    "\u6ef7\u86cb\u4e00\u9846": _BRAISED_EGG_ONE,
}


def component_estimates_from_manager_listed_items(
    listed_items: Sequence[str] | None,
) -> list[ComponentEstimate] | None:
    estimates: list[ComponentEstimate] = []
    for item in listed_items or []:
        canonical = _canonical_component_name(item)
        facts = _COMPONENT_FACTS.get(canonical)
        if facts is None:
            continue
        estimate_facts = {
            key: facts[key]
            for key in ("quantity_hint", "estimated_kcal", "protein_g", "carb_g", "fat_g")
        }
        estimates.append(
            ComponentEstimate(
                name=canonical,
                source="lookup",
                evidence_role="ingredient_anchor",
                estimate_basis="anchored",
                confidence_tier="medium",
                reason="manager_listed_item_component_stub",
                evidence_ids=[f"local_component_stub:{canonical}"],
                **estimate_facts,
            )
        )
    return estimates or None


def optional_refinement_for_manager_listed_items(listed_items: Sequence[str] | None) -> dict[str, object] | None:
    for item in listed_items or []:
        canonical = _canonical_component_name(item)
        facts = _COMPONENT_FACTS.get(canonical) or {}
        refinement = facts.get("optional_refinement")
        if isinstance(refinement, dict) and refinement.get("optional_refinement_allowed") is True:
            return dict(refinement)
    return None


def _canonical_component_name(item: object) -> str:
    text = str(item).strip()
    compact = (
        text.replace(" ", "")
        .replace("(", "")
        .replace(")", "")
        .replace("（", "")
        .replace("）", "")
    )
    if _BLACK_TEA in compact:
        return _BLACK_TEA
    if _TEPPAN_NOODLE in compact and any(marker in compact for marker in ("一半", "半份")):
        return _TEPPAN_NOODLE_HALF
    return _ALIASES.get(text, text)
