from __future__ import annotations

from typing import Any

CONSISTENT_DELTA_PCT = 0.10
RECONCILE_DELTA_PCT = 0.20


def _safe_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _exact_macro_breakdown(normalized_evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in normalized_evidence:
        raw = dict(item.get("raw") or {})
        source_class = str(raw.get("source_class") or item.get("source_class") or item.get("source_type") or "")
        if source_class not in {"exact_item_db", "web_search_official"}:
            continue
        label_macros = dict(raw.get("label_macros") or raw.get("macros") or {})
        protein = _safe_int(label_macros.get("protein_g") or raw.get("protein_g"))
        carb = _safe_int(label_macros.get("carb_g") or raw.get("carb_g"))
        fat = _safe_int(label_macros.get("fat_g") or raw.get("fat_g"))
        if protein <= 0 and carb <= 0 and fat <= 0:
            continue
        return {
            "protein_g": protein,
            "carb_g": carb,
            "fat_g": fat,
            "macro_source": "exact_label",
            "macro_confidence": "high",
            "macro_status": "available",
            "macro_kcal": protein * 4 + carb * 4 + fat * 9,
            "component_macro_coverage": "exact_label",
        }
    return None


def derive_macro_breakdown(
    *,
    answer_payload: dict[str, Any],
    normalized_evidence: list[dict[str, Any]],
    exactness: str,
    estimate_mode: str,
) -> dict[str, Any]:
    exact_case = exactness == "exact_item" or estimate_mode == "exact_item"
    exact = _exact_macro_breakdown(normalized_evidence) if exact_case else None
    if exact is not None:
        return exact

    component_breakdown = list(answer_payload.get("component_breakdown") or [])
    if not component_breakdown:
        return {
            "protein_g": None,
            "carb_g": None,
            "fat_g": None,
            "macro_source": "unavailable",
            "macro_confidence": "low",
            "macro_status": "unavailable",
            "macro_kcal": None,
            "component_macro_coverage": "empty",
        }

    protein = 0
    carb = 0
    fat = 0
    with_macro = 0
    for component in component_breakdown:
        if not isinstance(component, dict):
            continue
        component_protein = _safe_int(component.get("protein_g"))
        component_carb = _safe_int(component.get("carb_g"))
        component_fat = _safe_int(component.get("fat_g"))
        if any(value > 0 for value in (component_protein, component_carb, component_fat)):
            with_macro += 1
        protein += component_protein
        carb += component_carb
        fat += component_fat

    if with_macro <= 0:
        status = (
            "unavailable"
            if exact_case or estimate_mode in {"heuristic_fallback", "llm_only"} or exactness in {"best_effort", "unknown"}
            else "low_confidence_derived"
        )
        return {
            "protein_g": None if status == "unavailable" else protein or None,
            "carb_g": None if status == "unavailable" else carb or None,
            "fat_g": None if status == "unavailable" else fat or None,
            "macro_source": "unavailable" if status == "unavailable" else "derived_from_components",
            "macro_confidence": "low",
            "macro_status": status,
            "macro_kcal": None if status == "unavailable" else protein * 4 + carb * 4 + fat * 9,
            "component_macro_coverage": "none",
        }

    coverage = "complete" if with_macro == len(component_breakdown) else "partial"
    confidence = "medium" if coverage == "complete" and estimate_mode == "anchored_component" else "low"
    status = "available" if coverage == "complete" else "low_confidence_derived"
    return {
        "protein_g": protein,
        "carb_g": carb,
        "fat_g": fat,
        "macro_source": "derived_from_components",
        "macro_confidence": confidence,
        "macro_status": status,
        "macro_kcal": protein * 4 + carb * 4 + fat * 9,
        "component_macro_coverage": coverage,
    }


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _round_macro(value: float) -> int:
    return max(0, int(round(value)))


def _macro_unavailable(*, coverage: str, confidence: str = "low") -> dict[str, Any]:
    return {
        "protein_g": None,
        "carb_g": None,
        "fat_g": None,
        "macro_source": "unavailable",
        "macro_confidence": confidence,
        "macro_status": "unavailable",
        "macro_kcal": None,
        "component_macro_coverage": coverage,
        "macro_reconciled": False,
        "reconciliation_scale": None,
    }


def reconcile_macro_breakdown(
    *,
    raw_macro_breakdown: dict[str, Any],
    answer_payload: dict[str, Any],
    exactness: str,
    estimate_mode: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    kcal = _safe_float(answer_payload.get("estimated_kcal"))
    kcal_low = _safe_float(answer_payload.get("kcal_low"))
    kcal_high = _safe_float(answer_payload.get("kcal_high"))
    raw_macro_kcal = _safe_float(raw_macro_breakdown.get("macro_kcal"))
    source = str(raw_macro_breakdown.get("macro_source") or "unavailable")
    coverage = str(raw_macro_breakdown.get("component_macro_coverage") or "none")
    exact_case = exactness == "exact_item" or estimate_mode == "exact_item"
    heuristic_case = exactness in {"best_effort", "unknown"} or estimate_mode in {"heuristic_fallback", "llm_only"}

    meta: dict[str, Any] = {
        "raw_macro_kcal": int(raw_macro_kcal) if raw_macro_kcal > 0 else None,
        "display_macro_kcal": None,
        "delta_kcal": None,
        "delta_pct": None,
        "macro_reconciled": False,
        "reconciliation_scale": None,
        "macro_source_display": "unavailable",
        "macro_band_consistent": None,
    }

    if source == "exact_label":
        display = dict(raw_macro_breakdown)
        display["macro_reconciled"] = False
        display["reconciliation_scale"] = None
        meta["display_macro_kcal"] = int(raw_macro_kcal) if raw_macro_kcal > 0 else None
        meta["macro_source_display"] = "exact_label"
        return display, meta

    if raw_macro_kcal <= 0 or kcal <= 0:
        return _macro_unavailable(coverage=coverage), meta

    band_present = kcal_low > 0 and kcal_high > 0 and kcal_high >= kcal_low
    band_consistent = (not band_present) or (kcal_low <= raw_macro_kcal <= kcal_high)
    delta_kcal = abs(raw_macro_kcal - kcal)
    delta_pct = delta_kcal / kcal if kcal > 0 else 1.0
    meta["delta_kcal"] = int(delta_kcal)
    meta["delta_pct"] = round(delta_pct, 4)
    meta["macro_band_consistent"] = band_consistent

    if heuristic_case:
        if coverage != "complete" or not band_consistent or delta_pct > CONSISTENT_DELTA_PCT:
            return _macro_unavailable(coverage=coverage), meta
        display = dict(raw_macro_breakdown)
        display["macro_source"] = "derived_consistent"
        display["macro_reconciled"] = False
        display["reconciliation_scale"] = 1.0
        meta["display_macro_kcal"] = int(raw_macro_kcal)
        meta["macro_source_display"] = "derived_consistent"
        return display, meta

    if exact_case:
        return _macro_unavailable(coverage=coverage), meta

    if delta_pct <= CONSISTENT_DELTA_PCT:
        display = dict(raw_macro_breakdown)
        display["macro_source"] = "derived_consistent"
        display["macro_reconciled"] = False
        display["reconciliation_scale"] = 1.0
        meta["display_macro_kcal"] = int(raw_macro_kcal)
        meta["macro_source_display"] = "derived_consistent"
        return display, meta

    if delta_pct <= RECONCILE_DELTA_PCT:
        scale = kcal / raw_macro_kcal
        protein = _round_macro(_safe_float(raw_macro_breakdown.get("protein_g")) * scale)
        carb = _round_macro(_safe_float(raw_macro_breakdown.get("carb_g")) * scale)
        fat = _round_macro(_safe_float(raw_macro_breakdown.get("fat_g")) * scale)
        display_kcal = protein * 4 + carb * 4 + fat * 9
        display = dict(raw_macro_breakdown)
        display.update(
            {
                "protein_g": protein,
                "carb_g": carb,
                "fat_g": fat,
                "macro_kcal": display_kcal,
                "macro_source": "derived_reconciled",
                "macro_confidence": raw_macro_breakdown.get("macro_confidence") or "low",
                "macro_status": "available",
                "macro_reconciled": True,
                "reconciliation_scale": round(scale, 4),
            }
        )
        meta["display_macro_kcal"] = display_kcal
        meta["macro_reconciled"] = True
        meta["reconciliation_scale"] = round(scale, 4)
        meta["macro_source_display"] = "derived_reconciled"
        return display, meta

    return _macro_unavailable(coverage=coverage), meta
