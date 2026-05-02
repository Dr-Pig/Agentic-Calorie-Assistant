from __future__ import annotations

from typing import Any

from app.shared.contracts.correction_target import validate_correction_target_ref

from app.composition.intake_estimation_tools import estimate_nutrition_tool
from app.composition.intake_read_tools import compare_against_budget_tool
from app.nutrition.application.evidence_eligibility import classify_query_family, summarize_eligibility_results
from app.nutrition.application.web_extract_port import WebExtractPort
from app.nutrition.application.web_search_port import WebSearchPort
from app.runtime.application.execution_guard import evaluate_macro_display


def payload_trace_contract(payload: Any) -> dict[str, Any]:
    return dict(getattr(payload, "trace_contract", None) or {})


def payload_unresolved_info(payload: Any) -> list[str]:
    raw = payload_trace_contract(payload).get("unresolved_info") or []
    return [str(item) for item in raw if str(item).strip()]


def macro_summary(payload: Any | None) -> dict[str, Any]:
    if payload is None:
        return {"display_status": "hide", "guard_reason": "macro_missing", "macro_kcal_delta": 0}
    result = evaluate_macro_display(
        estimated_kcal=int(getattr(payload, "estimated_kcal", 0) or 0),
        protein_g=int(getattr(payload, "protein_g", 0) or 0),
        carb_g=int(getattr(payload, "carb_g", 0) or 0),
        fat_g=int(getattr(payload, "fat_g", 0) or 0),
    )
    return {
        "protein_g": int(getattr(payload, "protein_g", 0) or 0),
        "carbs_g": int(getattr(payload, "carb_g", 0) or 0),
        "fat_g": int(getattr(payload, "fat_g", 0) or 0),
        "display_status": result.display_status,
        "guard_reason": result.guard_reason,
        "macro_kcal": result.macro_kcal,
        "macro_kcal_delta": result.macro_kcal_delta,
        "alignment_warning": result.alignment_warning,
    }


def evidence_summary(*, raw_user_input: str, payload: Any | None) -> dict[str, Any]:
    trace_contract = payload_trace_contract(payload) if payload is not None else {}
    component_breakdown = list(getattr(payload, "component_breakdown", None) or []) if payload is not None else []
    grounding_summary = dict(trace_contract.get("grounding_summary") or {})
    db_hit_type = str(trace_contract.get("db_hit_type") or "")
    exact_truth_detected = (
        bool(grounding_summary.get("exact_truth_present"))
        or db_hit_type == "exact_truth"
        or "exact_truth" in {str(item) for item in (grounding_summary.get("evidence_roles") or [])}
        or int(((trace_contract.get("reasoning_state") or {}).get("exact_lane_count") or 0)) > 0
    )
    if exact_truth_detected:
        eligibility = {
            "candidate_count": max(1, int(grounding_summary.get("retrieved_knowledge_count") or 1)),
            "exact_count": 1,
            "near_exact_count": 0,
            "generic_count": 0,
            "provisional_eligibility": "exact",
            "high_variance_family": bool(classify_query_family(raw_user_input)),
            "family_rule": classify_query_family(raw_user_input),
            "why_not_exact": [],
        }
    elif component_breakdown:
        eligibility = summarize_eligibility_results(component_breakdown, query=raw_user_input)
    else:
        raw_why_not_exact = trace_contract.get("why_not_exact") or []
        why_not_exact = [raw_why_not_exact] if isinstance(raw_why_not_exact, str) and raw_why_not_exact.strip() else []
        if not isinstance(raw_why_not_exact, str):
            why_not_exact = [str(item) for item in raw_why_not_exact if str(item).strip()]
        eligibility = {
            "candidate_count": 0,
            "exact_count": 0,
            "near_exact_count": 0,
            "generic_count": 0,
            "provisional_eligibility": "generic" if classify_query_family(raw_user_input) else "unusable",
            "high_variance_family": bool(classify_query_family(raw_user_input)),
            "family_rule": classify_query_family(raw_user_input),
            "why_not_exact": why_not_exact,
        }
    return {
        "eligibility": eligibility.get("provisional_eligibility", "unusable"),
        "candidate_count": int(eligibility.get("candidate_count") or 0),
        "exact_count": int(eligibility.get("exact_count") or 0),
        "near_exact_count": int(eligibility.get("near_exact_count") or 0),
        "generic_count": int(eligibility.get("generic_count") or 0),
        "high_variance_family": bool(eligibility.get("high_variance_family")),
        "family_rule": eligibility.get("family_rule"),
        "why_not_exact": list(eligibility.get("why_not_exact") or []),
        "intake_execution_guard_family": trace_contract.get("intake_execution_guard_family"),
        "search_attempt_count": int(trace_contract.get("search_attempt_count") or 0),
        "search_query": trace_contract.get("search_query"),
        "db_hit_type": db_hit_type or None,
    }


