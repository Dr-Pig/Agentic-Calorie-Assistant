from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from ..schemas import ComponentEstimate, NutritionResolutionResult, TurnIntentResult

VALID_DECISIONS = {"DIRECT_ANSWER", "NEED_EXTERNAL_DATA", "ASK_USER"}
VALID_ORIGINS = {
    "generic_common",
    "restaurant_chain",
    "convenience_packaged",
    "customizable_drink",
    "customizable_bowl",
    "home_private",
}
VALID_PRIVATE_INFO_RISK = {"high", "low"}
VALID_RESOLUTION_MODES = {
    "exact_label_finalize",
    "near_exact_finalize",
    "component_estimate",
    "provisional_estimate",
    "cannot_estimate_yet",
}
VALID_RESOLUTION_BASES = {
    "exact_item_evidence",
    "official_source_evidence",
    "component_model",
    "calibrated_component_model",
}
VALID_EXACTNESS = {
    "exact_item",
    "near_exact",
    "calibrated_estimate",
    "component_grounded",
    "best_effort",
    "unknown",
}
VALID_ACTION_TAKEN = {
    "direct_answer",
    "clarify_before_estimate",
    "answer_with_uncertainty",
    "request_tool",
}
VALID_RESPONSE_MODE_HINTS = {
    "exact_answer",
    "rough_estimate_ok",
    "clarify_first",
}
VALID_ESTIMATE_MODES = {
    "exact_item",
    "anchored_component",
    "heuristic_fallback",
    "llm_only",
}
VALID_CONFIDENCE_TIERS = {"high", "medium", "low"}

PRIMARY_PROMPT = """You are the nutrition reasoning layer for a food estimation assistant.

Responsibilities:
- Read meal link, decision result, active meal context, and selected evidence.
- Decide exactness, whether estimation is possible, and the best nutrition answer payload.
- Return structured reasoning only; do not write the final user-facing reply.

Rules:
- You are the only layer allowed to produce calorie, macro, and component outputs.
- Never invent exact label values unless supported by exact item or official evidence.
- If the meal can only be estimated provisionally, keep unresolved_info and response_mode_hint=rough_estimate_ok.
- If blocking clarification is required, return action_taken=clarify_before_estimate and response_mode_hint=clarify_first.
"""

