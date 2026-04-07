from __future__ import annotations

from typing import Any

from ..schemas import NutritionResolutionResult


def _confidence_rank(value: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(str(value or "low"), 0)


def _confidence_label(rank: int) -> str:
    if rank >= 2:
        return "high"
    if rank >= 1:
        return "medium"
    return "low"


def _find_exact_item_evidence(normalized_evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in normalized_evidence:
        raw = dict(item.get("raw") or {})
        if (
            str(raw.get("source_class") or item.get("source_type") or "") == "exact_item_db"
            and str(raw.get("identity_confidence") or raw.get("match_confidence") or item.get("match_quality") or "") == "high"
        ):
            return raw
    return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def apply_nutrition_invariant_guards(
    *,
    result: NutritionResolutionResult,
    normalized_evidence: list[dict[str, Any]],
) -> tuple[NutritionResolutionResult, dict[str, Any]]:
    payload = dict(result.answer_payload or {})
    guard_meta: dict[str, Any] = {"guard_actions": [], "macro_delta": None}

    exact_item = _find_exact_item_evidence(normalized_evidence)
    if exact_item and result.exactness == "exact_item":
        exact_kcal = int(exact_item.get("label_kcal") or exact_item.get("kcal") or 0)
        exact_macros = dict(exact_item.get("label_macros") or {})
        base_kcal = int(payload.get("base_estimated_kcal") or exact_kcal or 0)
        base_protein = _safe_float(payload.get("base_protein_g"), _safe_float(exact_macros.get("protein_g") or exact_item.get("protein_g")))
        base_carb = _safe_float(payload.get("base_carb_g"), _safe_float(exact_macros.get("carb_g") or exact_item.get("carb_g")))
        base_fat = _safe_float(payload.get("base_fat_g"), _safe_float(exact_macros.get("fat_g") or exact_item.get("fat_g")))
        portion_multiplier = _safe_float(payload.get("portion_multiplier"), 1.0) or 1.0

        payload.setdefault("base_estimated_kcal", exact_kcal)
        payload.setdefault("base_protein_g", round(base_protein))
        payload.setdefault("base_carb_g", round(base_carb))
        payload.setdefault("base_fat_g", round(base_fat))
        payload.setdefault("portion_multiplier", portion_multiplier)
        payload.setdefault("portion_reason", str(payload.get("portion_reason") or "").strip())

        if base_kcal != exact_kcal or round(base_protein) != round(_safe_float(exact_macros.get("protein_g") or exact_item.get("protein_g"))) or round(base_carb) != round(_safe_float(exact_macros.get("carb_g") or exact_item.get("carb_g"))) or round(base_fat) != round(_safe_float(exact_macros.get("fat_g") or exact_item.get("fat_g"))):
            guard_meta["guard_actions"].append("flag_exact_label_mismatch")
            rank = max(0, _confidence_rank(result.confidence) - 1)
            result = result.model_copy(update={"confidence": _confidence_label(rank)})

        result = result.model_copy(update={"answer_payload": payload})

    kcal = int(payload.get("estimated_kcal") or 0)
    protein = int(payload.get("protein_g") or 0)
    carb = int(payload.get("carb_g") or 0)
    fat = int(payload.get("fat_g") or 0)
    if kcal > 0 and any(value > 0 for value in (protein, carb, fat)):
        implied_kcal = protein * 4 + carb * 4 + fat * 9
        delta = abs(implied_kcal - kcal)
        guard_meta["macro_delta"] = delta
        if delta > 180:
            rank = max(0, _confidence_rank(result.confidence) - 1)
            if _confidence_label(rank) != result.confidence:
                guard_meta["guard_actions"].append("flag_macro_kcal_mismatch")
                result = result.model_copy(update={"confidence": _confidence_label(rank)})
        elif delta > 80:
            rank = max(0, _confidence_rank(result.confidence) - 1)
            if _confidence_label(rank) != result.confidence:
                guard_meta["guard_actions"].append("flag_macro_kcal_mismatch")
                result = result.model_copy(update={"confidence": _confidence_label(rank)})

    return result, guard_meta
