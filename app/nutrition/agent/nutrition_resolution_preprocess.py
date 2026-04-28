from __future__ import annotations

from typing import Any

from .nutrition_resolution_parser import _normalize_text


def preprocess_raw_answer(raw: dict[str, Any]) -> dict[str, Any]:
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
    if basis:
        data["resolution_basis"] = resolution_basis_aliases.get(basis, basis)

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


def default_normalized_answer(user_text: str) -> dict[str, Any]:
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
