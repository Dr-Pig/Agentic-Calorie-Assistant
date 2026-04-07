from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Literal

from ..schemas import ComponentEstimate, IngredientCandidate
from .base_nutrition_aliases import merged_base_nutrition_aliases


EstimateBasis = Literal["exact", "anchored", "heuristic_only", "llm_only"]
EvidenceRole = Literal["exact_truth", "ingredient_anchor", "meal_pattern_prior", "retailer_fallback", "unknown"]
ConfidenceTier = Literal["high", "medium", "low"]
EstimateMode = Literal["exact_item_mode", "anchored_component_mode", "heuristic_fallback_mode", "llm_only"]


@dataclass(frozen=True)
class MacroProfile:
    protein_g: int
    carb_g: int
    fat_g: int


@dataclass(frozen=True)
class LookupResult:
    profile: MacroProfile
    evidence_role: EvidenceRole
    estimate_basis: EstimateBasis
    confidence_tier: ConfidenceTier
    macro_completeness: str
    source_name: str
    heuristic_dependencies: tuple[str, ...] = ()
    portion_assumptions: tuple[str, ...] = ()
    why_not_exact: str = ""


ROLE_DEFAULTS: dict[str, MacroProfile] = {
    "main_carb": MacroProfile(4, 48, 2),
    "main_protein": MacroProfile(20, 2, 12),
    "fat_source": MacroProfile(0, 1, 10),
    "broth": MacroProfile(3, 4, 8),
    "sauce": MacroProfile(0, 8, 2),
    "vegetable": MacroProfile(2, 6, 0),
    "other": MacroProfile(2, 5, 2),
}

HEURISTIC_POLICY_RATIOS: dict[str, tuple[float, float, float]] = {
    # Avocado is a high-fat fruit; generic fruit ratios materially overstate carbs.
    "avocado": (0.05, 0.15, 0.80),
}

# Backward-compatible alias for prior tests/imports.
FOOD_SPECIFIC_KCAL_MACRO_RATIOS = HEURISTIC_POLICY_RATIOS

PROFILE_ALIASES: dict[str, MacroProfile] = {
    "蛋餅皮": MacroProfile(3, 23, 7),
    "蛋餅": MacroProfile(3, 23, 7),
    "雞蛋": MacroProfile(6, 1, 5),
    "蛋": MacroProfile(6, 1, 5),
    "起司": MacroProfile(4, 1, 5),
    "起司片": MacroProfile(4, 1, 5),
    "食用油": MacroProfile(0, 0, 5),
    "油": MacroProfile(0, 0, 5),
    "白飯": MacroProfile(4, 55, 1),
    "白飯大份": MacroProfile(6, 80, 1),
    "白飯特盛": MacroProfile(8, 105, 2),
    "飯": MacroProfile(4, 55, 1),
    "牛肉": MacroProfile(18, 0, 12),
    "牛肉片": MacroProfile(18, 0, 12),
    "半熟蛋": MacroProfile(6, 1, 5),
    "溫泉蛋": MacroProfile(6, 1, 5),
    "洋蔥": MacroProfile(1, 5, 0),
    "醬汁": MacroProfile(0, 8, 2),
    "牛丼醬汁": MacroProfile(0, 10, 3),
    "麵": MacroProfile(10, 65, 3),
    "拉麵": MacroProfile(10, 65, 3),
    "湯底": MacroProfile(3, 4, 8),
    "白湯": MacroProfile(4, 5, 12),
    "豚骨湯": MacroProfile(4, 5, 12),
    "辣油": MacroProfile(0, 0, 9),
    "牛油": MacroProfile(0, 0, 9),
    "韭菜": MacroProfile(1, 2, 0),
    "蔥花": MacroProfile(0, 1, 0),
    "蔬菜": MacroProfile(2, 6, 0),
    "美乃滋": MacroProfile(0, 1, 10),
}

HIGH_RISK_KEYWORDS = {
    "ramen": {"拉麵", "白湯", "豚骨", "牛白湯", "ramen"},
    "gyudon": {"牛丼", "松屋", "牛肉飯", "gyudon"},
    "breakfast_shop_oily_items": {"蛋餅", "起司", "美乃滋", "炸", "煎"},
}

_ROOT = Path(__file__).resolve().parents[2]
_MAIN_KNOWLEDGE_DIR = _ROOT.parent / "line-liff-calorie-helper-main" / "knowledge"
_CATALOG_PATH = _MAIN_KNOWLEDGE_DIR / "food_catalog_tw.json"
_ANCHORS_PATH = _MAIN_KNOWLEDGE_DIR / "portion_anchors.json"
_LOCAL_BASE_NUTRITION_PATH = _ROOT / "app" / "knowledge" / "base_nutrition_db.json"


def _normalize_name(name: str) -> str:
    lowered = name.strip().lower()
    lowered = re.sub(r"\([^)]*\)", "", lowered)
    lowered = re.sub(r"\s+", "", lowered)
    return lowered