NUTRITION_RESOLUTION_PROMPT = """You are the nutrition resolution pass for a food estimation assistant.

Your role: Produce the best nutrition estimate by reasoning about food components.

## Evidence Priority

- If `exact_truth_available=true`, treat the case as exact-evidence-first. Do not fall back to component decomposition unless the exact candidates clearly conflict or fail identity.
- If `exact_truth_candidates` or `normalized_evidence` contains a same-item exact menu/product record, prefer that evidence over component decomposition.
- If `generic_drink_packaged_refs=true`, do not treat packaged retail drink records in `normalized_evidence` as the user's exact item. Use them only as weak anchor references for a class-level estimate.
- Treat local exact item evidence as valid exact evidence when brand + core item identity align, even if the user did not specify every optional customization.
- Do not downgrade a standard chain menu item into a generic component estimate just because customizations are hypothetically possible, unless the user explicitly mentioned them or the remaining ambiguity clearly changes calories materially.
- If multiple exact candidates exist, choose the one whose identity modifiers match the user text best, especially temperature words like hot/cold and explicit serving clues like size or cup count.
- Only ask follow-up for a branded exact item when the missing information changes which exact item it is. Do not ask follow-up about optional syrup/milk defaults when a matching default menu item is already supported by evidence.
- When an exact candidate includes kcal/macros and `portion_basis_quality` is strong, default to `resolution_mode=exact_label_finalize`, `resolution_basis=exact_item_evidence`, `exactness=exact_item`, `estimate_mode=exact_item`, and high confidence.
- A medium match-quality exact candidate is still acceptable exact evidence when it is the best same-brand same-item candidate and no stronger contradictory candidate exists.
- If you finalize from the best same-item exact candidate, set `confidence=high` unless the evidence itself contains a material identity contradiction.
- If the user text names a standard branded drink or menu item and the top exact candidate matches brand + core item + temperature, do not invent extra flavor ambiguity unless the evidence itself names a conflicting flavor variant.
- A generic serving basis like `per serving` is still usable exact evidence for a standardized chain item when no contradictory size record is present.
- But `per serving` packaged drink records are not enough to finalize a generic drink-class input like `珍珠奶茶` when the user did not specify brand, package, or size.
- Treat speculative unresolved_info from earlier passes as advisory only. If exact evidence is sufficient, ignore speculative flavor/customization doubts and finalize from the evidence.
- If the user already gave the cup size for a standardized drink, do not ask a follow-up about size again unless the evidence directly contradicts that size.
- If the user did not give the cup size for a standardized drink and different standard sizes would materially change calories, size is a blocking clarification. In that case prefer `action_taken=clarify_before_estimate` over pretending one exact size.
- Exception: for a generic drink class like `珍珠奶茶` without brand or package cues, a class-level estimate with follow-up is usually better than blocking clarification.
- If `generic_drink_customization_present=true`, treat sugar or ice modifiers as enough structure for a class-level anchored estimate even when cup size is still missing.
- If `generic_drink_packaged_refs=true`, prefer `provisional_estimate` or `component_estimate`, not `exact_label_finalize` or `near_exact_finalize`.
- If `generic_drink_packaged_refs=true`, do not anchor the calorie center to low packaged retail values like bottled or canned milk tea unless the user explicitly indicated a packaged drink.
- For a plain branded latte or similar default menu item, do not treat hypothetical seasonal flavors as blocking unless the user actually named a flavored variant.
- Use `estimate_mode=heuristic_fallback` for broad, high-variance dish classes where the estimate mainly comes from world knowledge and dish priors rather than explicit portion anchors. Examples: `滷肉飯`, `咖哩飯`, generic `拉麵`, or self-serve buffet descriptions with missing side dishes.
- Use `estimate_mode=anchored_component` when the estimate is grounded by explicit quantity or component anchors, such as `水餃10顆`, a customized drink with sugar/ice modifiers, or a dish with clear counted components.
- Treat the payload fields `standardized_drink_like`, `portion_clues`, and `size_missing_for_standardized_drink` as high-priority evidence about whether cup size has been specified.
- If `exact_title_match_present=true`, do not ask about combo/set/default side dishes unless the user text itself introduced that ambiguity.
- If you choose `resolution_mode=exact_label_finalize` or `resolution_mode=near_exact_finalize`, the answer is finalized. In that case leave `unresolved_info` empty unless you are also returning `action_taken=clarify_before_estimate`.
- Do not leave advisory refinement notes in `unresolved_info` for exact or near-exact answers. Put low-impact caveats in `uncertainty_factors` instead.

## Critical Decision: Estimate vs Clarify

Before decomposing, use your world knowledge to judge whether the input has enough
specificity to produce a meaningful estimate:

### When to ASK FOLLOW-UP (blocking):
- Input is a bare category word with no dish type or portion clues (e.g., just "憌脫?" with no drink type)
- Home-cooked / family meal with zero description of what was eaten
- The inherent calorie range for this dish type is 2-3x even with best-effort estimate
??action_taken=clarify_before_estimate, response_mode_hint=clarify_first
??unresolved_info: [the single most critical missing item]

### When to PROCEED TO ESTIMATE:
- The dish type is recognizable and a rough range is meaningful (error < 40% of total)
- Input has specific quantity clues (7憿? ?之, ??, ??) even if dish is generic
- Named components or multiple items are present
??Proceed with component decomposition and provide a range estimate
- For broad but common dishes like `滷肉飯`, `咖哩飯`, generic `拉麵`, or buffet-style meals, give a useful provisional estimate first and add one brief follow-up when it would materially narrow the range.
- For explicit count-based cases like `水餃10顆`, prefer a direct anchored estimate without follow-up unless a missing slot would change calories dramatically.

### Brand/Chain Signal ??Request Search:
- Input contains a brand name AND normalized_evidence shows no exact match:
  ??tool_request=search_official_nutrition
  ??tool_request_reason: "Brand detected, searching official nutrition data"
  ??state_transition_hint: "draft_unresolved"

## Core Reasoning Process

For any meal input you choose to estimate, do the following:

### Step 1: Decompose the Dish
Break down into individual food components by dish name, cooking method, and context.
For "?賊??蜈":
- ?賡ㄞ (rice): ~220-280g
- ?賊???(fried chicken cutlet): ~140-180g (chicken breast + breading + oil)
- ?祆? (sauce): ~15-25g
- 瘣/??: ~20-40g

### Step 2: Estimate Portion per Component
Use world knowledge (general Taiwanese/Japanese donburi portions) to estimate ranges.
- Familiar components (?? 憌? ??anchor to base nutrition.
- Uncertain ??use typical range for that component type.

### Step 3: Calculate Macros per Component
- protein_g, carb_g, fat_g per component
- protein/carbs = 4 kcal/g, fat = 9 kcal/g

### Step 4: Compute Total with Range
- kcal_low: conservative (lower portions)
- kcal_most_likely: midpoint
- kcal_high: generous (upper portions)

## Required Output Fields

Return ALL of:
{
  "title": "dish name in Chinese",
  "components": ["component1", "component2", ...],
  "protein_g": number, "carb_g": number, "fat_g": number,
  "kcal_low": number, "kcal_most_likely": number, "kcal_high": number,
  "resolution_mode": "provisional_estimate" (or "exact_label_finalize" if exact evidence),
  "resolution_basis": "calibrated_component_model" (or "exact_item_evidence" if verified),
  "confidence": "high/medium/low",
  "uncertainty_factors": ["factor1", ...],
  "top_uncertainty_drivers": [{"driver": "...", "impact": "high/medium/low"}, ...],
  "unresolved_info": [] (info that could refine estimate),
  "followup_question": "" (only if critical AND easy to provide),
  "action_taken": "answer_with_uncertainty" (or "direct_answer" if confident),
  "response_mode_hint": "rough_estimate_ok",
  "state_transition_hint": "completed_meal",
}

## World Knowledge Reference (typical portions)
- Japanese/Taiwanese donburi rice: 220-280g cooked ??~300-350 kcal
- Fried chicken cutlet (150g raw ??~180g fried): ~350-400 kcal
- Taiwanese sauce (sweet?望硃-based): ~30-50 kcal
- Egg (single): ~70-90 kcal, P:6g C:1g F:5g
- Taiwanese dry noodle (銋暹?暻?: base ~400-500 kcal, size-up adds ~80-200 kcal
- Chaoshou/?? (per piece): ~40-60 kcal
- Boba milk tea (medium, half sugar): ~350-450 kcal
- Shop-style pearl milk tea with pearls and no ice is usually higher than bottled milk tea. For a generic Taiwanese `珍珠奶茶半糖去冰`, a medium-cup class-level estimate often centers around ~450-520 kcal.

## Rules
- NEVER return 0 kcal for a real meal.
- Recognizable dish with uncertain portions ??provide a range.
- resolution_basis=calibrated_component_model for typical dishes.
- resolution_basis=exact_item_evidence only with verified nutrition label.
- List reasoning as uncertainty_factors, not blockers.
- Prefer "provisional_estimate" over "cannot_estimate_yet".
- Follow-up only if missing info is critical AND user can easily provide.
- For broad common dishes with high recipe variance, one short follow-up is usually appropriate after you give the estimate.
- For explicit count-based or tightly bounded anchors, prefer no follow-up and keep uncertainty in the wording.
- For `exact_label_finalize` or `near_exact_finalize` with `action_taken=direct_answer`, set `followup_question=""` and `unresolved_info=[]`.
- For a generic drink class with missing size, prefer `provisional_estimate` plus a brief follow-up instead of `cannot_estimate_yet` when a useful range can still be given.
- For a generic drink class with explicit modifiers like `半糖`, `微糖`, `無糖`, `去冰`, or `少冰`, missing cup size is usually not a blocker. Estimate first, then ask a brief follow-up only to refine.
- If a generic customized drink already has a useful class-level center estimate and the remaining size uncertainty would not invalidate the answer, prefer `followup_question=""` and keep the refinement note inside `uncertainty_factors` instead.
"""


