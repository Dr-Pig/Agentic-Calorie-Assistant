from __future__ import annotations
import re
from .base_nutrition_aliases import merged_base_nutrition_aliases
from .nutrition_profiles import (
    ConfidenceTier, EstimateBasis, LookupResult, MacroProfile, PROFILE_ALIASES, ROLE_DEFAULTS,
    _load_base_nutrition_records, _load_food_catalog, _load_portion_anchors, _macro_profile_from_kcal, _normalize_name,
)
def _amount_multiplier(amount_hint: str) -> float:
    text = amount_hint.strip().lower()
    if not text:
        return 1.0
    qty_match = re.match(r"^(\d+(?:\.\d+)?)\s*[顆份杯碗瓶盤塊片個條罐包袋]", text)
    if qty_match:
        return float(qty_match.group(1))
    if any(token in text for token in ["extra large", "double", "雙份", "加大"]):
        return 2.0
    if any(token in text for token in ["特盛", "特大"]):
        return 1.6
    if any(token in text for token in ["large", "大份", "大碗"]):
        return 1.4
    if any(token in text for token in ["多"]):
        return 1.3
    if any(token in text for token in ["一般", "普通", "標準"]):
        return 1.0
    if any(token in text for token in ["少", "少量"]):
        return 0.7
    if any(token in text for token in ["small", "小份", "小碗"]):
        return 0.8
    if any(token in text for token in ["half", "1/2", "半", "半份"]):
        return 0.5
    if any(token in text for token in ["optional", "unknown"]):
        return 0.5
    return 1.0

def _base_record_multiplier(record: dict, amount_hint: str, *, has_exact_macros: bool) -> float:
    multiplier = _amount_multiplier(amount_hint)
    if amount_hint.strip():
        return multiplier
    if has_exact_macros:
        return multiplier
    serving_basis = record.get("serving_basis") or {}
    amount = serving_basis.get("amount")
    unit_type = str(serving_basis.get("unit_type") or "")
    if unit_type != "g" or not isinstance(amount, (int, float)) or amount < 80:
        return multiplier
    category = str(record.get("category") or "")
    if category in {"nut_seed", "oil", "spread", "sauce"}:
        return multiplier * 0.2
    if category in {"grain", "flour", "starch", "legume"}:
        return multiplier * 0.6
    if category in {"vegetable", "mushroom", "fruit", "beverage"}:
        return multiplier * 0.8
    return multiplier


def _macro_completeness(nutrition: dict) -> str:
    protein = nutrition.get("protein_g")
    carb = nutrition.get("carb_g")
    fat = nutrition.get("fat_g")
    if all(isinstance(value, (int, float)) for value in (protein, carb, fat)):
        return "complete"
    if isinstance(nutrition.get("kcal"), (int, float)):
        return "kcal_only"
    return "partial"