def contextualized_query_for_estimation(*, raw_user_input: str, state_before: Any) -> str | None:
    pending_followup = ((state_before.injected_context or {}).get("PENDING_FOLLOWUP") or {})
    if not bool(pending_followup.get("is_open")):
        return None
    target = ((state_before.injected_context or {}).get("TARGET_MEAL_REFERENCE") or {})
    meal_title = str(target.get("meal_title") or "").strip()
    pending_question = str(pending_followup.get("pending_question") or "").strip()
    answer = str(raw_user_input or "").strip()
    if not meal_title or not answer:
        return None
    if pending_question:
        return f"Follow-up for {meal_title}. Pending question: {pending_question} User answer: {answer}"
    return f"Follow-up for {meal_title}: {answer}"


def correction_target_resolved(correction_target: dict[str, Any]) -> bool:
    return validate_correction_target_ref(correction_target).get("resolved") is True


def attach_correction_target_ref_to_payload(*, payload: Any | None, correction_target: dict[str, Any]) -> None:
    if payload is None or not correction_target_resolved(correction_target):
        return
    trace_contract = payload_trace_contract(payload)
    trace_contract["correction_target_ref"] = {
        "meal_thread_id": correction_target.get("meal_thread_id"),
        "meal_item_id": correction_target.get("meal_item_id"),
        "canonical_name": correction_target.get("canonical_name"),
    }
    trace_contract["correction_target_ref_source"] = "phase_a_resolved_target_reference"
    payload.trace_contract = trace_contract


