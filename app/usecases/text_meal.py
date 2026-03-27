from __future__ import annotations

from typing import Any

from ..logging import append_audit_event, now_iso
from ..schemas import (
    AnswerMode,
    AuditEvent,
    ComponentEstimate,
    EstimatePayload,
    EstimateRequest,
    PhaseOneDecision,
    PhaseTwoEstimate,
    SourceDecision,
)


COMPONENT_RESOLUTION_PROMPT = """You are a Traditional Chinese meal assistant.
Reply with compact JSON only.

Phase 1 task:
1. Understand what food this input refers to.
2. Write the main components of the meal.
3. Add simple quantity hints when they can be inferred from the meal name.
4. If components are not clear enough yet, decide whether the missing composition is more likely available from web search or only from the user.

Use this source_decision:
- ready: the main components are already usable
- search: web evidence is likely to clarify the composition
- ask_user: the user is the better source for the missing composition

Required keys:
- components
- source_decision

Optional keys:
- meal_title
- quantity_hints
- component_estimates
- followup_question
- search_query

When source_decision is ask_user, include one natural followup_question that matches the user's context.
When source_decision is search, include one short search_query.
"""


COMPONENT_RESOLUTION_WITH_EVIDENCE_PROMPT = """You are a Traditional Chinese meal assistant.
Reply with compact JSON only.

Phase 1 task with external evidence:
1. Use the evidence to understand what meal this is.
2. Write the main components.
3. Add simple quantity hints when the evidence supports them.
4. Decide whether the composition is now ready, or whether you still need the user.

Use this source_decision:
- ready
- ask_user

Required keys:
- components
- source_decision

Optional keys:
- meal_title
- quantity_hints
- component_estimates
- followup_question

When source_decision is ask_user, include one natural followup_question that matches the user's context.
"""


MACRO_ESTIMATION_PROMPT = """You are a Traditional Chinese meal assistant.
Reply with compact JSON only.

Phase 2 task:
1. Use the known components and quantity hints to estimate macros.
2. Return protein_g, carb_g, fat_g, and estimated_kcal.
3. Choose answer_mode:
- direct_answer
- answer_with_uncertainty

Required keys:
- protein_g
- carb_g
- fat_g
- estimated_kcal
- answer_mode

Optional keys:
- component_estimates
- uncertain_macro_areas
"""


COMPONENT_MACRO_PRIORS: dict[str, dict[str, Any]] = {
    "蛋餅皮": {"estimated_kcal": 140, "protein_g": 4, "carb_g": 22, "fat_g": 4, "quantity_hint": "1 份"},
    "餅皮": {"estimated_kcal": 140, "protein_g": 4, "carb_g": 22, "fat_g": 4, "quantity_hint": "1 份"},
    "雞蛋": {"estimated_kcal": 70, "protein_g": 6, "carb_g": 1, "fat_g": 5, "quantity_hint": "1 顆"},
    "蛋": {"estimated_kcal": 70, "protein_g": 6, "carb_g": 1, "fat_g": 5, "quantity_hint": "1 顆"},
    "起司": {"estimated_kcal": 60, "protein_g": 4, "carb_g": 1, "fat_g": 5, "quantity_hint": "1 片"},
    "蔥花": {"estimated_kcal": 5, "protein_g": 0, "carb_g": 1, "fat_g": 0, "quantity_hint": "少量"},
    "油": {"estimated_kcal": 45, "protein_g": 0, "carb_g": 0, "fat_g": 5, "quantity_hint": "約 1 茶匙"},
    "吐司": {"estimated_kcal": 80, "protein_g": 3, "carb_g": 15, "fat_g": 1, "quantity_hint": "1 片"},
    "培根": {"estimated_kcal": 45, "protein_g": 3, "carb_g": 0, "fat_g": 4, "quantity_hint": "1 片"},
    "豆漿": {"estimated_kcal": 130, "protein_g": 9, "carb_g": 10, "fat_g": 6, "quantity_hint": "1 杯"},
    "紅茶": {"estimated_kcal": 80, "protein_g": 0, "carb_g": 20, "fat_g": 0, "quantity_hint": "1 杯"},
    "白飯": {"estimated_kcal": 230, "protein_g": 4, "carb_g": 50, "fat_g": 0, "quantity_hint": "1 碗"},
    "排骨": {"estimated_kcal": 260, "protein_g": 20, "carb_g": 8, "fat_g": 16, "quantity_hint": "1 份"},
    "早餐店蘿蔔糕": {"estimated_kcal": 220, "protein_g": 4, "carb_g": 38, "fat_g": 6, "quantity_hint": "早餐店常見 1 份"},
    "蘿蔔糕": {"estimated_kcal": 220, "protein_g": 4, "carb_g": 38, "fat_g": 6, "quantity_hint": "1 份"},
}


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
    result: list[str] = []
    for item in _coerce_list(value):
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def _normalize_component_estimates(value: Any) -> list[ComponentEstimate]:
    estimates: list[ComponentEstimate] = []
    for item in _coerce_list(value):
        if isinstance(item, dict):
            estimates.append(
                ComponentEstimate(
                    name=str(item.get("name") or item.get("component") or "未命名成分"),
                    source="implicit" if item.get("source") == "implicit" else "explicit",
                    quantity_hint=item.get("quantity_hint") or item.get("quantity"),
                    estimated_kcal=int(round(float(item.get("estimated_kcal") or item.get("kcal") or 0))),
                    protein_g=int(round(float(item.get("protein_g") or 0))),
                    carb_g=int(round(float(item.get("carb_g") or 0))),
                    fat_g=int(round(float(item.get("fat_g") or 0))),
                )
            )
        else:
            estimates.append(ComponentEstimate(name=str(item)))
    return estimates


