from __future__ import annotations

from typing import Any

from ..logging import append_audit_event, now_iso
from ..policies import HOME_COOKED_MARKERS, MEAL_CATEGORY_POLICY, is_home_cooked_signal
from ..schemas import AuditEvent, ComponentEstimate, EstimatePayload, EstimateRequest, InitialDecision, SearchDecision


INITIAL_PROMPT = """You are a Traditional Chinese nutrition estimation assistant for Taiwan meals.
Always reply with compact JSON only.

Goal:
1. Parse the meal into a rough component sketch.
2. Estimate component-level kcal, protein, carb, fat.
3. Produce an uncertainty profile.
4. Decide one of: estimate, clarify, search.

Rules:
- Always reason from components first.
- Include explicit components and high-probability implicit components.
- For home-cooked or private meals, external search is usually not useful.
- If information is partial but still enough to produce a useful estimate, choose estimate and surface assumptions.
- If a single high-impact modifier is missing, choose clarify and ask exactly one question.
- Search only when external evidence can plausibly improve identification.
- Use Traditional Chinese.
- Never output user-facing failure.
- parse_confidence and macro_confidence must be numbers from 0 to 1, not words.
- confidence_level must be one of: high, provisional, low.
- assumptions, components, known_quantities, implicit_components, missing_modifiers, component_estimates must all be arrays.
- In component_estimates, use key name, not component.

Required JSON keys:
meal_title, meal_category, components, known_quantities, implicit_components, missing_modifiers,
highest_impact_modifier, parse_confidence, macro_confidence, external_verifiability,
search_eligibility, can_estimate_with_defaults, confidence_level, decision, decision_reason,
assumptions, followup_question, component_estimates, estimated_kcal, protein_g, carb_g, fat_g, search_query
"""

SEARCH_PROMPT = """You are a Traditional Chinese nutrition assistant.
You already have external evidence. Decide whether the evidence is strong enough to answer, or whether you still need one clarification.
Always reply with compact JSON only.

Rules:
- Do not use weakly similar search results as if they were exact matches.
- If evidence is insufficient or low-similarity, choose clarify.
- Use Traditional Chinese.
- assumptions and component_estimates must be arrays.

Required JSON keys:
resolution, resolution_reason, search_acceptability, assumptions, followup_question,
component_estimates, estimated_kcal, protein_g, carb_g, fat_g
"""


def _home_cooked_adjustments(text: str, decision: dict[str, Any]) -> dict[str, Any]:
    if not is_home_cooked_signal(text):
        return decision
    decision["meal_category"] = "homemade_or_private_meal"
    decision["search_eligibility"] = False
    decision["external_verifiability"] = "low"
    if not decision.get("components"):
        decision["decision"] = "clarify"
        decision["decision_reason"] = "私人或家常來源無法靠外部資訊確認，先補主食與主要配料。"
        decision["followup_question"] = "你可以直接告訴我這份餐點有哪些主要內容嗎？例如主食、蛋白質、飲料或湯品。"
    return decision