def _normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def render_primary_system_prompt(
    *,
    stable_prompt: str,
    dynamic_addition: dict[str, Any],
    template_context: str,
    driver_context: str,
    latest_log: Any | None,
    planner_result: TurnIntentResult,
    active_meal_context_allowed: bool,
    thin_sanitized_input: str,
    boundary_followup_question: str,
) -> str:
    parts = [stable_prompt.rstrip(), "\n\n[DYNAMIC_SYSTEM_ADDITION]\n", str(dynamic_addition)]
    if latest_log and active_meal_context_allowed:
        display_components = latest_log.components_json or [{"name": latest_log.meal_title, "portion_hint": "1 serving"}]
        parts.extend(
            [
                "\n\n[ACTIVE_MEAL_CONTEXT]\n",
                f"title: {latest_log.meal_title}\n",
                f"latest_kcal: {latest_log.kcal}\n",
                f"components: {display_components}\n",
                f"current_input: {thin_sanitized_input}\n",
                "Use this only because the planner already decided the user is still talking about the same meal.\n",
            ]
        )
    elif planner_result.meal_boundary == "boundary_clarification":
        parts.extend(
            [
                "\n\n[BOUNDARY_NOTE]\n",
                f"If you cannot safely estimate yet, the best clarification direction is: {boundary_followup_question}\n",
                "Do not merge old meal components unless the planner already allowed it.\n",
            ]
        )
    if template_context:
        parts.extend(["\n\n[TEMPLATE_CONTEXT]\n", template_context])
    if driver_context:
        parts.extend(["\n\n[DRIVER_CONTEXT]\n", driver_context])
    return "".join(parts)


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