def _exception_text(exc: Exception) -> str:
    text = str(exc).strip()
    return text or exc.__class__.__name__


def _call_provider_request_payload(
    system_prompt: str,
    user_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "system_prompt": system_prompt,
        "user_payload": user_payload,
    }


async def _call_provider(
    provider: Any,
    *,
    stage: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    max_tokens: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if hasattr(provider, "complete_with_trace"):
        try:
            return await provider.complete_with_trace(
                system_prompt=system_prompt,
                user_payload=user_payload,
                stage=stage,
                max_tokens=max_tokens,
            )
        except TypeError:
            return await provider.complete_with_trace(
                system_prompt=system_prompt,
                user_payload=user_payload,
                stage=stage,
            )
    parsed = await provider.complete_structured(
        system_prompt=system_prompt,
        user_payload=user_payload,
        max_tokens=max_tokens,
    )
    return parsed, {
        "stage": stage,
        "provider": "unknown",
        "model": None,
        "request_payload": _call_provider_request_payload(system_prompt, user_payload),
        "raw_content": None,
        "parsed_object": parsed,
    }


def _normalize_source_decision(raw: Any, allow_search: bool) -> SourceDecision:
    decision = str(raw or "").strip().lower()
    mapping = {
        "ready": "ready",
        "components_ready": "ready",
        "ask_user": "ask_user",
        "clarify_for_components": "ask_user",
        "clarify": "ask_user",
        "search": "search",
        "search_for_components": "search",
    }
    normalized = mapping.get(decision, "ask_user")
    if normalized == "search" and not allow_search:
        return "ask_user"
    return normalized  # type: ignore[return-value]


def _normalize_phase_one(raw: dict[str, Any], text: str, allow_search: bool) -> PhaseOneDecision:
    normalized = dict(raw)
    return PhaseOneDecision.model_validate(
        {
            "meal_title": normalized.get("meal_title") or normalized.get("meal_name") or text.strip() or "這餐",
            "components": _string_list(normalized.get("components")),
            "quantity_hints": _string_list(normalized.get("quantity_hints") or normalized.get("known_quantities")),
            "component_estimates": _normalize_component_estimates(normalized.get("component_estimates")),
            "source_decision": _normalize_source_decision(
                normalized.get("source_decision") or normalized.get("component_decision") or normalized.get("decision"),
                allow_search,
            ),
            "followup_question": (str(normalized.get("followup_question")).strip() or None)
            if normalized.get("followup_question") is not None
            else None,
            "search_query": (str(normalized.get("search_query")).strip() or None)
            if normalized.get("search_query") is not None
            else None,
        }
    )


def _normalize_phase_two(raw: dict[str, Any]) -> PhaseTwoEstimate:
    normalized = dict(raw)
    answer_mode = str(normalized.get("answer_mode") or "direct_answer").strip()
    if answer_mode not in {"direct_answer", "answer_with_uncertainty"}:
        answer_mode = "direct_answer"
    return PhaseTwoEstimate.model_validate(
        {
            "component_estimates": _normalize_component_estimates(normalized.get("component_estimates")),
            "protein_g": int(round(float(normalized.get("protein_g") or 0))),
            "carb_g": int(round(float(normalized.get("carb_g") or 0))),
            "fat_g": int(round(float(normalized.get("fat_g") or 0))),
            "estimated_kcal": int(round(float(normalized.get("estimated_kcal") or 0))),
            "uncertain_macro_areas": _string_list(normalized.get("uncertain_macro_areas")),
            "answer_mode": answer_mode,
        }
    )


def _match_component_prior(component_name: str) -> dict[str, Any] | None:
    normalized = component_name.strip()
    if not normalized:
        return None
    for key, prior in COMPONENT_MACRO_PRIORS.items():
        if key in normalized or normalized in key:
            return prior
    return None


def _fallback_phase_two_from_components(
    components: list[str],
    quantity_hints: list[str],
) -> PhaseTwoEstimate | None:
    estimates: list[ComponentEstimate] = []
    unmatched: list[str] = []
    combined = quantity_hints + components
    for component in components:
        prior = _match_component_prior(component)
        if prior is None:
            for hint in combined:
                prior = _match_component_prior(hint)
                if prior is not None:
                    break
        if prior is None:
            unmatched.append(component)
            continue
        estimates.append(
            ComponentEstimate(
                name=component,
                source="explicit",
                quantity_hint=prior["quantity_hint"],
                estimated_kcal=prior["estimated_kcal"],
                protein_g=prior["protein_g"],
                carb_g=prior["carb_g"],
                fat_g=prior["fat_g"],
            )
        )

    if not estimates:
        return None

    return PhaseTwoEstimate(
        component_estimates=estimates,
        protein_g=sum(item.protein_g for item in estimates),
        carb_g=sum(item.carb_g for item in estimates),
        fat_g=sum(item.fat_g for item in estimates),
        estimated_kcal=sum(item.estimated_kcal for item in estimates),
        uncertain_macro_areas=(
            [f"我現在比較不確定的是 {'、'.join(unmatched[:2])} 的份量。"] if unmatched else []
        ),
        answer_mode="answer_with_uncertainty" if unmatched else "direct_answer",
    )


def _fallback_clarify(text: str, reason: str) -> EstimatePayload:
    message = "我現在還沒辦法確認這餐的主要內容。"
    if reason:
        message = f"{message} 目前卡在：{reason}"
    return EstimatePayload(
        meal_title=text.strip() or "這餐",
        source_decision="ask_user",
        action_taken="目前先停在組成判斷階段。",
        route_target="clarify_before_search",
        route_reason=reason or "目前還無法確認這餐的組成。",
        reply_text=message,
    )


def _reply_for_answer(payload: EstimatePayload) -> str:
    message = (
        f"我先把這餐估成約 {payload.estimated_kcal} kcal，"
        f"蛋白質 {payload.protein_g}g、碳水 {payload.carb_g}g、脂肪 {payload.fat_g}g。"
    )
    if payload.answer_mode == "answer_with_uncertainty" and payload.uncertain_macro_areas:
        uncertainty = "；".join(payload.uncertain_macro_areas[:2])
        message += f" 我現在比較不確定的是 {uncertainty}"
        if not message.endswith("。"):
            message += "。"
        message += " 如果你願意補充，我可以再幫你修正；不補充就先以這次估算為準。"
    return message


async def run_text_meal_canary(
    request: EstimateRequest,
    *,
    provider: Any,
    search: Any,
) -> EstimatePayload:
    debug_steps: list[dict[str, Any]] = []
    llm_traces: list[dict[str, Any]] = []
    try:
        phase_one_raw, phase_one_trace = await _call_provider(
            provider,
            stage="component_resolution",
            system_prompt=COMPONENT_RESOLUTION_PROMPT,
            user_payload={"text": request.text, "allow_search": request.allow_search},
            max_tokens=500,
        )
        llm_traces.append(phase_one_trace)
        phase_one = _normalize_phase_one(phase_one_raw, request.text, request.allow_search)
        debug_steps.append(
            {
                "step": "component_resolution",
                "source_decision": phase_one.source_decision,
                "component_count": len(phase_one.components),
            }
        )

        sources: list[dict[str, Any]] = []
        used_search = False
        search_query: str | None = None

        if phase_one.source_decision == "search":
            search_query = phase_one.search_query or request.text
            sources = await search.search(search_query)
            used_search = True
            debug_steps.append({"step": "search", "query": search_query, "result_count": len(sources)})
            phase_one_search_raw, phase_one_search_trace = await _call_provider(
                provider,
                stage="component_resolution_after_search",
                system_prompt=COMPONENT_RESOLUTION_WITH_EVIDENCE_PROMPT,
                user_payload={"text": request.text, "search_results": sources},
                max_tokens=500,
            )
            llm_traces.append(phase_one_search_trace)
            phase_one = _normalize_phase_one(phase_one_search_raw, request.text, request.allow_search)
            debug_steps.append(
                {
                    "step": "component_resolution_after_search",
                    "source_decision": phase_one.source_decision,
                    "component_count": len(phase_one.components),
                }
            )
            if phase_one.source_decision == "search":
                phase_one = phase_one.model_copy(update={"source_decision": "ask_user"})
                debug_steps.append(
                    {
                        "step": "search_resolution",
                        "result": "search_did_not_resolve_components",
                    }
                )

        if phase_one.source_decision != "ready":
            route_target = "clarify_after_search" if used_search else "clarify_before_search"
            if phase_one.followup_question is None:
                debug_steps.append(
                    {
                        "step": "incomplete_followup",
                        "reason": "ask_user_without_followup_question",
                    }
                )
            reply_text = phase_one.followup_question or "我現在還缺一個關鍵資訊，才能把這餐的組成判斷清楚。"
            return EstimatePayload(
                meal_title=phase_one.meal_title or request.text.strip() or "這餐",
                components=phase_one.components,
                quantity_hints=phase_one.quantity_hints,
                source_decision=phase_one.source_decision,
                action_taken="先補足組成，再進 macro 估算。",
                route_target=route_target,
                route_reason="目前還沒有足夠的組成資訊。",
                followup_question=phase_one.followup_question,
                used_search=used_search,
                search_query=search_query,
                sources=sources,
                debug_steps=debug_steps,
                llm_traces=llm_traces,
                reply_text=reply_text,
            )

        macro_fallback_used = False
        try:
            phase_two_raw, phase_two_trace = await _call_provider(
                provider,
                stage="macro_estimation",
                system_prompt=MACRO_ESTIMATION_PROMPT,
                user_payload={
                    "text": request.text,
                    "components": phase_one.components,
                    "quantity_hints": phase_one.quantity_hints,
                    "component_estimates": [item.model_dump(mode="json") for item in phase_one.component_estimates],
                },
                max_tokens=400,
            )
            llm_traces.append(phase_two_trace)
            phase_two = _normalize_phase_two(phase_two_raw)
            if phase_two.estimated_kcal <= 0:
                raise RuntimeError("macro_estimation returned no usable macros")
            debug_steps.append(
                {
                    "step": "macro_estimation",
                    "answer_mode": phase_two.answer_mode,
                }
            )
        except Exception as exc:
            fallback = _fallback_phase_two_from_components(phase_one.components, phase_one.quantity_hints)
            if fallback is None:
                raise
            phase_two = fallback
            macro_fallback_used = True
            debug_steps.append(
                {
                    "step": "macro_fallback",
                    "reason": _exception_text(exc),
                    "component_count": len(phase_one.components),
                }
            )

        route_target = (
            "answer_after_search"
            if used_search
            else "direct_estimate"
            if phase_two.answer_mode == "direct_answer"
            else "estimate_with_assumptions"
        )
        action_taken = (
            "模型沒有穩定回出 macro JSON，我先根據已判斷出的組成做保守 macro 估算。"
            if macro_fallback_used
            else "先根據組成與份量提示推估 macro，再換算熱量。"
        )
        route_reason = (
            "我已經有足夠的組成資訊，可以先估算。"
            if phase_two.answer_mode == "direct_answer"
            else "我已經能估算，但其中一部分份量仍可能讓數字上下浮動。"
        )
        payload = EstimatePayload(
            meal_title=phase_one.meal_title or request.text.strip() or "這餐",
            components=phase_one.components,
            quantity_hints=phase_one.quantity_hints,
            component_estimates=phase_two.component_estimates,
            protein_g=phase_two.protein_g,
            carb_g=phase_two.carb_g,
            fat_g=phase_two.fat_g,
            estimated_kcal=phase_two.estimated_kcal,
            uncertain_macro_areas=phase_two.uncertain_macro_areas,
            source_decision="ready",
            answer_mode=phase_two.answer_mode,
            action_taken=action_taken,
            route_target=route_target,
            route_reason=route_reason,
            used_search=used_search,
            search_query=search_query,
            sources=sources,
            debug_steps=debug_steps,
            llm_traces=llm_traces,
        )
        payload.reply_text = _reply_for_answer(payload)
        return payload
    except Exception as exc:
        payload = _fallback_clarify(request.text, _exception_text(exc))
        payload.debug_steps = debug_steps + [{"step": "fallback", "error": _exception_text(exc)}]
        payload.llm_traces = llm_traces
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
            llm_traces=payload.llm_traces,
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
