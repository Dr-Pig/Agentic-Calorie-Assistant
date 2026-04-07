from __future__ import annotations

import re
from typing import Any

from ..schemas import DecisionPassResult, TaskMealLinkResult


DECISION_PROMPT = """You are the decision pass for a food estimation assistant.

Your role: decide what the system should do next: clarify, continue to nutrition resolution, or look up more evidence.

## Core Decision Logic

0. Exact evidence already in hand comes first.
- If `exact_truth_available=true` and the payload already contains same-brand same-item exact candidates, do not request external search just because the input contains a brand.
- When local exact evidence already covers the user item well enough, choose `next_action=run_nutrition_resolution`.
- Treat hypothetical customizations as non-blocking unless the user explicitly mentioned them or they materially change which exact item this is.
- But if `size_missing_for_standardized_drink=true`, prefer `run_clarify` because cup size is still a blocking identity slot.
- If `exact_title_match_present=true`, treat the identity as already resolved. Do not invent combo-vs-single or set-vs-a-la-carte ambiguity unless the user text explicitly mentions it.
- Exception: for a generic drink class like bubble tea, milk tea, latte, or smoothie with no brand/package cues, do not let a packaged retail exact card pretend the identity is fully resolved. Treat those exact cards as weak references, not as the user's exact item.
- If `generic_drink_customization_present=true`, treat sugar or ice modifiers as enough structure for a useful provisional drink estimate even when cup size is still missing.

1. Brand or chain signal.
- A brand mention is a reason to search only when exact evidence is missing, weak, or identity is still unresolved.

2. Specificity.
- Ask whether the input is specific enough for a useful estimate.
- Generic category only: likely clarify.
- Recognizable dish or exact item: usually proceed.
- For standardized drinks, cup size can be identity-critical. If the user named a chain drink but omitted size and different sizes materially change calories, prefer blocking clarify instead of pretending one exact size.
- For a generic drink class with modifiers like `半糖`, `去冰`, or `無糖`, missing cup size is usually not blocking. Prefer `run_nutrition_resolution` so the nutrition pass can estimate with uncertainty.
- For a generic drink class like `珍珠奶茶` with no brand or size, a rough anchored estimate is still useful. Prefer `run_nutrition_resolution` and allow a follow-up for refinement instead of making clarification blocking by default.

3. Inherent variance.
- If the plausible calorie range is so wide that any answer would be misleading, clarify first.
- If a rough estimate would still be useful, proceed and let the nutrition pass carry uncertainty.

4. Tool choice.
- `search_official_nutrition`: use when branded exact evidence is still missing after local retrieval.
- `resolve_ingredient_anchors`: use when dish structure is clear but exact item evidence is unavailable.
- `get_meal_calibration`: supplementary only.

## Output Responsibilities

Return a structured decision with:
- `next_action`
- `tool_plan`
- `decision_confidence`
- `clarify_priority`
- `unresolved_info`
- `response_mode_hint`
- `clarify_is_blocking`
- `can_proceed_without_clarify`

## Rules
- Do not produce calories or macros here.
- If `exact_truth_available=true`, default to `run_nutrition_resolution` unless the exact candidates clearly contradict each other on identity.
- If the item is a standardized drink and size is missing, it is acceptable to choose `run_clarify` even when exact candidates exist, when size ambiguity would change the answer materially.
- But if `generic_drink_customization_present=true`, do not treat missing cup size as blocking by default unless the input is still too vague to estimate at all.
- But do not make clarification blocking for a generic drink class when a useful class-level estimate is still possible.
- Treat the payload flags `standardized_drink_like`, `portion_clues`, `drink_customization_clues`, `generic_drink_customization_present`, and `size_missing_for_standardized_drink` as direct evidence about whether cup size is still missing and whether a useful provisional estimate is still possible.
- Do not escalate to search when the only remaining uncertainty is optional syrup, milk, sugar, or similar customization not mentioned by the user.
- If input is a generic category with no specific type, prefer blocking clarify.
- If input is recognizable and a rough estimate is still useful, proceed.
"""


def fallback_decision_result(
    *,
    meal_link_result: TaskMealLinkResult,
) -> DecisionPassResult:
    return DecisionPassResult(
        next_action="run_clarify",
        tool_plan="none",
        decision_confidence="low",
        clarify_priority="meal_boundary" if meal_link_result.clarification_blocking else None,
        unresolved_info=["meal_boundary"] if meal_link_result.clarification_blocking else [],
        response_mode_hint="clarify_first" if meal_link_result.clarification_blocking else "rough_estimate_ok",
        clarify_is_blocking=bool(meal_link_result.clarification_blocking),
        can_proceed_without_clarify=not bool(meal_link_result.clarification_blocking),
    )


