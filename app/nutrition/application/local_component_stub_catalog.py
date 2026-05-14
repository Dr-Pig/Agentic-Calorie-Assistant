from __future__ import annotations

from collections.abc import Sequence

from app.shared.contracts.intake import ComponentEstimate

_TEPPAN_NOODLE = "\u9435\u677f\u9eb5"
_FRIED_EGG = "\u8377\u5305\u86cb"
_PORK_SLICES = "\u8c6c\u8089\u7247"
_BREAKFAST_PORK_SLICES = "\u65e9\u9910\u5e97\u8c6c\u8089\u7247"

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