def _coerce_float(value: Any, *, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    mapping = {"高": 0.85, "中": 0.6, "低": 0.3, "high": 0.85, "medium": 0.6, "low": 0.3}
    return mapping.get(str(value).strip().lower(), mapping.get(str(value).strip(), default))


def _coerce_confidence_level(value: Any, *, default: str = "low") -> str:
    text = str(value).strip().lower()
    mapping = {
        "高": "high",
        "中": "provisional",
        "低": "low",
        "high": "high",
        "medium": "provisional",
        "mid": "provisional",
        "provisional": "provisional",
        "low": "low",
    }
    return mapping.get(text, mapping.get(str(value).strip(), default))


def _coerce_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [f"{k}: {v}" for k, v in value.items()]
    text = str(value).strip()
    if not text:
        return []
    for delimiter in ["；", ";", "、", ",", "\n"]:
        if delimiter in text:
            return [item.strip() for item in text.split(delimiter) if item.strip()]
    return [text]


def _string_list(value: Any) -> list[str]:
    items = _coerce_list(value)
    result: list[str] = []
    for item in items:
        if isinstance(item, dict):
            result.extend(f"{k}: {v}" for k, v in item.items())
        else:
            text = str(item).strip()
            if text:
                result.append(text)
    return result


def _normalize_component_estimates(value: Any) -> list[dict[str, Any]]:
    items = _coerce_list(value)
    normalized: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            normalized.append(
                {
                    "name": item.get("name") or item.get("component") or "未命名成分",
                    "source": item.get("source") or ("implicit" if item.get("implicit") else "explicit"),
                    "quantity_hint": item.get("quantity_hint") or item.get("quantity"),
                    "estimated_kcal": int(item.get("estimated_kcal") or item.get("kcal") or 0),
                    "protein_g": int(item.get("protein_g") or 0),
                    "carb_g": int(item.get("carb_g") or 0),
                    "fat_g": int(item.get("fat_g") or 0),
                }
            )
        else:
            normalized.append(ComponentEstimate(name=str(item)).model_dump())
    return normalized


def _normalize_initial(decision: dict[str, Any], text: str, allow_search: bool) -> InitialDecision:
    adjusted = _home_cooked_adjustments(text, dict(decision))
    adjusted["meal_title"] = adjusted.get("meal_title") or adjusted.get("meal_name") or text.strip()
    adjusted["components"] = _string_list(adjusted.get("components"))
    adjusted["known_quantities"] = _string_list(adjusted.get("known_quantities"))
    adjusted["implicit_components"] = _string_list(adjusted.get("implicit_components"))
    adjusted["missing_modifiers"] = _string_list(adjusted.get("missing_modifiers"))
    adjusted["assumptions"] = _string_list(adjusted.get("assumptions"))
    adjusted["component_estimates"] = _normalize_component_estimates(adjusted.get("component_estimates"))
    adjusted["parse_confidence"] = _coerce_float(adjusted.get("parse_confidence"))
    adjusted["macro_confidence"] = _coerce_float(adjusted.get("macro_confidence"))
    adjusted["confidence_level"] = _coerce_confidence_level(adjusted.get("confidence_level"))
    ext = adjusted.get("external_verifiability")
    if isinstance(ext, bool):
        adjusted["external_verifiability"] = "high" if ext else "low"
    elif ext is None:
        adjusted["external_verifiability"] = "unknown"
    else:
        adjusted["external_verifiability"] = str(ext)
    if not allow_search:
        adjusted["search_eligibility"] = False
        if adjusted.get("decision") == "search":
            adjusted["decision"] = "clarify"
            adjusted["decision_reason"] = "目前未開啟搜尋，先補一個關鍵細節。"
    if adjusted.get("meal_category") not in MEAL_CATEGORY_POLICY:
        adjusted["meal_category"] = "unknown"
    adjusted.setdefault("decision", "clarify")
    adjusted.setdefault("decision_reason", "資訊不足，先補一個關鍵細節。")
    adjusted.setdefault("assumptions", [])
    adjusted.setdefault("component_estimates", [])
    return InitialDecision.model_validate(adjusted)


def _normalize_search_resolution(resolution: dict[str, Any]) -> SearchDecision:
    normalized = dict(resolution)
    normalized["assumptions"] = _string_list(normalized.get("assumptions"))
    normalized["component_estimates"] = _normalize_component_estimates(normalized.get("component_estimates"))
    normalized.setdefault("resolution", "clarify")
    normalized.setdefault("resolution_reason", "搜尋結果仍不足以直接回答。")
    normalized.setdefault("assumptions", [])
    normalized.setdefault("component_estimates", [])
    return SearchDecision.model_validate(normalized)


def _fallback_clarify(text: str, reason: str) -> EstimatePayload:
    return EstimatePayload(
        meal_title=text.strip() or "未命名餐點",
        meal_category="unknown",
        components=[],
        known_quantities=[],
        implicit_components=[],
        missing_modifiers=["main_components"],
        highest_impact_modifier="main_components",
        parse_confidence=0.0,
        macro_confidence=0.0,
        external_verifiability="unknown",
        search_eligibility=False,
        search_acceptability=None,
        confidence_level="low",
        estimated_kcal=0,
        protein_g=0,
        carb_g=0,
        fat_g=0,
        component_estimates=[],
        action_taken="目前先不硬猜，改為追問最關鍵資訊。",
        route_target="clarify_before_search",
        route_reason=reason,
        assumptions=[],
        followup_question="你可以直接告訴我這餐的主要內容嗎？例如主食、蛋白質、飲料或湯品。",
        used_search=False,
        search_query=None,
        sources=[],
        debug_steps=[],
        reply_text="我現在還不知道這餐的主要內容。你可以直接告訴我主食、蛋白質、飲料或湯品嗎？",
    )


def _reply_for_estimate(payload: EstimatePayload) -> str:
    macros = f"約 {payload.estimated_kcal} kcal，蛋白質 {payload.protein_g}g、碳水 {payload.carb_g}g、脂肪 {payload.fat_g}g。"
    assumption_text = "；".join(payload.assumptions[:2])
    if payload.route_target == "estimate_with_assumptions":
        tail = f"目前最不確定的是 {payload.highest_impact_modifier or '份量'}。如果你願意補充，我可以再幫你修正；不補充就先以這次估算為準。"
    else:
        tail = f"處置：{payload.action_taken}"
    if assumption_text:
        tail = f"{tail} 假設：{assumption_text}"
    return f"我先把這餐理解成「{payload.meal_title}」，{macros} {tail}"


async def run_text_meal_canary(
    request: EstimateRequest,
    *,
    provider: Any,
    search: Any,
) -> EstimatePayload:
    debug_steps: list[dict[str, Any]] = []
    try:
        initial_raw = await provider.complete_structured(
            system_prompt=INITIAL_PROMPT,
            user_payload={
                "text": request.text,
                "allow_search": request.allow_search,
                "policy": MEAL_CATEGORY_POLICY,
                "home_cooked_markers": HOME_COOKED_MARKERS,
            },
        )
        initial = _normalize_initial(initial_raw, request.text, request.allow_search)
        debug_steps.append(
            {
                "step": "component_sketch",
                "meal_category": initial.meal_category,
                "decision": initial.decision,
                "search_eligibility": initial.search_eligibility,
                "highest_impact_modifier": initial.highest_impact_modifier,
            }
        )
        if initial.decision == "clarify":
            return EstimatePayload(
                meal_title=initial.meal_title,
                meal_category=initial.meal_category,
                components=initial.components,
                known_quantities=initial.known_quantities,
                implicit_components=initial.implicit_components,
                missing_modifiers=initial.missing_modifiers,
                highest_impact_modifier=initial.highest_impact_modifier,
                parse_confidence=initial.parse_confidence,
                macro_confidence=initial.macro_confidence,
                external_verifiability=initial.external_verifiability,
                search_eligibility=initial.search_eligibility,
                search_acceptability=None,
                confidence_level=initial.confidence_level,
                estimated_kcal=initial.estimated_kcal,
                protein_g=initial.protein_g,
                carb_g=initial.carb_g,
                fat_g=initial.fat_g,
                component_estimates=initial.component_estimates,
                action_taken="先補一個最關鍵細節，再決定是否重算。",
                route_target="clarify_before_search",
                route_reason=initial.decision_reason,
                assumptions=initial.assumptions,
                followup_question=initial.followup_question or "你可以補充最影響熱量的那個細節嗎？",
                used_search=False,
                search_query=None,
                sources=[],
                debug_steps=debug_steps,
                reply_text=initial.followup_question or "你可以補充最影響熱量的那個細節嗎？",
            )

        if initial.decision == "search" and initial.search_eligibility and request.allow_search:
            query = initial.search_query or f"{request.text} 熱量 菜單"
            results = await search.search(query)
            debug_steps.append({"step": "search", "query": query, "result_count": len(results)})
            search_raw = await provider.complete_structured(
                system_prompt=SEARCH_PROMPT,
                user_payload={
                    "text": request.text,
                    "initial": initial.model_dump(mode="json"),
                    "search_results": results,
                },
            )
            resolved = _normalize_search_resolution(search_raw)
            debug_steps.append(
                {
                    "step": "search_resolution",
                    "resolution": resolved.resolution,
                    "search_acceptability": resolved.search_acceptability,
                }
            )
            route_target = "answer_after_search" if resolved.resolution == "answer" else "clarify_after_search"
            payload = EstimatePayload(
                meal_title=initial.meal_title,
                meal_category=initial.meal_category,
                components=initial.components,
                known_quantities=initial.known_quantities,
                implicit_components=initial.implicit_components,
                missing_modifiers=initial.missing_modifiers,
                highest_impact_modifier=initial.highest_impact_modifier,
                parse_confidence=initial.parse_confidence,
                macro_confidence=initial.macro_confidence,
                external_verifiability=initial.external_verifiability,
                search_eligibility=initial.search_eligibility,
                search_acceptability=resolved.search_acceptability,
                confidence_level=initial.confidence_level,
                estimated_kcal=resolved.estimated_kcal,
                protein_g=resolved.protein_g,
                carb_g=resolved.carb_g,
                fat_g=resolved.fat_g,
                component_estimates=resolved.component_estimates or initial.component_estimates,
                action_taken="先搜尋可用外部資訊，再根據 evidence 做估算或追問。",
                route_target=route_target,
                route_reason=resolved.resolution_reason,
                assumptions=(initial.assumptions + resolved.assumptions)[:4],
                followup_question=resolved.followup_question,
                used_search=True,
                search_query=query,
                sources=results,
                debug_steps=debug_steps,
                reply_text="",
            )
            payload.reply_text = (
                resolved.followup_question or "我已先查過外部資訊，但還差一個關鍵細節。你可以再補充嗎？"
                if route_target == "clarify_after_search"
                else _reply_for_estimate(payload)
            )
            return payload

        route_target = "direct_estimate" if initial.confidence_level == "high" else "estimate_with_assumptions"
        payload = EstimatePayload(
            meal_title=initial.meal_title,
            meal_category=initial.meal_category,
            components=initial.components,
            known_quantities=initial.known_quantities,
            implicit_components=initial.implicit_components,
            missing_modifiers=initial.missing_modifiers,
            highest_impact_modifier=initial.highest_impact_modifier,
            parse_confidence=initial.parse_confidence,
            macro_confidence=initial.macro_confidence,
            external_verifiability=initial.external_verifiability,
            search_eligibility=initial.search_eligibility,
            search_acceptability=None,
            confidence_level=initial.confidence_level,
            estimated_kcal=initial.estimated_kcal,
            protein_g=initial.protein_g,
            carb_g=initial.carb_g,
            fat_g=initial.fat_g,
            component_estimates=initial.component_estimates,
            action_taken="直接用組成與預設假設先估算。",
            route_target=route_target,
            route_reason=initial.decision_reason,
            assumptions=initial.assumptions,
            followup_question=None,
            used_search=False,
            search_query=None,
            sources=[],
            debug_steps=debug_steps,
            reply_text="",
        )
        payload.reply_text = _reply_for_estimate(payload)
        return payload
    except Exception as exc:
        payload = _fallback_clarify(request.text, str(exc))
        payload.debug_steps = debug_steps + [{"step": "fallback", "error": str(exc)}]
        return payload


def record_success(request: EstimateRequest, payload: EstimatePayload) -> None:
    append_audit_event(
        AuditEvent(
            timestamp=now_iso(),
            text=request.text,
            allow_search=request.allow_search,
            status="ok",
            route_target=payload.route_target,
            action_taken=payload.action_taken,
            debug_steps=payload.debug_steps,
            payload=payload.model_dump(mode="json"),
        )
    )


def record_error(request: EstimateRequest, error: str) -> None:
    append_audit_event(
        AuditEvent(
            timestamp=now_iso(),
            text=request.text,
            allow_search=request.allow_search,
            status="error",
            error=error,
        )
    )
