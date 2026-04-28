from __future__ import annotations

from typing import Any

from app.schemas import ComponentEstimate, NutritionEstimateResult

from .nutrition_resolution_sanitizer import normalize_confidence, sanitize_int

VALID_RESULT_RESOLUTION_MODES = {
    "exact_label_finalize",
    "near_exact_finalize",
    "component_estimate",
    "provisional_estimate",
    "cannot_estimate_yet",
}

VALID_RESULT_EXACTNESS = {
    "exact_item",
    "near_exact",
    "calibrated_estimate",
    "component_grounded",
    "best_effort",
    "unknown",
}


def build_component_estimates(
    components: list[str],
    *,
    source: str = "llm",
    component_breakdown: list[dict[str, Any]] | None = None,
) -> list[ComponentEstimate]:
    by_name = {
        str(item.get("name") or item.get("title") or "").strip(): item
        for item in (component_breakdown or [])
        if str(item.get("name") or item.get("title") or "").strip()
    }
    return [
        ComponentEstimate(
            name=name,
            source=source,
            confidence_tier="low",
            quantity_hint=str(by_name.get(name, {}).get("quantity_hint") or by_name.get(name, {}).get("portion_hint") or "").strip() or None,
            reason=str(by_name.get(name, {}).get("reason") or "").strip(),
            evidence_ids=[str(item) for item in by_name.get(name, {}).get("evidence_ids", []) if str(item).strip()],
            estimated_kcal=sanitize_int(by_name.get(name, {}).get("estimated_kcal")),
            protein_g=sanitize_int(by_name.get(name, {}).get("protein_g")),
            carb_g=sanitize_int(by_name.get(name, {}).get("carb_g")),
            fat_g=sanitize_int(by_name.get(name, {}).get("fat_g")),
        )
        for name in components
        if name
    ]


def nutrition_result_from_primary(primary_result: dict[str, Any]) -> NutritionEstimateResult:
    unresolved = [str(item) for item in primary_result.get("unresolved_info", []) if str(item).strip()]
    resolution_mode = _normalize_result_resolution_mode(primary_result.get("resolution_mode"))
    basis = str(primary_result.get("resolution_basis") or "component_model")
    exactness = _normalize_result_exactness(primary_result.get("exactness"))
    return NutritionEstimateResult(
        resolution_mode=resolution_mode,  # type: ignore[arg-type]
        resolution_basis=basis,  # type: ignore[arg-type]
        confidence=normalize_confidence(primary_result.get("confidence")),
        exactness=exactness,  # type: ignore[arg-type]
        answer_payload=dict(primary_result.get("answer_payload") or {}),
        unresolved_info=unresolved,
        state_transition_hint=primary_result.get("state_transition_hint"),
    )


def _normalize_result_resolution_mode(value: Any) -> str:
    normalized = str(value or "").strip()
    if normalized in VALID_RESULT_RESOLUTION_MODES:
        return normalized
    aliases = {
        "estimated": "component_estimate",
        "estimate": "component_estimate",
        "rough_estimate": "provisional_estimate",
    }
    return aliases.get(normalized, "cannot_estimate_yet")


def _normalize_result_exactness(value: Any) -> str:
    normalized = str(value or "").strip()
    return normalized if normalized in VALID_RESULT_EXACTNESS else "unknown"