def suppress_followup_for_exact_match(
    parsed: dict[str, Any],
    *,
    evidence_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    updated = dict(parsed)
    evidence_items = evidence_items or []
    strong_exact = (
        str(updated.get("estimate_mode") or "") == "exact_item"
        or any(
            str(item.get("evidence_role") or "") == "exact_truth"
            and str(item.get("match_confidence") or item.get("identity_confidence") or "") == "high"
            for item in evidence_items
        )
    )
    if not strong_exact:
        return updated
    updated["followup_questions"] = []
    updated["followup_question"] = ""
    updated["top_uncertainty_drivers"] = []
    updated["missing_slots"] = []
    updated["blocking_slots"] = []
    return augment_followup_metadata(updated)


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


def build_component_estimates(components: list[str], *, source: str = "llm") -> list[ComponentEstimate]:
    return [ComponentEstimate(name=name, source=source, confidence_tier="low") for name in components if name]


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
        "estimate_mode": "llm_only",
        "estimate_confidence_tier": "low",
        "why_not_exact": "No deterministic evidence was applied.",
        "heuristic_dependencies": [],
        "action_taken": "clarify_before_estimate",
        "tool_request": "none",
        "tool_request_reason": "",
        "follow_up_needed": False,
        "follow_up_reasoning": "",
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
    raw_had_action_taken = "action_taken" in raw
    raw_had_response_mode_hint = "response_mode_hint" in raw
    raw_had_exactness = "exactness" in raw
    raw_had_estimate_mode = "estimate_mode" in raw
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
    if resolution_mode and not raw_had_action_taken:
        action_map = {
            "exact_label_finalize": "direct_answer",
            "near_exact_finalize": "direct_answer",
            "component_estimate": "direct_answer",
            "provisional_estimate": "answer_with_uncertainty",
            "cannot_estimate_yet": "clarify_before_estimate",
        }
        raw["action_taken"] = action_map.get(resolution_mode, raw.get("action_taken"))
    if resolution_mode and not raw_had_response_mode_hint:
        response_map = {
            "exact_label_finalize": "exact_answer",
            "near_exact_finalize": "exact_answer",
            "component_estimate": "rough_estimate_ok",
            "provisional_estimate": "rough_estimate_ok",
            "cannot_estimate_yet": "clarify_first",
        }
        raw["response_mode_hint"] = response_map.get(resolution_mode, raw.get("response_mode_hint"))
    if resolution_mode and not raw_had_exactness:
        exactness_map = {
            "exact_label_finalize": "exact_item",
            "near_exact_finalize": "near_exact",
            "component_estimate": "component_grounded",
            "provisional_estimate": "best_effort",
            "cannot_estimate_yet": "unknown",
        }
        raw["exactness"] = exactness_map.get(resolution_mode, raw.get("exactness"))
    if resolution_basis and not raw_had_estimate_mode:
        estimate_mode_map = {
            "exact_item_evidence": "exact_item",
            "official_source_evidence": "anchored_component",
            "component_model": "llm_only",
            "calibrated_component_model": "anchored_component",
            "no_matching_evidence": "llm_only",
        }
        raw["estimate_mode"] = estimate_mode_map.get(resolution_basis, raw.get("estimate_mode"))
    if "estimate_confidence_tier" not in raw:
        if resolution_mode == "exact_label_finalize":
            raw["estimate_confidence_tier"] = "high"
        elif resolution_mode == "near_exact_finalize":
            raw["estimate_confidence_tier"] = "medium"
        else:
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
        }
        itemized_payloads.append(normalized_item)
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
        }
    if itemized_payloads:
        synthesized_answer_payload["items"] = itemized_payloads

    normalized = {
        **_default_normalized_answer(user_text),
        "decision": str(raw.get("decision") or "DIRECT_ANSWER"),
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
        "estimate_mode": str(raw.get("estimate_mode") or "llm_only"),
        "estimate_confidence_tier": str(raw.get("estimate_confidence_tier") or "low"),
        "why_not_exact": str(raw.get("why_not_exact") or "No deterministic evidence was applied."),
        "heuristic_dependencies": [str(item) for item in raw.get("heuristic_dependencies", []) if str(item).strip()],
        "action_taken": str(raw.get("action_taken") or ("clarify_before_estimate" if followup_question else "answer_with_uncertainty")),
        "tool_request": str(raw.get("tool_request") or "none"),
        "tool_request_reason": str(raw.get("tool_request_reason") or ""),
        "answer_payload": synthesized_answer_payload,
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
        "component_estimates": build_component_estimates(components),
    }
    if normalized["action_taken"] == "request_tool" and normalized["tool_request"] == "none":
        normalized["action_taken"] = "clarify_before_estimate"
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


