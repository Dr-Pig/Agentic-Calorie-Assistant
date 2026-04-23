from __future__ import annotations

import json
import re
from typing import Any

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
from .nutrition_resolution_parser import (
    _normalize_text,
    augment_followup_metadata,
    infer_dish_structure,
    normalize_food_origin,
    parse_answer_text,
)
from app.schemas import ComponentEstimate, NutritionEstimateResult


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
            estimated_kcal=_sanitize_int(by_name.get(name, {}).get("estimated_kcal")),
            protein_g=_sanitize_int(by_name.get(name, {}).get("protein_g")),
            carb_g=_sanitize_int(by_name.get(name, {}).get("carb_g")),
            fat_g=_sanitize_int(by_name.get(name, {}).get("fat_g")),
        )
        for name in components
        if name
    ]


def _sanitize_literal(value: Any, valid_set: set[str], default: str) -> str:
    """Sanitize a literal value to one of the valid values."""
    if value is None:
        return default
    normalized = str(value).strip().lower()
    return normalized if normalized in valid_set else default


def _sanitize_int(value: Any, default: int = 0) -> int:
    """Sanitize an integer value."""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _sanitize_list(value: Any, max_length: int = 50) -> list:
    """Sanitize a list value."""
    if value is None:
        return []
    if not isinstance(value, list):
        return [value] if value else []
    return value[:max_length]