@lru_cache(maxsize=1)
def _load_food_catalog() -> list[dict]:
    if not _CATALOG_PATH.exists():
        return []
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_portion_anchors() -> list[dict]:
    if not _ANCHORS_PATH.exists():
        return []
    return json.loads(_ANCHORS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_base_nutrition_records() -> list[dict]:
    if not _LOCAL_BASE_NUTRITION_PATH.exists():
        return []
    payload = json.loads(_LOCAL_BASE_NUTRITION_PATH.read_text(encoding="utf-8"))
    return list(payload.get("records", []))


def _kcal(profile: MacroProfile) -> int:
    return profile.protein_g * 4 + profile.carb_g * 4 + profile.fat_g * 9


def _amount_multiplier(amount_hint: str) -> float:
    text = amount_hint.strip().lower()
    if not text:
        return 1.0

    # Phase 4: 數量詞解析 (e.g. "3顆", "2份", "3 顆")
    qty_match = re.match(r"^(\d+(?:\.\d+)?)\s*[顆份杯碗瓶盤塊片個條罐包袋]", text)
    if qty_match:
        return float(qty_match.group(1))

    # Phase 3: 語義份量倍率（LLM portion_hint → multiplier）
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


def _macro_profile_from_kcal(kcal: int, *, category: str, role: str, record_id: str = "") -> MacroProfile:
    ratios = HEURISTIC_POLICY_RATIOS.get(record_id)
    if ratios is not None:
        protein_ratio, carb_ratio, fat_ratio = ratios
        return MacroProfile(
            max(0, round(kcal * protein_ratio / 4)),
            max(0, round(kcal * carb_ratio / 4)),
            max(0, round(kcal * fat_ratio / 9)),
        )
    if role == "main_carb" or category in {"grain", "flour", "starch"}:
        return MacroProfile(max(1, round(kcal * 0.10 / 4)), max(1, round(kcal * 0.78 / 4)), max(0, round(kcal * 0.12 / 9)))
    if role == "main_protein" or category == "legume":
        return MacroProfile(max(1, round(kcal * 0.26 / 4)), max(1, round(kcal * 0.56 / 4)), max(0, round(kcal * 0.18 / 9)))
    if role in {"fat_source", "sauce"} or category in {"nut_seed", "oil", "spread", "sauce"}:
        return MacroProfile(max(0, round(kcal * 0.10 / 4)), max(0, round(kcal * 0.18 / 4)), max(1, round(kcal * 0.72 / 9)))
    if category == "fruit":
        return MacroProfile(max(0, round(kcal * 0.05 / 4)), max(1, round(kcal * 0.90 / 4)), max(0, round(kcal * 0.05 / 9)))
    if category in {"vegetable", "mushroom"}:
        return MacroProfile(max(0, round(kcal * 0.18 / 4)), max(1, round(kcal * 0.72 / 4)), max(0, round(kcal * 0.10 / 9)))
    if category == "beverage":
        return MacroProfile(max(0, round(kcal * 0.12 / 4)), max(1, round(kcal * 0.76 / 4)), max(0, round(kcal * 0.12 / 9)))
    return MacroProfile(max(1, round(kcal * 0.16 / 4)), max(1, round(kcal * 0.54 / 4)), max(0, round(kcal * 0.30 / 9)))


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
                estimate_basis="anchored",  # 提升為 anchored 以確保優先於 LLM 的初步預估
                confidence_tier="high",     # 手調黃金基準視為高信心度
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


def _estimate_mode_from_components(component_estimates: list[ComponentEstimate], unknown: list[str]) -> EstimateMode:
    if not component_estimates:
        return "llm_only"
    if any(item.estimate_basis == "heuristic_only" for item in component_estimates) or unknown:
        return "heuristic_fallback_mode"
    if all(item.estimate_basis == "exact" for item in component_estimates):
        return "exact_item_mode"
    return "anchored_component_mode"


def _confidence_tier_for_result(
    *,
    component_estimates: list[ComponentEstimate],
    unknown: list[str],
    matched_critical: int,
    critical_total: int,
) -> ConfidenceTier:
    if not component_estimates or (critical_total > 0 and matched_critical < critical_total):
        return "low"
    if any(item.estimate_basis == "heuristic_only" for item in component_estimates) or unknown:
        return "low"
    if all(item.confidence_tier == "high" for item in component_estimates):
        return "high"
    return "medium"


def deterministic_macro_estimate(ingredients: list[IngredientCandidate]) -> dict[str, object]:
    component_estimates: list[ComponentEstimate] = []
    protein = 0
    carb = 0
    fat = 0
    unknown: list[str] = []
    matched_critical = 0
    critical_total = 0
    macro_basis: list[dict[str, object]] = []
    portion_assumptions: list[str] = []
    heuristic_dependencies: list[str] = []

    for ingredient in ingredients:
        if ingredient.is_critical:
            critical_total += 1
        lookup = resolve_ingredient_estimate(ingredient.name, ingredient.amount_hint, ingredient.role)
        print(f"  [DEBUG] Processing ingredient: {ingredient.name} | hint: {ingredient.amount_hint} | matched: {bool(lookup)}")
        if lookup is None:
            unknown.append(ingredient.name)
            continue
        if ingredient.is_critical:
            matched_critical += 1
        print(f"  [DEBUG] Component {ingredient.name}: P={lookup.profile.protein_g}, C={lookup.profile.carb_g}, F={lookup.profile.fat_g} (Kcal: {_kcal(lookup.profile)})")
        component_estimates.append(
            ComponentEstimate(
                name=ingredient.name,
                source="lookup",
                evidence_role=lookup.evidence_role,
                estimate_basis=lookup.estimate_basis,
                confidence_tier=lookup.confidence_tier,
                quantity_hint=ingredient.amount_hint or None,
                estimated_kcal=_kcal(lookup.profile),
                protein_g=lookup.profile.protein_g,
                carb_g=lookup.profile.carb_g,
                fat_g=lookup.profile.fat_g,
                heuristic_dependencies=list(lookup.heuristic_dependencies),
            )
        )
        protein += lookup.profile.protein_g
        carb += lookup.profile.carb_g
        fat += lookup.profile.fat_g
        print(f"  [DEBUG] Running Totals: P={protein}, C={carb}, F={fat}")
        macro_basis.append(
            {
                "name": ingredient.name,
                "source_name": lookup.source_name,
                "evidence_role": lookup.evidence_role,
                "estimate_basis": lookup.estimate_basis,
                "macro_completeness": lookup.macro_completeness,
                "confidence_tier": lookup.confidence_tier,
            }
        )
        portion_assumptions.extend(lookup.portion_assumptions)
        heuristic_dependencies.extend(lookup.heuristic_dependencies)

    estimated_kcal = protein * 4 + carb * 4 + fat * 9
    deterministic_hit = bool(component_estimates) and (critical_total == 0 or matched_critical == critical_total)
    estimate_mode = _estimate_mode_from_components(component_estimates, unknown)
    confidence_tier = _confidence_tier_for_result(
        component_estimates=component_estimates,
        unknown=unknown,
        matched_critical=matched_critical,
        critical_total=critical_total,
    )
    evidence_gaps = []
    if unknown:
        evidence_gaps.append("unmatched_components")
    if any(item.estimate_basis == "heuristic_only" for item in component_estimates):
        evidence_gaps.append("heuristic_macro_dependency")
    if critical_total > matched_critical:
        evidence_gaps.append("critical_component_gap")

    if estimate_mode == "exact_item_mode":
        why_not_exact = ""
    elif estimate_mode == "anchored_component_mode":
        why_not_exact = "No exact item truth matched; estimate comes from complete ingredient anchors."
    elif estimate_mode == "heuristic_fallback_mode":
        why_not_exact = "Estimate depends on heuristic macro inference or incomplete ingredient anchors."
    else:
        why_not_exact = "No deterministic ingredient evidence was available."

    return {
        "component_estimates": component_estimates,
        "totals": {
            "protein_g": protein,
            "carb_g": carb,
            "fat_g": fat,
            "estimated_kcal": estimated_kcal,
        },
        "unknown_components": unknown,
        "deterministic_hit": deterministic_hit,
        "estimate_mode": estimate_mode,
        "confidence_tier": confidence_tier,
        "evidence_gaps": evidence_gaps,
        "macro_basis": macro_basis,
        "portion_assumptions": list(dict.fromkeys(item for item in portion_assumptions if item)),
        "heuristic_dependencies": list(dict.fromkeys(item for item in heuristic_dependencies if item)),
        "why_not_exact": why_not_exact,
        "matched_critical": matched_critical,
        "critical_total": critical_total,
    }


def apply_high_risk_sanity_checks(
    *,
    title: str,
    components: list[str],
    protein_g: int,
    carb_g: int,
    fat_g: int,
    uncertainty_factors: list[str],
) -> list[str]:
    flagged = list(dict.fromkeys(uncertainty_factors))
    joined = " ".join([title, *components]).lower()

    if any(token.lower() in joined for token in HIGH_RISK_KEYWORDS["ramen"]) and fat_g < 15:
        flagged.append("濃湯拉麵的脂肪估計可能偏低，實際油脂與喝湯量可能更高。")
    if any(token.lower() in joined for token in HIGH_RISK_KEYWORDS["gyudon"]) and (carb_g < 40 or fat_g < 10):
        flagged.append("牛丼類餐點通常會包含較多白飯與醬汁，目前估計可能偏低。")
    if any(token.lower() in joined for token in HIGH_RISK_KEYWORDS["breakfast_shop_oily_items"]) and fat_g < 10:
        flagged.append("早餐店煎製油量與起司/美乃滋用量可能讓脂肪再更高。")
    return list(dict.fromkeys(flagged))
