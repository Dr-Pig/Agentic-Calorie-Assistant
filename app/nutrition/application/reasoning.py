"""Reasoning state builder extracted from evidence_assembly."""
from __future__ import annotations

from typing import Any

from app.nutrition.application.evidence_normalizer import (
    infer_brand_hint,
    split_evidence_lanes,
    source_class_for_item,
)


def build_reasoning_state(
    *,
    user_input: str,
    selected_evidence: list[dict[str, Any]],
    partial_grounding: dict[str, Any] | None = None,
    meal_template_hit: bool = False,
    used_search: bool = False,
    search_query: str | None = None,
    search_quality: Any = None,
    search_attempt_count: int = 0,
) -> dict[str, Any]:
    user_brand_hint = infer_brand_hint({"title": user_input}, query=user_input).strip()
    lanes = split_evidence_lanes(selected_evidence)
    brand_hints = sorted(
        {
            *{
                str(item.get("brand_hint") or infer_brand_hint(item, query=user_input)).strip()
                for item in selected_evidence
                if str(item.get("brand_hint") or infer_brand_hint(item, query=user_input)).strip()
            },
            *([user_brand_hint] if user_brand_hint else []),
        }
    )
    official_evidence_present = any(source_class_for_item(item) == "web_search_official" for item in selected_evidence)
    identity_conflict_present = len(brand_hints) > 1
    missing_components = list((partial_grounding or {}).get("missing_components") or [])
    template_lane_count = len(lanes["template_lane"]) + (1 if meal_template_hit else 0)
    if lanes["exact_lane"]:
        insufficiency = ""
        coverage_status = "exact_available"
    elif lanes["anchor_lane"]:
        insufficiency = "exact lane empty; anchor evidence only"
        coverage_status = "anchor_only"
    elif template_lane_count > 0:
        insufficiency = "only template scaffold evidence available"
        coverage_status = "template_only"
    else:
        insufficiency = "no usable local evidence"
        coverage_status = "empty"
    observation_summary = {
        "official_hit_count": sum(1 for item in selected_evidence if source_class_for_item(item) == "web_search_official"),
        "identity_hit_count": sum(
            1
            for item in selected_evidence
            if str(item.get("identity_confidence") or item.get("match_confidence") or "none") in {"high", "medium"}
        ),
        "top_conflict_type": "brand_conflict" if identity_conflict_present else "none",
        "coverage_status": coverage_status,
        "why_not_enough_yet": insufficiency,
    }
    return {
        "exact_lane_count": len(lanes["exact_lane"]),
        "anchor_lane_count": len(lanes["anchor_lane"]),
        "template_lane_count": template_lane_count,
        "official_evidence_present": official_evidence_present,
        "brand_detected": bool(brand_hints),
        "brand_hints": brand_hints,
        "identity_conflict_present": identity_conflict_present,
        "missing_high_impact_slots": [str(item.get("name") or "") for item in missing_components if str(item.get("importance") or "") == "high"],
        "search_attempt_count": int(search_attempt_count),
        "last_search_quality": search_quality.get("quality") if isinstance(search_quality, dict) else search_quality,
        "last_search_query": search_query,
        "used_search": used_search,
        "why_current_evidence_is_insufficient": insufficiency,
        "observation_summary": observation_summary,
    }