def _validate_structured_answer(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Strictly validate and sanitize LLM structured answer output.

    This prevents:
    - Invalid literal values causing Pydantic validation errors
    - Type mismatches in downstream processing
    - Injection attacks through prompt injection

    Returns:
        Sanitized dict with all values properly typed
    """
    if not isinstance(raw, dict):
        return {}

    sanitized: dict[str, Any] = {}
    literal_fields = {
        "action_taken": (VALID_ACTION_TAKEN, "clarify_before_estimate"),
        "confidence": (VALID_CONFIDENCE_TIERS, "low"),
        "exactness": (VALID_EXACTNESS, "unknown"),
        "resolution_mode": (VALID_RESOLUTION_MODES, "cannot_estimate_yet"),
        "resolution_basis": (VALID_RESOLUTION_BASES, "component_model"),
        "response_mode_hint": (VALID_RESPONSE_MODE_HINTS, "clarify_first"),
        "estimate_mode": (VALID_ESTIMATE_MODES, "llm_only"),
    }
    int_fields = {"protein_g", "carb_g", "fat_g", "estimated_kcal", "kcal_low", "kcal_high", "kcal_most_likely"}
    list_fields = {
        "components",
        "items",
        "uncertainty_factors",
        "blockers",
        "missing_slots",
        "blocking_slots",
        "unresolved_info",
        "top_uncertainty_drivers",
        "heuristic_dependencies",
    }
    bool_fields = {"follow_up_needed", "clarification_blocking"}
    string_fields = {
        "title",
        "tool_request",
        "state_transition_hint",
        "followup_question",
        "follow_up_reasoning",
        "tool_request_reason",
        "why_no_more_tools",
        "current_evidence_sufficiency",
        "reason_for_not_requesting_tool",
        "portion_reason",
        "why_not_exact",
    }

    for key, value in raw.items():
        if key in literal_fields:
            valid_set, default = literal_fields[key]
            sanitized[key] = _normalize_confidence(value) if key == "confidence" else _sanitize_literal(value, valid_set, default)
        elif key in int_fields:
            sanitized[key] = _sanitize_int(value)
        elif key in list_fields:
            sanitized[key] = _sanitize_list(value)
        elif key in bool_fields:
            sanitized[key] = bool(value)
        elif key in string_fields:
            sanitized[key] = str(value or "").strip()[:500]
        elif key == "portion_multiplier":
            try:
                sanitized[key] = float(value if value is not None else 1.0)
            except (TypeError, ValueError):
                sanitized[key] = 1.0
        elif key == "answer_payload":
            sanitized[key] = dict(value or {})
        else:
            sanitized[key] = value

    sanitized["_raw_validated"] = True
    return sanitized


def _preprocess_raw_answer(raw: dict[str, Any]) -> dict[str, Any]:
    data = dict(raw or {})
    if not data:
        return data

    alias_pairs = {
        "total_kcal": "estimated_kcal",
        "calories_kcal": "estimated_kcal",
        "calorie_kcal": "estimated_kcal",
        "provisional_kcal": "estimated_kcal",
        "calories_low": "kcal_low",
        "calories_high": "kcal_high",
        "carbs_g": "carb_g",
        "provisional_protein_g": "protein_g",
        "provisional_carb_g": "carb_g",
        "provisional_fat_g": "fat_g",
    }
    for alias, canonical in alias_pairs.items():
        if canonical not in data and alias in data:
            data[canonical] = data[alias]

    resolution_basis_aliases = {
        "recognizable_dish_structure": "component_model",
        "named_dish_structure": "component_model",
        "named_dish_components": "component_model",
        "named_dish_with_portion_clue": "component_model",
        "cultural_dish_knowledge": "component_model",
        "anchored_evidence_with_conservative_missing": "component_model",
        "portion_clue_estimate": "component_model",
        "menu_derived_estimate": "official_source_evidence",
        "exact_label_match": "exact_item_evidence",
        "official_menu_match": "official_source_evidence",
    }
    basis = str(data.get("resolution_basis") or "").strip()
    if basis and basis not in VALID_RESOLUTION_BASES:
        data["resolution_basis"] = resolution_basis_aliases.get(basis, "component_model")

    if "components" not in data and isinstance(data.get("items"), list):
        data["components"] = [item.get("title") or item.get("name") for item in data["items"] if isinstance(item, dict)]

    if isinstance(data.get("total_macros"), dict):
        total_macros = dict(data.get("total_macros") or {})
        if "protein_g" not in data and total_macros.get("protein_g") is not None:
            data["protein_g"] = total_macros.get("protein_g")
        if "carb_g" not in data:
            carb_value = total_macros.get("carb_g", total_macros.get("carbs_g"))
            if carb_value is not None:
                data["carb_g"] = carb_value
        if "fat_g" not in data and total_macros.get("fat_g") is not None:
            data["fat_g"] = total_macros.get("fat_g")

    if isinstance(data.get("calories"), dict):
        calories = dict(data.get("calories") or {})
        if "estimated_kcal" not in data and calories.get("total") is not None:
            data["estimated_kcal"] = calories.get("total")
        if "kcal_low" not in data and calories.get("low") is not None:
            data["kcal_low"] = calories.get("low")
        if "kcal_high" not in data and calories.get("high") is not None:
            data["kcal_high"] = calories.get("high")
        if "confidence" not in data and calories.get("confidence") is not None:
            data["confidence"] = calories.get("confidence")

    if isinstance(data.get("macros"), dict):
        macros = dict(data.get("macros") or {})
        if "protein_g" not in data:
            protein_value = macros.get("protein_g", macros.get("protein"))
            if protein_value is not None:
                data["protein_g"] = protein_value
        if "carb_g" not in data:
            carb_value = macros.get("carb_g", macros.get("carbs_g", macros.get("carbs")))
            if carb_value is not None:
                data["carb_g"] = carb_value
        if "fat_g" not in data:
            fat_value = macros.get("fat_g", macros.get("fat"))
            if fat_value is not None:
                data["fat_g"] = fat_value

    if isinstance(data.get("estimate_confidence"), str) and "confidence" not in data:
        data["confidence"] = data.get("estimate_confidence")

    if isinstance(data.get("nutrition_model"), dict):
        nutrition_model = dict(data.get("nutrition_model") or {})
        if "estimated_kcal" not in data:
            kcal_value = nutrition_model.get(
                "kcal",
                nutrition_model.get(
                    "estimated_kcal",
                    nutrition_model.get("total_kcal", nutrition_model.get("total_calories", nutrition_model.get("calories"))),
                ),
            )
            if kcal_value is not None:
                data["estimated_kcal"] = kcal_value
        macro_source = nutrition_model
        if isinstance(nutrition_model.get("macros"), dict):
            macro_source = dict(nutrition_model.get("macros") or {})
        if "protein_g" not in data:
            protein_value = macro_source.get("protein_g", macro_source.get("protein"))
            if protein_value is not None:
                data["protein_g"] = protein_value
        if "carb_g" not in data:
            carb_value = macro_source.get("carb_g", macro_source.get("carbs_g", macro_source.get("carbs")))
            if carb_value is not None:
                data["carb_g"] = carb_value
        if "fat_g" not in data:
            fat_value = macro_source.get("fat_g", macro_source.get("fat"))
            if fat_value is not None:
                data["fat_g"] = fat_value
        if "items" not in data and isinstance(nutrition_model.get("components"), list):
            items: list[dict[str, Any]] = []
            component_names: list[str] = []
            for item in nutrition_model.get("components") or []:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("item") or item.get("component") or item.get("title") or item.get("name") or "").strip()
                if not title:
                    continue
                component_names.append(title)
                items.append(
                    {
                        "title": title,
                        "components": [title],
                        "estimated_kcal": item.get("kcal", item.get("estimated_kcal", item.get("calories"))),
                        "protein_g": (
                            dict(item.get("macros") or {}).get("protein_g", dict(item.get("macros") or {}).get("protein", item.get("protein_g")))
                            if isinstance(item.get("macros"), dict)
                            else item.get("protein_g", item.get("protein"))
                        ),
                        "carb_g": (
                            dict(item.get("macros") or {}).get("carb_g", dict(item.get("macros") or {}).get("carbs_g", dict(item.get("macros") or {}).get("carbs")))
                            if isinstance(item.get("macros"), dict)
                            else item.get("carb_g", item.get("carbs_g", item.get("carbs")))
                        ),
                        "fat_g": (
                            dict(item.get("macros") or {}).get("fat_g", dict(item.get("macros") or {}).get("fat", item.get("fat_g")))
                            if isinstance(item.get("macros"), dict)
                            else item.get("fat_g", item.get("fat"))
                        ),
                        "portion_hint": item.get("serving") or item.get("serving_size") or item.get("serving_estimate") or item.get("portion_estimate"),
                    }
                )
            if items:
                data["items"] = items
            if "components" not in data and component_names:
                data["components"] = component_names

    if isinstance(data.get("estimate_quality"), str) and "confidence" not in data:
        data["confidence"] = data.get("estimate_quality")

    if "items" not in data and isinstance(data.get("component_breakdown"), list):
        items: list[dict[str, Any]] = []
        component_names: list[str] = []
        for item in data.get("component_breakdown") or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("component") or item.get("title") or item.get("name") or "").strip()
            if not title:
                continue
            component_names.append(title)
            items.append(
                {
                    "title": title,
                    "components": [title],
                    "estimated_kcal": item.get("kcal", item.get("estimated_kcal")),
                    "protein_g": item.get("protein_g"),
                    "carb_g": item.get("carb_g", item.get("carbs_g")),
                    "fat_g": item.get("fat_g"),
                    "portion_hint": item.get("serving_estimate") or item.get("portion_estimate"),
                }
            )
        if items:
            data["items"] = items
        if "components" not in data and component_names:
            data["components"] = component_names

    if "items" not in data and isinstance(data.get("components"), list):
        items: list[dict[str, Any]] = []
        component_names: list[str] = []
        for item in data.get("components") or []:
            if isinstance(item, str):
                title = item.strip()
                if title:
                    component_names.append(title)
                continue
            if not isinstance(item, dict):
                continue
            title = str(item.get("component") or item.get("title") or item.get("name") or "").strip()
            if not title:
                continue
            component_names.append(title)
            macro_source = dict(item.get("macros") or {}) if isinstance(item.get("macros"), dict) else item
            calories_value = item.get("estimated_kcal", item.get("calories", item.get("kcal")))
            if isinstance(calories_value, dict):
                calories_value = calories_value.get("est", calories_value.get("total", calories_value.get("kcal")))
            items.append(
                {
                    "title": title,
                    "components": [title],
                    "estimated_kcal": calories_value,
                    "protein_g": macro_source.get("protein_g", macro_source.get("protein")),
                    "carb_g": macro_source.get("carb_g", macro_source.get("carbs_g", macro_source.get("carbs"))),
                    "fat_g": macro_source.get("fat_g", macro_source.get("fat")),
                    "portion_hint": item.get("portion_hint") or item.get("portion_evidence") or item.get("basis"),
                }
            )
        if items:
            data["items"] = items
        if component_names:
            data["components"] = component_names

    return data


def _default_normalized_answer(user_text: str) -> dict[str, Any]:
    return {
        "title": _normalize_text(user_text),
        "components": [],
        "component_portion_hints": {},
        "protein_g": 0,
        "carb_g": 0,
        "fat_g": 0,
        "kcal_low": 0,
        "kcal_high": 0,
        "kcal_most_likely": 0,
        "estimated_kcal": 0,
        "uncertainty_factors": [],
        "blockers": [],
        "followup_question": "",
        "body": "",
        "parse_mode": "empty",
        "dish_structure": "multi_component_simple",
        "exactness": "unknown",
        "estimate_mode": "llm_only",
        "estimate_confidence_tier": "low",
        "why_not_exact": "No deterministic evidence was applied.",
        "why_no_more_tools": "",
        "current_evidence_sufficiency": "",
        "reason_for_not_requesting_tool": "",
        "heuristic_dependencies": [],
        "action_taken": "clarify_before_estimate",
        "tool_request": "none",
        "tool_request_reason": "",
        "follow_up_needed": False,
        "follow_up_reasoning": "",
        "evidence_ids_used": [],
        "component_breakdown": [],
        "state_transition_hint": "candidate_meal",
        "answer_payload": {},
        "unresolved_info": [],
        "response_mode_hint": "clarify_first",
        "confidence": "low",
    }


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

    # Apply strict validation and sanitization before further processing
    # This prevents invalid literal values (e.g., 'medium_low') from causing Pydantic errors
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


def _normalize_confidence(value: Any) -> str:
    """Normalize confidence value to one of the valid Literal values: high, medium, low."""
    if value is None:
        return "low"
    normalized = str(value).strip().lower()
    if normalized in VALID_CONFIDENCE_TIERS:
        return normalized
    # Handle compound values like 'medium_low', 'medium-high', etc.
    if "medium" in normalized:
        return "medium"
    if "high" in normalized and "low" not in normalized:
        return "high"
    if "low" in normalized and "high" not in normalized:
        return "low"
    # Default to medium for ambiguous cases like 'medium_low', 'mediumhigh', or invalid values
    return "medium"


def nutrition_result_from_primary(primary_result: dict[str, Any]) -> NutritionEstimateResult:
    unresolved = [str(item) for item in primary_result.get("unresolved_info", []) if str(item).strip()]
    resolution_mode = str(primary_result.get("resolution_mode") or "cannot_estimate_yet")
    basis = str(primary_result.get("resolution_basis") or "component_model")
    exactness = str(primary_result.get("exactness") or "unknown").strip()
    return NutritionEstimateResult(
        resolution_mode=resolution_mode,  # type: ignore[arg-type]
        resolution_basis=basis,  # type: ignore[arg-type]
        confidence=_normalize_confidence(primary_result.get("confidence")),
        exactness=exactness,  # type: ignore[arg-type]
        answer_payload=dict(primary_result.get("answer_payload") or {}),
        unresolved_info=unresolved,
        state_transition_hint=primary_result.get("state_transition_hint"),
    )