def _base_nutrition_lookup(name: str, amount_hint: str = "", role: str = "other") -> LookupResult | None:
    normalized_name = _normalize_name(name)
    if not normalized_name:
        return None

    for record in _load_base_nutrition_records():
        names = merged_base_nutrition_aliases(record)
        canon_names = [_normalize_name(str(candidate)) for candidate in names if candidate]
        if not any(candidate and (candidate in normalized_name or normalized_name in candidate) for candidate in canon_names):
            continue

        nutrition = record.get("nutrition") or {}
        kcal = nutrition.get("kcal")
        if not isinstance(kcal, (int, float)) or kcal <= 0:
            continue

        macro_completeness = _macro_completeness(nutrition)
        source_name = str(record.get("source_name") or record.get("title") or "base_nutrition")
        if macro_completeness == "complete":
            profile = MacroProfile(
                protein_g=max(0, round(float(nutrition.get("protein_g") or 0))),
                carb_g=max(0, round(float(nutrition.get("carb_g") or 0))),
                fat_g=max(0, round(float(nutrition.get("fat_g") or 0))),
            )
            estimate_basis: EstimateBasis = "anchored"
            confidence_tier: ConfidenceTier = "high"
            heuristic_dependencies: tuple[str, ...] = ()
            why_not_exact = "No exact branded item truth matched; used complete ingredient anchors."
        else:
            record_id = str(record.get("id") or "")
            profile = _macro_profile_from_kcal(
                int(round(float(kcal))),
                category=str(record.get("category") or ""),
                role=role,
                record_id=record_id,
            )
            estimate_basis = "heuristic_only"
            confidence_tier = "low"
            heuristic_dependencies = ("kcal_only_anchor", f"heuristic_policy:{record_id or 'generic'}")
            why_not_exact = "Matched only a kcal-only ingredient anchor, so macros come from heuristic policy."

        multiplier = _base_record_multiplier(record, amount_hint, has_exact_macros=macro_completeness == "complete")
        profile = MacroProfile(
            protein_g=max(0, round(profile.protein_g * multiplier)),
            carb_g=max(0, round(profile.carb_g * multiplier)),
            fat_g=max(0, round(profile.fat_g * multiplier)),
        )
        portion_assumptions: tuple[str, ...] = ((amount_hint or str((record.get("serving_basis") or {}).get("label") or "")).strip(),)
        return LookupResult(
            profile=profile,
            evidence_role="ingredient_anchor",
            estimate_basis=estimate_basis,
            confidence_tier=confidence_tier,
            macro_completeness=macro_completeness,
            source_name=source_name,
            heuristic_dependencies=tuple(item for item in heuristic_dependencies if item),
            portion_assumptions=tuple(item for item in portion_assumptions if item),
            why_not_exact=why_not_exact,
        )

    return None

def _catalog_lookup(name: str, amount_hint: str = "") -> LookupResult | None:
    normalized_name = _normalize_name(name)
    if not normalized_name:
        return None

    for item in _load_food_catalog():
        names = [item.get("name", ""), *(item.get("aliases") or [])]
        canon_names = [_normalize_name(str(candidate)) for candidate in names if candidate]
        if not any(candidate and (candidate in normalized_name or normalized_name in candidate) for candidate in canon_names):
            continue

        low = int(item.get("typical_kcal_low") or 0)
        high = int(item.get("typical_kcal_high") or 0)
        if low <= 0 and high <= 0:
            continue
        kcal = round(((low + high) / 2 if high else low) * _amount_multiplier(amount_hint))
        category = str(item.get("category") or "")
        if category == "drink":
            profile = MacroProfile(0, max(0, round(kcal / 4)), 0)
        elif category in {"rice_bowl", "noodle", "dumpling", "staple_meal"}:
            profile = MacroProfile(max(6, round(kcal * 0.12 / 4)), max(0, round(kcal * 0.52 / 4)), max(0, round(kcal * 0.36 / 9)))
        else:
            profile = MacroProfile(max(4, round(kcal * 0.16 / 4)), max(0, round(kcal * 0.44 / 4)), max(0, round(kcal * 0.40 / 9)))
        return LookupResult(
            profile=profile,
            evidence_role="retailer_fallback",
            estimate_basis="heuristic_only",
            confidence_tier="low",
            macro_completeness="kcal_only",
            source_name=str(item.get("name") or "food_catalog"),
            heuristic_dependencies=("catalog_range_proxy",),
            portion_assumptions=tuple(item for item in [amount_hint] if item),
            why_not_exact="Fell back to generic catalog range instead of an exact or complete anchor.",
        )
    return None