def normalize_decision_result(raw: dict[str, Any], *, fallback: DecisionPassResult) -> DecisionPassResult:
    if not raw:
        return fallback
    data = dict(raw)
    raw_text = str(data.get("_raw_text") or "").strip()
    if raw_text:
        data = {**data, **_parse_decision_text(raw_text)}
    next_action = str(data.get("next_action") or "").strip()
    direct_tool_actions = {
        "resolve_exact_item",
        "get_meal_calibration",
        "resolve_ingredient_anchors",
        "search_official_nutrition",
        "read_official_doc_fragment",
    }
    if next_action in direct_tool_actions:
        if not data.get("tool_plan"):
            data["tool_plan"] = next_action
        next_action = "run_tool_lookup"
    if not next_action:
        legacy_action = str(data.get("next_execution_action") or "").strip().lower()
        legacy_map = {
            "ask_clarification": "run_clarify",
            "clarify": "run_clarify",
            "tool_lookup": "run_tool_lookup",
            "run_tool_lookup": "run_tool_lookup",
            "nutrition_resolution": "run_nutrition_resolution",
            "estimate": "run_nutrition_resolution",
            "run_nutrition_resolution": "run_nutrition_resolution",
        }
        next_action = legacy_map.get(legacy_action, fallback.next_action)
    valid_tool_plans = {
        "none",
        "resolve_exact_item",
        "get_meal_calibration",
        "resolve_ingredient_anchors",
        "search_official_nutrition",
        "read_official_doc_fragment",
    }
    tool_plan = data.get("tool_plan")
    tool_query_override = None
    if isinstance(tool_plan, list):
        first_tool_entry = next(
            (item for item in tool_plan if isinstance(item, dict) and str(item.get("tool") or "").strip() in valid_tool_plans),
            None,
        )
        first_tool = next(
            (
                str(item.get("tool") or "").strip()
                for item in tool_plan
                if isinstance(item, dict) and str(item.get("tool") or "").strip() in valid_tool_plans
            ),
            "",
        )
        tool_plan_value = first_tool or fallback.tool_plan
        if isinstance(first_tool_entry, dict):
            params = first_tool_entry.get("params")
            if isinstance(params, dict):
                query_override = str(params.get("query") or "").strip()
                if query_override:
                    tool_query_override = query_override
    else:
        if tool_plan is None:
            tool_plan = fallback.tool_plan
        tool_plan_value = str(tool_plan or fallback.tool_plan).strip()
    if tool_plan_value not in valid_tool_plans:
        tool_plan_value = fallback.tool_plan
    clarify_is_blocking = bool(data.get("clarify_is_blocking", data.get("clarification_blocking", fallback.clarify_is_blocking)))
    can_proceed_without_clarify = bool(
        data.get(
            "can_proceed_without_clarify",
            data.get("provisional_estimate_possible", fallback.can_proceed_without_clarify),
        )
    )
    unresolved_info_raw = data.get("unresolved_info", fallback.unresolved_info)
    if isinstance(unresolved_info_raw, str):
        unresolved_info = [segment.strip() for segment in re.split(r"[;\n]+", unresolved_info_raw) if segment.strip()]
    else:
        unresolved_info = [str(item) for item in unresolved_info_raw if str(item).strip()]
    clarify_priority = data.get("clarify_priority")
    clarify_priority_value = str(clarify_priority).strip() if clarify_priority is not None else None
    if clarify_priority_value in {"", "none", "null"}:
        clarify_priority_value = None
    confidence_value = str(data.get("decision_confidence") or fallback.decision_confidence).strip().lower()
    if confidence_value not in {"high", "medium", "low"}:
        confidence_value = fallback.decision_confidence
    response_mode_hint = str(data.get("response_mode_hint") or "").strip().lower()
    if not response_mode_hint:
        if clarify_is_blocking and not can_proceed_without_clarify:
            response_mode_hint = "clarify_first"
        elif next_action == "run_nutrition_resolution":
            response_mode_hint = "rough_estimate_ok"
        else:
            response_mode_hint = fallback.response_mode_hint
    elif "clarify" in response_mode_hint:
        response_mode_hint = "clarify_first"
    elif "exact" in response_mode_hint:
        response_mode_hint = "exact_answer"
    elif response_mode_hint not in {"exact_answer", "rough_estimate_ok", "clarify_first"}:
        response_mode_hint = "rough_estimate_ok"
    return DecisionPassResult(
        next_action=str(next_action or fallback.next_action),  # type: ignore[arg-type]
        tool_plan=tool_plan_value,  # type: ignore[arg-type]
        decision_confidence=confidence_value,  # type: ignore[arg-type]
        tool_query_override=tool_query_override,
        clarify_priority=clarify_priority_value,
        unresolved_info=unresolved_info,
        response_mode_hint=str(response_mode_hint or fallback.response_mode_hint),  # type: ignore[arg-type]
        clarify_is_blocking=clarify_is_blocking,
        can_proceed_without_clarify=can_proceed_without_clarify,
    )


def _parse_decision_text(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    normalized = re.sub(r"\*\*", "", text.strip())
    next_action_match = re.search(r"next execution action:\s*([^\n]+)", normalized, flags=re.IGNORECASE)
    if next_action_match:
        action = next_action_match.group(1).strip().lower()
        action = re.split(r"\s*\(", action, maxsplit=1)[0].strip()
        if action in {"resolve_exact_item", "get_meal_calibration", "resolve_ingredient_anchors", "search_official_nutrition", "read_official_doc_fragment"}:
            parsed["next_action"] = "run_tool_lookup"
            parsed["tool_plan"] = action
        elif action in {"run_nutrition_resolution", "nutrition_resolution", "estimate"}:
            parsed["next_action"] = "run_nutrition_resolution"
        elif action in {"run_clarify", "clarify", "ask_clarification", "generic_clarification"}:
            parsed["next_action"] = "run_clarify"
    blocking_match = re.search(r"clarification blocking\??\s*:\s*([^\n]+)", normalized, flags=re.IGNORECASE)
    if blocking_match:
        value = blocking_match.group(1).strip().lower()
        parsed["clarify_is_blocking"] = value.startswith(("yes", "true", "blocking", "y"))
    proceed_match = re.search(r"proceed to provisional estimate\??\s*:\s*([^\n]+)", normalized, flags=re.IGNORECASE)
    if proceed_match:
        value = proceed_match.group(1).strip().lower()
        parsed["can_proceed_without_clarify"] = value.startswith(("yes", "true", "y"))
    return parsed
