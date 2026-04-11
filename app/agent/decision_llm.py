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
- If `exact_truth_candidate_count>0`, do not make brand clarification blocking by default. Let the nutrition pass resolve candidate choice unless the missing brand is the only thing that distinguishes materially different items and no useful estimate can be given.
- Read `exact_brand_hints`, `exact_brand_conflict_count`, `core_default_candidate_count`, and `query_alignment` when exact candidates coexist.
- If there are multiple `core_default` exact candidates but they come from conflicting `brand_hint` values, do not immediately block on asking the user for brand. Prefer the candidate whose title or alias aligns best with the user text, and only escalate if the remaining conflict still changes the likely item materially.
- If the conflict is between a cross-brand title collision and an orthographic alias of a known chain item, you may still proceed to nutrition resolution without a blocking brand question.
- Treat `attested_evidence_blocks` as the canonical external evidence surface. Read `evidence_id`, `source_tier`, `source_class`, `origin_channel`, and `attestation` before deciding.
- When you refer to evidence in your hidden reasoning, cite `evidence_id` mentally and prefer higher `source_tier` over lower `source_tier`.
- Read `evidence_policy.source_priority` as:
  - exact verified evidence
  - verified context / confirmed memory
  - structured anchors and dish priors
  - weak or non-exact web evidence
  - model-only context
- Treat hypothetical customizations as non-blocking unless the user explicitly mentioned them or they materially change which exact item this is.
- But if `standardized_drink_like=true` and `cup_size_provided=false`, prefer `run_clarify` because cup size is still a blocking identity slot.
- Exception: if the user named a recognizable branded drink family and a useful anchored estimate is still possible, prefer `run_nutrition_resolution` over blocking clarify so the nutrition pass can return estimate-with-followup.
- If any entry in `exact_match_paths` is `exact_title` or `exact_alias`, treat the identity as already resolved. Do not invent combo-vs-single or set-vs-a-la-carte ambiguity unless the user text explicitly mentions it.
- Exception: for a generic drink class like bubble tea, milk tea, latte, or smoothie with no brand/package cues, do not let packaged exact candidates pretend the identity is fully resolved. Use `packaged_exact_candidate_count` only as evidence context, not as automatic identity resolution.
- If `drink_customization_clues` is non-empty for a generic drink class, treat sugar or ice modifiers as enough structure for a useful provisional drink estimate even when cup size is still missing.

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
- If the input contains a recognized restaurant or chain signal and `exact_truth_available=false`, your strong default should be `search_official_nutrition` before settling for a heuristic estimate.
- If `exact_brand_conflict_count>0` and the conflicting candidates imply different chains or brands, it is acceptable to prefer `search_official_nutrition` to disambiguate instead of forcing a blocking brand question.
- Only bypass search and go straight to heuristic nutrition if search was already attempted this turn, the brand is clearly irrelevant to the actual food identity, or a verified context signal already resolves the item strongly enough.
- `resolve_ingredient_anchors`: use when dish structure is clear but exact item evidence is unavailable.
- `get_meal_calibration`: supplementary only.
- If `attested_evidence_blocks` show only weak search evidence, low identity confidence, or missing official corroboration, it is valid to request more search with a tighter query.

## Output Responsibilities

Return a structured decision with:
- `next_action`
- `tool_plan`
- `tool_goal`
- `missing_evidence_type`
- `expected_success_condition`
- `decision_confidence`
- `clarify_priority`
- `unresolved_info`
- `response_mode_hint`
- `clarify_is_blocking`
- `can_proceed_without_clarify`

## Rules
- Do not produce calories or macros here.
- If `exact_truth_available=true`, default to `run_nutrition_resolution` unless the exact candidates clearly contradict each other on identity.
- Read `reasoning_state` / `evidence_gap_state` and treat them as the current ReAct observation of evidence sufficiency.
- If `reasoning_state.brand_detected=true`, `reasoning_state.exact_lane_count=0`, and `reasoning_state.search_attempt_count=0`, strongly prefer `next_action=run_tool_lookup` with `tool_plan=search_official_nutrition`.
- If `reasoning_state.template_lane_count>0`, `reasoning_state.anchor_lane_count=0`, and `reasoning_state.exact_lane_count=0`, do not pretend a direct estimate is ready. Prefer clarify or let nutrition handle a template-only ask-followup path.
- Multiple exact candidates is not the same as blocking ambiguity. If at least one exact candidate is still a plausible same-item interpretation, prefer `run_nutrition_resolution` and let the nutrition pass state uncertainty or ask a non-blocking follow-up.
- If the item is a standardized drink and `cup_size_provided=false`, it is acceptable to choose `run_clarify` even when exact candidates exist, when size ambiguity would change the answer materially.
- But for a branded drink with a recognizable core item and no explicit size, it is also acceptable to choose `run_nutrition_resolution` when a useful anchored estimate can still be given.
- But if `drink_customization_clues` is non-empty for a generic drink class, do not treat missing cup size as blocking by default unless the input is still too vague to estimate at all.
- But do not make clarification blocking for a generic drink class when a useful class-level estimate is still possible.
- If the system cannot produce any safe estimate at all, do not route toward a commit-capable estimate path. Prefer `run_clarify` with `clarify_is_blocking=true` and `response_mode_hint=clarify_first`.
- Treat the payload fields `standardized_drink_like`, `portion_clues`, `drink_customization_clues`, `cup_size_provided`, `exact_truth_candidate_count`, `exact_match_paths`, and `packaged_exact_candidate_count` as evidence facts, not deterministic decisions.
- Treat `evidence_policy.source_priority` as the trust order:
  exact verified > verified context > anchor/prior evidence > weak web > model knowledge.
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
    tool_goal = str(data.get("tool_goal") or "").strip()
    missing_evidence_type = str(data.get("missing_evidence_type") or "").strip()
    expected_success_condition = str(data.get("expected_success_condition") or "").strip()
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
    if clarify_is_blocking:
        can_proceed_without_clarify = False
        if response_mode_hint != "clarify_first":
            response_mode_hint = "clarify_first"
    elif next_action == "run_clarify" and not can_proceed_without_clarify:
        clarify_is_blocking = True
    return DecisionPassResult(
        next_action=str(next_action or fallback.next_action),  # type: ignore[arg-type]
        tool_plan=tool_plan_value,  # type: ignore[arg-type]
        decision_confidence=confidence_value,  # type: ignore[arg-type]
        tool_query_override=tool_query_override,
        tool_goal=tool_goal,
        missing_evidence_type=missing_evidence_type,
        expected_success_condition=expected_success_condition,
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
