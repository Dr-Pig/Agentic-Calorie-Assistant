from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..agent.decision_llm import DECISION_PROMPT, fallback_decision_result, normalize_decision_result
from ..agent.exact_item_packets import build_exact_item_lane_packet
from ..agent.local_knowledge_selector import resolve_ingredient_anchors
from ..application.evidence_assembly import (
    build_partial_grounding_packet,
    build_tool_candidate_requests,
    build_tool_result,
    execute_primary_tool_request,
    infer_expected_components,
    merge_evidence_items,
    normalize_tool_evidence,
    retrieval_query_is_usable,
    summarize_selected_evidence,
    tool_availability,
)
from ..application.context_assembly import build_decision_payload
from ..application.pass_runner import run_pass


def canonical_safety_floor_kcal(
    *,
    body_plan: Any | None = None,
    explicit_safety_floor_kcal: int | None = None,
) -> int | None:
    """Return the canonical safety floor if one is already known.

    The canonical source is the active BodyPlan safety floor, or an explicit override
    passed by the rescue/correction caller. This helper intentionally does not infer
    a fallback from sex/gender or other profile heuristics.
    """

    if explicit_safety_floor_kcal is not None:
        try:
            return max(0, int(explicit_safety_floor_kcal))
        except (TypeError, ValueError):
            return None
    if body_plan is None:
        return None
    if isinstance(body_plan, dict):
        value = body_plan.get("safety_floor_kcal")
    else:
        value = getattr(body_plan, "safety_floor_kcal", None)
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


@dataclass
class InitialGroundingState:
    retrieval_query: str
    retrieval_triggered: bool
    available_tools: list[str]
    candidate_tool_calls: list[dict[str, Any]]
    executed_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    doc_read_fragments: list[dict[str, Any]] = field(default_factory=list)
    retrieved_knowledge: list[dict[str, Any]] = field(default_factory=list)
    filtered_knowledge: list[dict[str, Any]] = field(default_factory=list)
    normalized_evidence: list[dict[str, Any]] = field(default_factory=list)
    partial_grounding: dict[str, Any] = field(default_factory=dict)
    local_exact_truth_present: bool = False


@dataclass
class DecisionStageOutcome:
    decision_result: Any
    selected_evidence_for_primary: list[dict[str, Any]]
    normalized_evidence: list[dict[str, Any]]
    partial_grounding: dict[str, Any]
    sources: list[dict[str, Any]]
    used_search: bool
    search_query: str | None
    search_quality: Any


def _decision_repair_note(*, decision_result: Any, decision_payload: dict[str, Any]) -> str | None:
    if decision_result.next_action != "run_clarify" or not bool(decision_result.clarify_is_blocking):
        return None
    if bool(decision_payload.get("exact_truth_available")):
        return (
            "Exact evidence is already present. Do not make clarification blocking unless the missing detail is the only thing "
            "that changes which exact item the user means and no useful estimate can be given."
        )
    if bool(decision_payload.get("standardized_drink_like")) and not bool(decision_payload.get("cup_size_provided")):
        return (
            "For a recognizable drink item, missing size does not automatically require blocking clarification when a useful "
            "estimate-with-followup is still possible. Re-evaluate whether nutrition resolution should proceed."
        )
    if int(decision_payload.get("exact_brand_conflict_count") or 0) > 0:
        return (
            "Conflicting brand hints are present among exact candidates. Prefer nutrition resolution or official search rather than a blocking brand question unless the brand conflict is truly the only way to avoid a misleading answer."
        )
    return None


def _planner_brand_context(planner_result: Any) -> str | None:
    input_signals = getattr(planner_result, "input_signals", None) or {}
    brands = input_signals.get("brands") if isinstance(input_signals, dict) else []
    for brand in brands or []:
        value = str(brand).strip()
        if value:
            return value
    return None


def resolve_local_exact_item_lane(
    *,
    retrieval_query: str,
    planner_result: Any,
    limit: int = 4,
) -> dict[str, Any]:
    return build_exact_item_lane_packet(
        retrieval_query,
        active_brand_context=_planner_brand_context(planner_result),
        limit=limit,
    )


