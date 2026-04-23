"""Partial grounding packet builder extracted from evidence_assembly."""
from __future__ import annotations

from typing import Any

from app.nutrition.application.context_normalizer import canonicalize_lookup_text, lookup_key
from app.nutrition.application.evidence_normalizer import source_class_for_item
from app.nutrition.application.evidence_normalizer import infer_expected_components, infer_store_hint
from app.nutrition.application.evidence_normalizer import split_evidence_lanes
from app.nutrition.application.evidence_selector import summarize_selected_evidence


def build_partial_grounding_packet(
    *,
    user_input: str,
    planner_foods: list[str] | None,
    selected_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    expected_components = infer_expected_components(user_input=user_input, planner_foods=planner_foods)
    store_hint = infer_store_hint(user_input)
    anchored_components: list[dict[str, Any]] = []
    missing_components: list[dict[str, Any]] = []
    lanes = split_evidence_lanes(selected_evidence)
    exact_truth_present = bool(lanes["exact_lane"])
    evidence_haystacks: list[tuple[dict[str, Any], str]] = []
    for item in selected_evidence:
        haystack_parts = [
            str(item.get("title") or item.get("name") or ""),
            *[str(alias) for alias in item.get("aliases", []) if str(alias).strip()],
            *[str(comp) for comp in item.get("common_components", []) if str(comp).strip()],
            str(item.get("brand") or ""),
            str(item.get("content") or ""),
            str(item.get("snippet") or ""),
        ]
        evidence_haystacks.append((item, canonicalize_lookup_text(" ".join(haystack_parts))))
    for index, component in enumerate(expected_components):
        component_key = lookup_key(component)
        matched_item: dict[str, Any] | None = None
        for item, haystack in evidence_haystacks:
            if component_key and component_key in lookup_key(haystack):
                matched_item = item
                break
        if matched_item is not None:
            anchored_components.append(
                {
                    "name": component,
                    "evidence_title": str(matched_item.get("title") or matched_item.get("name") or ""),
                    "evidence_role": str(matched_item.get("evidence_role") or "unknown"),
                    "identity_confidence": str(matched_item.get("identity_confidence") or matched_item.get("match_confidence") or "none"),
                    "source_class": source_class_for_item(matched_item),
                }
            )
        else:
            missing_components.append(
                {
                    "name": component,
                    "importance": "high" if index < 2 else "medium",
                }
            )
    grounded_count = len(anchored_components)
    missing_count = len(missing_components)
    if exact_truth_present:
        grounding_quality = "high"
    elif grounded_count and missing_count:
        grounding_quality = "partial"
    elif grounded_count:
        grounding_quality = "medium"
    else:
        grounding_quality = "low"
    return {
        "expected_components": expected_components,
        "store_hint": store_hint,
        "store_header_removed": bool(store_hint),
        "exact_lane_candidates": summarize_selected_evidence(lanes["exact_lane"], limit=5),
        "anchor_lane_candidates": summarize_selected_evidence(lanes["anchor_lane"], limit=5),
        "template_lane_hits": summarize_selected_evidence(lanes["template_lane"], limit=5),
        "anchored_components": anchored_components,
        "missing_components": missing_components,
        "grounded_component_count": grounded_count,
        "missing_component_count": missing_count,
        "grounding_quality": grounding_quality,
        "exact_truth_present": exact_truth_present,
    }