def _portion_anchor_lookup(name: str, amount_hint: str = "", role: str = "other") -> LookupResult | None:
    normalized_name = _normalize_name(name)
    normalized_amount = _normalize_name(amount_hint)
    if not normalized_name and not normalized_amount:
        return None

    for anchor in _load_portion_anchors():
        label = _normalize_name(str(anchor.get("label") or ""))
        if not label:
            continue
        if label not in normalized_name and label not in normalized_amount:
            continue
        kcal = int(anchor.get("rough_kcal") or 0)
        if kcal <= 0:
            continue
        category = str(anchor.get("category") or "")
        if category in {"rice", "drink", "staple_meal", "bento"} or role == "main_carb":
            profile = MacroProfile(max(2, round(kcal * 0.08 / 4)), max(0, round(kcal * 0.72 / 4)), max(0, round(kcal * 0.20 / 9)))
        elif category == "protein" or role == "main_protein":
            profile = MacroProfile(max(8, round(kcal * 0.48 / 4)), max(0, round(kcal * 0.08 / 4)), max(0, round(kcal * 0.44 / 9)))
        elif category in {"fat", "sauce"} or role in {"fat_source", "sauce"}:
            profile = MacroProfile(0, max(0, round(kcal * 0.20 / 4)), max(0, round(kcal * 0.80 / 9)))
        else:
            profile = MacroProfile(max(2, round(kcal * 0.12 / 4)), max(0, round(kcal * 0.58 / 4)), max(0, round(kcal * 0.30 / 9)))
        return LookupResult(
            profile=profile,
            evidence_role="ingredient_anchor",
            estimate_basis="heuristic_only",
            confidence_tier="low",
            macro_completeness="kcal_only",
            source_name=str(anchor.get("label") or "portion_anchor"),
            heuristic_dependencies=("portion_anchor_proxy",),
            portion_assumptions=tuple(item for item in [amount_hint or str(anchor.get("label") or "")] if item),
            why_not_exact="Used a portion anchor proxy instead of an exact or complete ingredient record.",
        )
    return None

def resolve_ingredient_estimate(name: str, amount_hint: str = "", role: str = "other") -> LookupResult | None:
    normalized_name = _normalize_name(name)
    if not normalized_name:
        return None

    for key, profile in PROFILE_ALIASES.items():
        normalized_key = _normalize_name(key)
        if normalized_key and (normalized_key in normalized_name or normalized_name in normalized_key):
            scaled = MacroProfile(
                protein_g=max(0, round(profile.protein_g * _amount_multiplier(amount_hint))),
                carb_g=max(0, round(profile.carb_g * _amount_multiplier(amount_hint))),
                fat_g=max(0, round(profile.fat_g * _amount_multiplier(amount_hint))),
            )
            return LookupResult(
                profile=scaled,
                evidence_role="ingredient_anchor",
                estimate_basis="anchored",
                confidence_tier="high",
                macro_completeness="partial",
                source_name="profile_aliases",
                heuristic_dependencies=("alias_profile",),
                portion_assumptions=tuple(item for item in [amount_hint] if item),
                why_not_exact="Used a hand-tuned alias profile instead of exact item truth.",
            )

    for resolver in (
        lambda: _base_nutrition_lookup(name, amount_hint, role),
        lambda: _catalog_lookup(name, amount_hint),
        lambda: _portion_anchor_lookup(name, amount_hint, role),
    ):
        matched = resolver()
        if matched is not None:
            return matched

    matched = ROLE_DEFAULTS.get(role)
    if matched is None or role == "other":
        return None
    scaled = MacroProfile(
        protein_g=max(0, round(matched.protein_g * _amount_multiplier(amount_hint))),
        carb_g=max(0, round(matched.carb_g * _amount_multiplier(amount_hint))),
        fat_g=max(0, round(matched.fat_g * _amount_multiplier(amount_hint))),
    )
    return LookupResult(
        profile=scaled,
        evidence_role="unknown",
        estimate_basis="heuristic_only",
        confidence_tier="low",
        macro_completeness="partial",
        source_name="role_defaults",
        heuristic_dependencies=("role_default_fallback",),
        portion_assumptions=tuple(item for item in [amount_hint] if item),
        why_not_exact="No exact or anchored evidence matched; used a role default fallback.",
    )


def lookup_ingredient_profile(name: str, amount_hint: str = "", role: str = "other") -> MacroProfile | None:
    matched = resolve_ingredient_estimate(name, amount_hint, role)
    return matched.profile if matched is not None else None
