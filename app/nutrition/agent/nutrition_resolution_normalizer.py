from __future__ import annotations
import json
import re
from typing import Any

from .nutrition_resolution_preprocess import default_normalized_answer as _default_normalized_answer
from .nutrition_resolution_preprocess import preprocess_raw_answer as _preprocess_raw_answer
from .nutrition_resolution_prompt import (
    VALID_ACTION_TAKEN,
    VALID_CONFIDENCE_TIERS,
    VALID_ESTIMATE_MODES,
    VALID_EXACTNESS,
    VALID_PRIVATE_INFO_RISK,
    VALID_RESOLUTION_BASES,
    VALID_RESOLUTION_MODES,
    VALID_RESPONSE_MODE_HINTS,
)
from .nutrition_resolution_result import build_component_estimates, nutrition_result_from_primary
from .nutrition_resolution_sanitizer import (
    normalize_confidence as _normalize_confidence,
    sanitize_int as _sanitize_int,
    validate_structured_answer as _validate_structured_answer,
)
from .nutrition_resolution_parser import (
    _normalize_text,
    augment_followup_metadata,
    infer_dish_structure,
    normalize_food_origin,
    parse_answer_text,
)
def normalize_structured_answer(
    raw: dict[str, Any] | str | None,
    *,
    user_text: str,
    risk_packet: dict[str, Any] | None = None,
    meal_template: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del risk_packet, meal_template
    if raw is None:
        return _default_normalized_answer(user_text)
    if isinstance(raw, str):
        text = raw.strip()
        fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            text = "\n".join(chunk.strip() for chunk in fenced if chunk.strip())
        try:
            raw = json.loads(text)
        except Exception:
            raw = parse_answer_text(text)
    if not isinstance(raw, dict):
        return _default_normalized_answer(user_text)
    if raw.get("_raw_text"):
        raw = parse_answer_text(str(raw.get("_raw_text") or ""))
    raw = _preprocess_raw_answer(raw)

    raw = _validate_structured_answer(raw)

    answer_payload = raw.get("answer_payload")
    if isinstance(answer_payload, dict):
        for key, value in answer_payload.items():
            if key not in raw:
                raw[key] = value
    resolution_mode = str(raw.get("resolution_mode") or "").strip()
    resolution_basis = str(raw.get("resolution_basis") or "").strip()
    if "estimate_confidence_tier" not in raw:
        raw["estimate_confidence_tier"] = str(raw.get("confidence") or "low")
    if "estimated_kcal" not in raw:
        raw["estimated_kcal"] = raw.get("provisional_kcal") or raw.get("calorie_kcal") or 0
    if "protein_g" not in raw:
        raw["protein_g"] = raw.get("provisional_protein_g") or 0
    if "carb_g" not in raw:
        raw["carb_g"] = raw.get("provisional_carb_g") or 0
    if "fat_g" not in raw:
        raw["fat_g"] = raw.get("provisional_fat_g") or 0
    if "uncertainty_factors" not in raw and raw.get("reason"):
        raw["uncertainty_factors"] = [str(raw.get("reason"))]
    if "why_not_exact" not in raw and raw.get("reason"):
        raw["why_not_exact"] = str(raw.get("reason"))

    food_origin, raw_food_origin = normalize_food_origin(str(raw.get("food_origin") or ""))
    private_info_risk = raw.get("private_info_risk") if raw.get("private_info_risk") in VALID_PRIVATE_INFO_RISK else "low"
    components: list[str] = []
    component_portion_hints: dict[str, str] = {}
    for item in raw.get("components", []):
        if isinstance(item, dict):
            name = str(item.get("name", "")).strip()
            if name:
                components.append(name)
                hint = str(item.get("portion_hint", "")).strip()
                if hint:
                    component_portion_hints[name] = hint
        else:
            cleaned = str(item).strip()
            if cleaned:
                components.append(cleaned)
    itemized_payloads: list[dict[str, Any]] = []
    component_breakdown: list[dict[str, Any]] = []
    for item in raw.get("items", []):
        if not isinstance(item, dict):
            continue
        item_title = str(item.get("title") or item.get("name") or "").strip()
        if not item_title:
            continue
        item_components = item.get("components")
        if not isinstance(item_components, list) or not item_components:
            item_components = [item_title]
        normalized_item = {
            "title": item_title,
            "components": [str(comp).strip() for comp in item_components if str(comp).strip()],
            "estimated_kcal": _sanitize_int(item.get("estimated_kcal", item.get("calories_kcal"))),
            "protein_g": _sanitize_int(item.get("protein_g")),
            "carb_g": _sanitize_int(item.get("carb_g", item.get("carbs_g"))),
            "fat_g": _sanitize_int(item.get("fat_g")),
            "reason": str(item.get("reason") or item.get("basis") or "").strip(),
            "evidence_ids": [str(entry) for entry in item.get("evidence_ids", []) if str(entry).strip()],
        }
        itemized_payloads.append(normalized_item)
        component_breakdown.append(
            {
                "name": item_title,
                "estimated_kcal": normalized_item["estimated_kcal"],
                "protein_g": normalized_item["protein_g"],
                "carb_g": normalized_item["carb_g"],
                "fat_g": normalized_item["fat_g"],
                "portion_basis": str(
                    item.get("portion_basis")
                    or item.get("portion_hint")
                    or item.get("portion_estimate")
                    or item.get("serving_estimate")
                    or item.get("serving")
                    or ""
                ).strip(),
                "reason": normalized_item["reason"],
                "evidence_ids": normalized_item["evidence_ids"],
                "quantity_hint": str(item.get("portion_hint") or item.get("portion_estimate") or item.get("serving_estimate") or "").strip(),
            }
        )
        if item_title not in components:
            components.append(item_title)
    uncertainty_factors = [str(item).strip() for item in raw.get("uncertainty_factors", []) if str(item).strip()]
    followup_question = str(raw.get("followup_question") or "").strip()
    estimated_kcal = int(raw.get("estimated_kcal") or raw.get("kcal_most_likely") or 0)
    if estimated_kcal <= 0 and itemized_payloads:
        estimated_kcal = sum(int(item.get("estimated_kcal") or 0) for item in itemized_payloads)
    protein_g = int(raw.get("protein_g") or 0)
    carb_g = int(raw.get("carb_g") or 0)
    fat_g = int(raw.get("fat_g") or 0)
    if itemized_payloads:
        if protein_g <= 0:
            protein_g = sum(int(item.get("protein_g") or 0) for item in itemized_payloads)
        if carb_g <= 0:
            carb_g = sum(int(item.get("carb_g") or 0) for item in itemized_payloads)
        if fat_g <= 0:
            fat_g = sum(int(item.get("fat_g") or 0) for item in itemized_payloads)
    evidence_ids_used = [str(item) for item in raw.get("evidence_ids_used", []) if str(item).strip()]
    if not evidence_ids_used:
        seen_ids: set[str] = set()
        for item in itemized_payloads:
            for evidence_id in item.get("evidence_ids", []):
                if evidence_id and evidence_id not in seen_ids:
                    seen_ids.add(evidence_id)
                    evidence_ids_used.append(evidence_id)
    synthesized_answer_payload = dict(raw.get("answer_payload") or {})
    if not synthesized_answer_payload:
        synthesized_answer_payload = {
            "title": str(raw.get("title") or "").strip() or _normalize_text(user_text),
            "components": components,
            "estimated_kcal": estimated_kcal,
            "protein_g": protein_g,
            "carb_g": carb_g,
            "fat_g": fat_g,
            "uncertainty_factors": uncertainty_factors,
            "base_estimated_kcal": raw.get("base_estimated_kcal"),
            "base_protein_g": raw.get("base_protein_g"),
            "base_carb_g": raw.get("base_carb_g"),
            "base_fat_g": raw.get("base_fat_g"),
            "portion_multiplier": raw.get("portion_multiplier", 1.0),
            "portion_reason": str(raw.get("portion_reason") or ""),
            "component_breakdown": component_breakdown,
            "macro_breakdown": {
                "protein_g": protein_g if protein_g > 0 else None,
                "carb_g": carb_g if carb_g > 0 else None,
                "fat_g": fat_g if fat_g > 0 else None,
            },
            "evidence_ids_used": evidence_ids_used,
        }
    if itemized_payloads:
        synthesized_answer_payload["items"] = itemized_payloads
    synthesized_answer_payload.setdefault("component_breakdown", component_breakdown)
    synthesized_answer_payload.setdefault(
        "macro_breakdown",
        {
            "protein_g": protein_g if protein_g > 0 else None,
            "carb_g": carb_g if carb_g > 0 else None,
            "fat_g": fat_g if fat_g > 0 else None,
        },
    )
    synthesized_answer_payload.setdefault("evidence_ids_used", evidence_ids_used)

    normalized = {
        **_default_normalized_answer(user_text),
        "decision": str(raw.get("decision") or "DIRECT_ANSWER"),
        "resolution_mode": resolution_mode or "cannot_estimate_yet",
        "resolution_basis": resolution_basis or "component_model",
        "title": str(raw.get("title") or "").strip() or _normalize_text(user_text),
        "components": components,
        "component_portion_hints": component_portion_hints,
        "protein_g": protein_g,
        "carb_g": carb_g,
        "fat_g": fat_g,
        "kcal_low": int(raw.get("kcal_low") or (estimated_kcal if estimated_kcal > 0 else 0)),
        "kcal_high": int(raw.get("kcal_high") or estimated_kcal),
        "kcal_most_likely": int(raw.get("kcal_most_likely") or estimated_kcal),
        "estimated_kcal": estimated_kcal,
        "uncertainty_factors": uncertainty_factors,
        "blockers": [str(item).strip() for item in raw.get("blockers", []) if str(item).strip()],
        "followup_question": followup_question,
        "body": str(raw.get("body") or ""),
        "parse_mode": str(raw.get("parse_mode") or "structured"),
        "food_origin": food_origin,
        "raw_food_origin": raw_food_origin,
        "private_info_risk": private_info_risk,
        "dish_structure": str(raw.get("dish_structure") or "")
        or infer_dish_structure(
            food_origin=food_origin,
            food_class=str(raw.get("food_class") or "").strip(),
            components=components,
            user_text=user_text,
        ),
        "exactness": str(raw.get("exactness") or "unknown"),
        "estimate_mode": str(raw.get("estimate_mode") or "llm_only"),
        "estimate_confidence_tier": str(raw.get("estimate_confidence_tier") or "low"),
        "why_not_exact": str(raw.get("why_not_exact") or "No deterministic evidence was applied."),
        "why_no_more_tools": str(raw.get("why_no_more_tools") or ""),
        "current_evidence_sufficiency": str(raw.get("current_evidence_sufficiency") or ""),
        "reason_for_not_requesting_tool": str(raw.get("reason_for_not_requesting_tool") or ""),
        "heuristic_dependencies": [str(item) for item in raw.get("heuristic_dependencies", []) if str(item).strip()],
        "action_taken": str(raw.get("action_taken") or ("clarify_before_estimate" if followup_question else "answer_with_uncertainty")),
        "tool_request": str(raw.get("tool_request") or "none"),
        "tool_request_reason": str(raw.get("tool_request_reason") or ""),
        "answer_payload": synthesized_answer_payload,
        "evidence_ids_used": evidence_ids_used,
        "component_breakdown": component_breakdown,
        "unresolved_info": [str(item) for item in raw.get("unresolved_info", []) if str(item).strip()],
        "response_mode_hint": str(raw.get("response_mode_hint") or ("clarify_first" if followup_question else "rough_estimate_ok")),
        "confidence": str(raw.get("confidence") or "low"),
        "missing_slots": [str(item) for item in raw.get("missing_slots", []) if str(item).strip()],
        "blocking_slots": [str(item) for item in raw.get("blocking_slots", []) if str(item).strip()],
        "top_uncertainty_drivers": [str(item) for item in raw.get("top_uncertainty_drivers", []) if str(item).strip()],
        "base_estimated_kcal": raw.get("base_estimated_kcal"),
        "base_protein_g": raw.get("base_protein_g"),
        "base_carb_g": raw.get("base_carb_g"),
        "base_fat_g": raw.get("base_fat_g"),
        "portion_multiplier": raw.get("portion_multiplier", 1.0),
        "portion_reason": str(raw.get("portion_reason") or ""),
        "component_estimates": build_component_estimates(components, component_breakdown=component_breakdown),
    }
    return augment_followup_metadata(normalized)