def nutrition_tool_output(
    *,
    raw_user_input: str,
    nutrition_artifact: Any | None,
    correction_target: dict[str, Any],
    budget_summary: dict[str, Any] | None,
    failure_family: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    payload = getattr(nutrition_artifact, "payload", None) if nutrition_artifact is not None else None
    evidence: dict[str, Any] = {"nutrition_payload": None}
    if payload is not None:
        evidence["nutrition_payload"] = {
            "meal_title": getattr(payload, "meal_title", ""),
            "estimated_kcal": int(getattr(payload, "estimated_kcal", 0) or 0),
            "route_target": getattr(payload, "route_target", ""),
            "action_taken": getattr(payload, "action_taken", ""),
            "followup_question": getattr(payload, "followup_question", ""),
            "reply_text": getattr(payload, "reply_text", ""),
            "unresolved_info": payload_unresolved_info(payload),
            "trace_contract": payload_trace_contract(payload),
        }
    return {
        "tool_name": "estimate_nutrition",
        "evidence": evidence,
        "mutation_result": {},
        "provenance": {
            "correction_target": correction_target,
            "budget_summary": budget_summary or {},
            "macro_summary": macro_summary(payload),
            "evidence_summary": evidence_summary(raw_user_input=raw_user_input, payload=payload),
        },
        "confidence": "available" if payload is not None else "none",
        "failure_family": failure_family,
        "error_message": error_message,
    }


def apply_final_action_to_payload(
    *,
    payload: Any | None,
    raw_user_input: str,
    final_action: str,
    manager_answer_contract: dict[str, Any] | None = None,
    manager_semantic_decision: dict[str, Any] | None = None,
) -> None:
    if payload is None:
        return
    trace_contract = payload_trace_contract(payload)
    trace_contract["manager_final_action"] = str(final_action or "")
    trace_contract["manager_final_action_role"] = "trace_only_no_semantic_rewrite"
    existing_followup = str(getattr(payload, "followup_question", None) or "").strip()
    answer_contract = dict(manager_answer_contract or {})
    semantic_decision = dict(manager_semantic_decision or {})
    manager_followup = str(
        answer_contract.get("followup_question")
        or semantic_decision.get("followup_question")
        or ""
    ).strip()
    if manager_followup and not existing_followup:
        payload.followup_question = manager_followup
        payload.follow_up_needed = True
        trace_contract["manager_followup_projection"] = {
            "source": (
                "manager_answer_contract"
                if answer_contract.get("followup_question")
                else "manager_semantic_decision"
            ),
            "role": "manager_owned_renderer_projection",
            "deterministic_role": "projection_only_no_followup_creation",
        }
    payload.trace_contract = trace_contract


async def execute_manager_tool_calls(
    *,
    db: Any,
    user_external_id: str,
    raw_user_input: str,
    request_id: str,
    local_date: str,
    allow_search: bool,
    manager_provider: Any | None,
    provider: Any | None,
    search_port: WebSearchPort | None,
    extract_port: WebExtractPort | None,
    state_before: Any,
    correction_target: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    tool_state: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for call in tool_calls:
        name = str(call.get("name") or call.get("tool_name") or "").strip()
        if name == "resolve_correction_target":
            tool_state["correction_target"] = correction_target
            results.append(
                {
                    "tool_name": name,
                    "evidence": {},
                    "mutation_result": {},
                    "provenance": {"correction_target": correction_target},
                    "confidence": "available" if correction_target else "none",
                    "failure_family": None,
                }
            )
            continue
        if name == "compare_against_budget":
            artifact = tool_state.get("nutrition_artifact")
            payload = getattr(artifact, "payload", None) if artifact is not None else None
            if payload is None:
                results.append({"tool_name": name, "evidence": {}, "mutation_result": {}, "provenance": {}, "confidence": "none", "failure_family": "missing_nutrition_payload"})
                continue
            budget_summary = compare_against_budget_tool(
                current_budget_view=state_before.current_budget_view,
                estimated_kcal=int(getattr(payload, "estimated_kcal", 0) or 0),
                replaced_kcal=0,
            )
            tool_state["budget_summary"] = budget_summary
            results.append({"tool_name": name, "evidence": {"budget_summary": budget_summary}, "mutation_result": {}, "provenance": {}, "confidence": "available", "failure_family": None})
            continue
        if name == "estimate_nutrition":
            try:
                artifact = await estimate_nutrition_tool(
                    db,
                    user_external_id=user_external_id,
                    raw_user_input=raw_user_input,
                    request_id=request_id,
                    local_date=local_date,
                    manager_provider=manager_provider,
                    provider=provider,
                    search_port=search_port,
                    extract_port=extract_port,
                    allow_search=allow_search,
                    force_new_meal_context=(
                        not bool(((state_before.injected_context or {}).get("PENDING_FOLLOWUP") or {}).get("is_open"))
                        and not correction_target_resolved(correction_target)
                    ),
                    contextualized_query=contextualized_query_for_estimation(raw_user_input=raw_user_input, state_before=state_before),
                )
                payload = getattr(artifact, "payload", None)
                budget_summary = None
                if payload is not None:
                    attach_correction_target_ref_to_payload(
                        payload=payload,
                        correction_target=correction_target,
                    )
                    budget_summary = compare_against_budget_tool(
                        current_budget_view=state_before.current_budget_view,
                        estimated_kcal=int(getattr(payload, "estimated_kcal", 0) or 0),
                        replaced_kcal=0,
                    )
                tool_state["nutrition_artifact"] = artifact
                tool_state["budget_summary"] = budget_summary
                results.append(nutrition_tool_output(raw_user_input=raw_user_input, nutrition_artifact=artifact, correction_target=correction_target, budget_summary=budget_summary))
            except Exception as exc:
                results.append(nutrition_tool_output(raw_user_input=raw_user_input, nutrition_artifact=None, correction_target=correction_target, budget_summary=None, failure_family="tool_execution_error", error_message=str(exc)))
            continue
        results.append({"tool_name": name or "unknown", "evidence": {}, "mutation_result": {}, "provenance": {}, "confidence": "none", "failure_family": "unknown_tool"})
    return results