def prepare_initial_grounding(
    *,
    effective_user_input: str,
    planner_result: Any,
    request: Any,
    search_adapter: Any | None,
    max_selected_evidence_items: int,
) -> InitialGroundingState:
    retrieval_query = (
        planner_result.resolved_query.strip()
        or (planner_result.input_signals.get("foods", [effective_user_input])[0] if planner_result.input_signals.get("foods") else effective_user_input)
    )
    available_tools = tool_availability(request, search_adapter=search_adapter)
    candidate_tool_calls = build_tool_candidate_requests(query=retrieval_query, decision_tool_plan="none")
    state = InitialGroundingState(
        retrieval_query=retrieval_query,
        retrieval_triggered=False,
        available_tools=available_tools,
        candidate_tool_calls=candidate_tool_calls,
    )

    if planner_result.planning_brief.evidence_strategy == "clarify_before_grounding":
        return state
    if not retrieval_query_is_usable(retrieval_query):
        return state

    state.retrieval_triggered = True
    exact_lane_packet = resolve_local_exact_item_lane(
        retrieval_query=retrieval_query,
        planner_result=planner_result,
        limit=4,
    )
    exact_candidates = list(exact_lane_packet["exact_candidates"])
    fallback_component_list = infer_expected_components(
        user_input=effective_user_input,
        planner_foods=[str(item) for item in planner_result.input_signals.get("foods", []) if str(item).strip()],
    )
    anchor_component_list = list(
        dict.fromkeys((planner_result.input_signals.get("foods") or []) or fallback_component_list or [effective_user_input])
    )
    anchor_candidates = resolve_ingredient_anchors(
        anchor_component_list,
        portion_hints=planner_result.input_signals.get("portion_clues", []),
        limit=max(6, len(anchor_component_list)),
    )
    state.retrieved_knowledge = merge_evidence_items(exact_candidates, anchor_candidates)
    state.filtered_knowledge = list(state.retrieved_knowledge[:max_selected_evidence_items])
    state.local_exact_truth_present = bool(exact_lane_packet["local_exact_truth_present"])
    state.normalized_evidence = normalize_tool_evidence(
        state.filtered_knowledge,
        source_type="local_retrieval",
        query=retrieval_query,
        limit=max_selected_evidence_items,
    )
    state.partial_grounding = build_partial_grounding_packet(
        user_input=effective_user_input,
        planner_foods=[str(item) for item in planner_result.input_signals.get("foods", []) if str(item).strip()],
        selected_evidence=state.filtered_knowledge,
    )
    state.executed_tool_calls.extend(
        [
            build_tool_result(
                tool_name="resolve_exact_item",
                status="executed",
                reason="Local exact-item resolver executed for bounded candidate retrieval.",
                result_count=len(exact_candidates),
                quality="high"
                if any(item.get("identity_confidence") == "high" for item in exact_candidates)
                else ("medium" if exact_candidates else "low"),
            ),
            build_tool_result(
                tool_name="resolve_ingredient_anchors",
                status="executed",
                reason="Ingredient anchor resolver executed for bounded candidate retrieval.",
                result_count=len(anchor_candidates),
                quality="medium" if anchor_candidates else "low",
            ),
        ]
    )
    return state


