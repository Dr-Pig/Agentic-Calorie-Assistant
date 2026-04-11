from __future__ import annotations

import re
import unicodedata
from typing import Any

from .nutrition_resolution_prompt import (
    VALID_DECISIONS,
    VALID_ORIGINS,
)


def _normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def normalize_food_origin(value: str) -> tuple[str, str]:
    raw = _normalize_text(value)
    aliases = {
        "generic_common": {"generic_common", "generic", "common"},
        "restaurant_chain": {"restaurant_chain", "chain_restaurant", "chain"},
        "convenience_packaged": {"convenience_packaged", "packaged", "convenience"},
        "customizable_drink": {"customizable_drink", "drink_custom", "drink"},
        "customizable_bowl": {"customizable_bowl", "bowl_custom", "bowl"},
        "home_private": {"home_private", "home_cooked", "private"},
    }
    for canonical, variants in aliases.items():
        if raw in variants:
            return canonical, value
    return "generic_common", value


def infer_dish_structure(
    *,
    food_origin: str,
    food_class: str,
    components: list[str],
    user_text: str,
) -> str:
    lowered = _normalize_text(user_text).lower()
    if food_origin == "customizable_drink":
        return "customizable_drink"
    if food_origin == "customizable_bowl":
        return "customizable_bowl"
    if food_origin in {"restaurant_chain", "convenience_packaged"} and len(components) <= 1:
        return "single_exact_item"
    if food_class in {"ramen", "rice_bowl", "staple_meal"} and len(components) >= 3:
        return "composite_cooked_dish"
    if any(token in lowered for token in ["fried", "soup", "latte", "bowl", "set"]) and len(components) >= 3:
        return "composite_cooked_dish"
    return "multi_component_simple"


def augment_followup_metadata(parsed: dict[str, Any]) -> dict[str, Any]:
    updated = dict(parsed)
    followup_question = str(updated.get("followup_question") or "").strip()
    blocking_slots = [str(item) for item in updated.get("blocking_slots", []) if str(item).strip()]
    missing_slots = [str(item) for item in updated.get("missing_slots", []) if str(item).strip()]
    updated["follow_up_needed"] = bool(followup_question)
    if followup_question:
        if blocking_slots:
            updated["follow_up_reasoning"] = f"blocking_slots:{', '.join(blocking_slots)}"
        elif missing_slots:
            updated["follow_up_reasoning"] = f"missing_slots:{', '.join(missing_slots)}"
        else:
            updated["follow_up_reasoning"] = "nutrition_material_uncertainty"
    else:
        updated["follow_up_reasoning"] = ""
    return updated


def _parse_control_lines(text: str) -> tuple[dict[str, Any], str]:
    normalized = _normalize_text(text)
    lines = [line.rstrip() for line in normalized.splitlines()]
    fields = {
        "decision": "DIRECT_ANSWER",
        "external_data_query": "",
        "food_origin": "generic_common",
        "food_class": "",
        "confidence": "medium",
        "invalid_decision": False,
    }
    index = 0
    while index < len(lines):
        line = lines[index]
        upper = line.upper()
        if upper.startswith("DECISION:"):
            raw = line.split(":", 1)[1].strip().upper()
            if raw in VALID_DECISIONS:
                fields["decision"] = raw
            else:
                fields["invalid_decision"] = True
                for candidate in VALID_DECISIONS:
                    if candidate in raw:
                        fields["decision"] = candidate
                        break
            index += 1
            continue
        if upper.startswith("EXTERNAL_DATA_QUERY:"):
            fields["external_data_query"] = line.split(":", 1)[1].strip()
            index += 1
            continue
        if upper.startswith("FOOD_ORIGIN:"):
            raw = line.split(":", 1)[1].strip()
            if raw in VALID_ORIGINS:
                fields["food_origin"] = raw
            index += 1
            continue
        if upper.startswith("FOOD_CLASS:"):
            fields["food_class"] = line.split(":", 1)[1].strip()
            index += 1
            continue
        if upper.startswith("CONFIDENCE:"):
            fields["confidence"] = line.split(":", 1)[1].strip().lower() or "medium"
            index += 1
            continue
        break
    return fields, "\n".join(lines[index:]).strip()


