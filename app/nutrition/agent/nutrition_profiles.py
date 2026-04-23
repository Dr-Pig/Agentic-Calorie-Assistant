from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Literal



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

_ROOT = Path(__file__).resolve().parents[3]
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