async def run_decision_tool_lookup(
    *,
    decision_result: Any,
    local_exact_truth_present: bool,
    planner_result: Any,
    request: Any,
    search_adapter: Any | None,
    executed_tool_calls: list[dict[str, Any]],
    selected_evidence_for_primary: list[dict[str, Any]],
    normalized_evidence: list[dict[str, Any]],
    effective_user_input: str,
    exact_brand_conflict_count: int = 0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], bool, str | None, Any, str, int]:
    sources: list[dict[str, Any]] = []
    used_search = False
    search_query, search_quality = None, None
    decision_tool_query = (
        str(getattr(decision_result, "tool_query_override", "") or "").strip()
        or str(planner_result.resolved_query or "").strip()
        or str(effective_user_input or "").strip()
    )
    if decision_result.tool_plan in {"resolve_exact_item", "resolve_ingredient_anchors"}:
        executed_tool_calls.append(
            build_tool_result(
                tool_name=decision_result.tool_plan,
                status="not_needed",
                reason="Bounded local grounding already executed this local retrieval tool before decision routing.",
                result_count=0,
                quality="medium" if selected_evidence_for_primary else "low",
            )
        )
        return (
            selected_evidence_for_primary,
            normalized_evidence,
            sources,
            build_partial_grounding_packet(
                user_input=effective_user_input,
                planner_foods=[str(item) for item in planner_result.input_signals.get("foods", []) if str(item).strip()],
                selected_evidence=selected_evidence_for_primary,
            ),
            used_search,
            search_query,
            search_quality,
            decision_tool_query,
            0,
        )
    if not (
        decision_result.next_action == "run_tool_lookup"
        and decision_result.tool_plan != "none"
        and not (
            local_exact_truth_present
            and exact_brand_conflict_count <= 0
            and decision_result.tool_plan in {"search_official_nutrition", "read_official_doc_fragment"}
        )
    ):
        return (
            selected_evidence_for_primary,
            normalized_evidence,
            sources,
            build_partial_grounding_packet(
                user_input=effective_user_input,
                planner_foods=[str(item) for item in planner_result.input_signals.get("foods", []) if str(item).strip()],
                selected_evidence=selected_evidence_for_primary,
            ),
            used_search,
            search_query,
            search_quality,
            decision_tool_query,
            0,
        )

    tool_evidence, search_sources, search_query, search_quality = await execute_primary_tool_request(
        tool_request=decision_result.tool_plan,
        tool_reason="Decision pass requested tool lookup before nutrition resolution.",
        retrieval_query=decision_tool_query,
        resolved_query=decision_tool_query,
        planner_result=planner_result,
        request=request,
        search_adapter=search_adapter,
        executed_tool_calls=executed_tool_calls,
        build_tool_result=build_tool_result,
    )
    if search_sources:
        used_search = True
        sources = merge_evidence_items(sources, search_sources)
    if tool_evidence:
        selected_evidence_for_primary = merge_evidence_items(selected_evidence_for_primary, tool_evidence)
        normalized_evidence = [
            *normalized_evidence,
            *normalize_tool_evidence(
                tool_evidence,
                source_type=decision_result.tool_plan,
                query=search_query or decision_tool_query,
            ),
        ]
    partial_grounding = build_partial_grounding_packet(
        user_input=effective_user_input,
        planner_foods=[str(item) for item in planner_result.input_signals.get("foods", []) if str(item).strip()],
        selected_evidence=selected_evidence_for_primary,
    )
    partial_grounding["search_attempt_count"] = 1 if used_search else 0
    return (
        selected_evidence_for_primary,
        normalized_evidence,
        sources,
        partial_grounding,
        used_search,
        search_query,
        search_quality,
        decision_tool_query,
        len(tool_evidence),
    )