def _extract_section(body: str, heading: str, next_headings: list[str]) -> str:
    pattern = rf"{re.escape(heading)}\s*(.*?)(?:{'|'.join(re.escape(item) for item in next_headings)}|\Z)"
    match = re.search(pattern, body, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_first_section(body: str, headings: list[str], next_headings: list[str]) -> tuple[str, str]:
    for heading in headings:
        section = _extract_section(body, heading, next_headings)
        if section:
            return heading, section
    return "", ""


def _parse_range_number(text: str) -> int:
    values = [int(value) for value in re.findall(r"\d+", text or "")]
    if not values:
        return 0
    return int(round(sum(values) / len(values)))


def _parse_components(section: str) -> list[str]:
    items: list[str] = []
    for line in _normalize_text(section).splitlines():
        cleaned = line.strip().lstrip("-").strip()
        if cleaned:
            items.append(cleaned)
    return items


def _split_component_line(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"[??嚗?]", text) if item.strip()]


def _parse_macro(section: str, label: str) -> int:
    match = re.search(rf"{label}\s*[:嚗?\s*([0-9]+)", section or "", flags=re.IGNORECASE)
    return int(match.group(1)) if match else 0


def _fallback_kcal_from_body(body: str) -> int:
    match = re.search(r"(?:kcal|calories?)\s*[:嚗?\s*([^\r\n]+)", body or "", flags=re.IGNORECASE)
    if match:
        return _parse_range_number(match.group(1))
    return _parse_range_number(body)


def _fallback_components_from_body(body: str) -> list[str]:
    first_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
    return _split_component_line(first_line)


def _fallback_followup_from_body(body: str) -> str:
    question_line = next((line.strip() for line in body.splitlines() if "?" in line), "")
    return question_line


def parse_answer_text(raw_text: str) -> dict[str, Any]:
    fields, body = _parse_control_lines(raw_text)
    section_headings = {
        "title": ["Title"],
        "components": ["Components"],
        "macro": ["Macros"],
        "kcal": ["Calories", "Kcal"],
        "uncertainty": ["Uncertainty"],
        "blockers": ["Blocking info"],
        "followup": ["Follow-up", "Question"],
    }
    title_heading, title_section = _extract_first_section(
        body, section_headings["title"], [item for items in section_headings.values() for item in items if item not in section_headings["title"]]
    )
    _, components_section = _extract_first_section(
        body, section_headings["components"], [item for items in section_headings.values() for item in items if item not in section_headings["components"]]
    )
    _, macro_section = _extract_first_section(
        body, section_headings["macro"], [item for items in section_headings.values() for item in items if item not in section_headings["macro"]]
    )
    _, kcal_section = _extract_first_section(
        body, section_headings["kcal"], [item for items in section_headings.values() for item in items if item not in section_headings["kcal"]]
    )
    _, uncertainty_section = _extract_first_section(
        body, section_headings["uncertainty"], [item for items in section_headings.values() for item in items if item not in section_headings["uncertainty"]]
    )
    _, blockers_section = _extract_first_section(
        body, section_headings["blockers"], [item for items in section_headings.values() for item in items if item not in section_headings["blockers"]]
    )
    _, followup_section = _extract_first_section(
        body, section_headings["followup"], [item for items in section_headings.values() for item in items if item not in section_headings["followup"]]
    )

    title = title_section.strip()
    components = _parse_components(components_section) or _fallback_components_from_body(body)
    followup = followup_section.strip() or _fallback_followup_from_body(body)
    kcal = _parse_range_number(kcal_section) or _fallback_kcal_from_body(body)
    parse_mode = "strict" if any([title_heading, components_section, macro_section, kcal_section]) else "sentence_fallback"
    return {
        **fields,
        "title": title.strip(),
        "components": components,
        "protein_g": _parse_macro(macro_section, "protein"),
        "carb_g": _parse_macro(macro_section, "carb"),
        "fat_g": _parse_macro(macro_section, "fat"),
        "estimated_kcal": kcal,
        "uncertainty_factors": _parse_components(uncertainty_section),
        "blockers": _parse_components(blockers_section),
        "followup_question": followup,
        "body": body,
        "parse_mode": parse_mode,
    }