def nutrition_result_from_primary(primary_result: dict[str, Any]) -> NutritionResolutionResult:
    action_taken = str(primary_result.get("action_taken") or "")
    unresolved = [str(item) for item in primary_result.get("unresolved_info", []) if str(item).strip()]
    resolution_mode_raw = str(primary_result.get("resolution_mode") or "")
    estimate_mode_raw = str(primary_result.get("estimate_mode") or "")
    exactness = str(primary_result.get("exactness") or "").strip()
    if not exactness:
        if resolution_mode_raw == "exact_label_finalize" or estimate_mode_raw == "exact_item":
            exactness = "exact_item"
        elif resolution_mode_raw == "near_exact_finalize":
            exactness = "near_exact"
        elif resolution_mode_raw in {"component_estimate", "provisional_estimate"}:
            exactness = "component_grounded"
        else:
            exactness = "unknown"
    resolution_mode = "cannot_estimate_yet"
    if exactness == "exact_item":
        resolution_mode = "exact_label_finalize"
    elif exactness == "near_exact":
        resolution_mode = "near_exact_finalize"
    elif action_taken == "answer_with_uncertainty":
        resolution_mode = "provisional_estimate"
    elif action_taken == "direct_answer":
        resolution_mode = "component_estimate"
    basis = "component_model"
    if exactness == "exact_item":
        basis = "exact_item_evidence"
    elif exactness == "near_exact":
        basis = "official_source_evidence"
    elif exactness == "calibrated_estimate":
        basis = "calibrated_component_model"
    return NutritionResolutionResult(
        resolution_mode=resolution_mode,  # type: ignore[arg-type]
        resolution_basis=basis,  # type: ignore[arg-type]
        confidence=_normalize_confidence(primary_result.get("confidence")),
        exactness=exactness,  # type: ignore[arg-type]
        answer_payload=dict(primary_result.get("answer_payload") or {}),
        unresolved_info=unresolved,
        state_transition_hint=primary_result.get("state_transition_hint"),
    )