def build_selected_evidence_summary(selected_evidence_for_primary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return summarize_selected_evidence(selected_evidence_for_primary)


async def run_decision_stage(
    *,
    primary_llm: Any,
    request_id: str,
    effective_user_input: str,
    canonical_meal_state: Any,
    task_meal_link_result: Any,
    planner_result: Any,
    filtered_knowledge: list[dict[str, Any]],
    available_tools: list[str],
    local_exact_truth_present: bool,
    request: Any,
    search_adapter: Any | None,
    executed_tool_calls: list[dict[str, Any]],
    normalized_evidence: list[dict[str, Any]],
    partial_grounding: dict[str, Any],
    run_stage: Any,
    llm_traces: list[dict[str, Any]],
    debug_steps: list[dict[str, Any]],
    planner_max_tokens: int,
) -> DecisionStageOutcome:
    fallback_decision = fallback_decision_result(meal_link_result=task_meal_link_result)
    decision_payload = build_decision_payload(
        user_input=effective_user_input,
        meal_state=canonical_meal_state,
        meal_link_result=task_meal_link_result,
        selected_evidence_summary=build_selected_evidence_summary(filtered_knowledge),
        available_tools=available_tools,
        planning_brief=planner_result.planning_brief,
    )
    decision_result, decision_envelope = await run_pass(
        provider=primary_llm,
        stage="decision_pass",
        system_prompt=DECISION_PROMPT,
        user_payload=decision_payload,
        max_tokens=planner_max_tokens,
        fallback_result=fallback_decision,
        normalize=lambda raw, fallback: normalize_decision_result(raw, fallback=fallback),
        dump=lambda result: result.model_dump(mode="json"),
        run_stage=run_stage,
        request_id=request_id,
        llm_traces=llm_traces,
        trigger_reason="decision_pass",
        handoff_contract={
            "meal_link_action": task_meal_link_result.meal_link_action,
            "target_meal_id": task_meal_link_result.target_meal_id,
            "selected_evidence_count": len(filtered_knowledge),
        },
        required_fields=["next_action", "tool_plan", "clarify_is_blocking", "can_proceed_without_clarify"],
        required_fields_source="normalized",
        nullable_required_fields=["clarify_priority"],
    )
    if decision_envelope.status != "success":
        debug_steps.append({"request_id": request_id, "step": "decision_pass", "error": decision_envelope.error})

    repair_note = _decision_repair_note(decision_result=decision_result, decision_payload=decision_payload)
    if repair_note:
        decision_result, decision_envelope = await run_pass(
            provider=primary_llm,
            stage="decision_pass_repair",
            system_prompt=DECISION_PROMPT + "\n\n[REPAIR_NOTE]\n" + repair_note,
            user_payload=decision_payload,
            max_tokens=planner_max_tokens,
            fallback_result=decision_result,
            normalize=lambda raw, fallback: normalize_decision_result(raw, fallback=fallback),
            dump=lambda result: result.model_dump(mode="json"),
            run_stage=run_stage,
            request_id=request_id,
            llm_traces=llm_traces,
            trigger_reason="decision_pass_repair",
            handoff_contract={
                "meal_link_action": task_meal_link_result.meal_link_action,
                "target_meal_id": task_meal_link_result.target_meal_id,
                "selected_evidence_count": len(filtered_knowledge),
                "repair_note": repair_note,
            },
            required_fields=["next_action", "tool_plan", "clarify_is_blocking", "can_proceed_without_clarify"],
            required_fields_source="normalized",
            nullable_required_fields=["clarify_priority"],
        )
        if decision_envelope.status != "success":
            debug_steps.append({"request_id": request_id, "step": "decision_pass_repair", "error": decision_envelope.error})

    selected_evidence_for_primary = list(filtered_knowledge)
    sources: list[dict[str, Any]] = []
    used_search = False
    search_query, search_quality = None, None
    reasoning_state = dict(decision_payload.get("reasoning_state") or {})

    should_escalate_search = (
        bool(search_adapter)
        and request.allow_search
        and bool(reasoning_state.get("brand_detected"))
        and int(reasoning_state.get("exact_lane_count") or 0) == 0
        and int(reasoning_state.get("search_attempt_count") or 0) == 0
        and decision_result.next_action != "run_tool_lookup"
    )
    if should_escalate_search:
        decision_result = decision_result.model_copy(
            update={
                "next_action": "run_tool_lookup",
                "tool_plan": "search_official_nutrition",
                "tool_goal": "find_exact_verified_brand_item",
                "missing_evidence_type": "official_exact",
                "expected_success_condition": "exact lane has same-item official or exact DB candidate",
            }
        )

    if (
        decision_result.next_action == "run_tool_lookup"
        and decision_result.tool_plan != "none"
        and not (
            local_exact_truth_present
            and decision_result.tool_plan in {"search_official_nutrition", "read_official_doc_fragment"}
        )
    ):
        (
            selected_evidence_for_primary,
            normalized_evidence,
            search_sources,
            partial_grounding,
            used_search,
            search_query,
            search_quality,
            decision_tool_query,
            decision_tool_hit_count,
        ) = await run_decision_tool_lookup(
            decision_result=decision_result,
            local_exact_truth_present=local_exact_truth_present,
            planner_result=planner_result,
            request=request,
            search_adapter=search_adapter,
            executed_tool_calls=executed_tool_calls,
            selected_evidence_for_primary=selected_evidence_for_primary,
            normalized_evidence=normalized_evidence,
            effective_user_input=effective_user_input,
            exact_brand_conflict_count=int(decision_payload.get("exact_brand_conflict_count") or 0),
        )
        if search_sources:
            sources = merge_evidence_items(sources, search_sources)
        debug_steps.append(
            {
                "request_id": request_id,
                "step": "decision_tool_lookup",
                "tool_plan": decision_result.tool_plan,
                "tool_goal": getattr(decision_result, "tool_goal", ""),
                "missing_evidence_type": getattr(decision_result, "missing_evidence_type", ""),
                "query": decision_tool_query,
                "tool_hit_count": decision_tool_hit_count,
                "search_hit_count": len(search_sources),
            }
        )

    return DecisionStageOutcome(
        decision_result=decision_result,
        selected_evidence_for_primary=selected_evidence_for_primary,
        normalized_evidence=normalized_evidence,
        partial_grounding=partial_grounding,
        sources=sources,
        used_search=used_search,
        search_query=search_query,
        search_quality=search_quality,
    )
