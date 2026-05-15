from __future__ import annotations

from typing import Any

from app.composition.intake_estimation_tools import (
    estimate_nutrition_tool,
    manager_semantic_decision_from_tool_arguments,
)
from app.composition.intake_tool_context import (
    contextualized_query_for_estimation,
    correction_target_resolved,
)
from app.composition.intake_read_tools import compare_against_budget_tool
from app.composition.intake_manager_thread_target_validation import validate_manager_thread_target_proposal
from app.composition.intake_tool_evidence_summary import (
    evidence_summary,
    macro_summary,
    payload_trace_contract,
    payload_unresolved_info,
)
from app.intake.application.target_evidence_artifacts import payload_is_target_evidence
from app.nutrition.application.web_extract_port import WebExtractPort
from app.nutrition.application.web_search_port import WebSearchPort
from app.shared.contracts.correction_operation import (
    structured_correction_operation,
    structured_payload_requests_thread_level_correction,
)

def validate_manager_target_proposal(
    *,
    correction_target: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    """Validate Manager-proposed correction target against deterministic state candidates."""
    if not proposal:
        return dict(correction_target)
    candidates = [dict(item) for item in (correction_target.get("item_candidates") or []) if isinstance(item, dict)]
    proposed_id = proposal.get("meal_item_id")
    proposed_name = str(proposal.get("canonical_name") or proposal.get("item_name") or "").strip()
    operation = structured_correction_operation(proposal)
    if structured_payload_requests_thread_level_correction(proposal):
        return validate_manager_thread_target_proposal(correction_target=correction_target, proposal=proposal)
    matched: dict[str, Any] | None = None
    for candidate in candidates:
        id_matches = proposed_id is not None and candidate.get("meal_item_id") == proposed_id
        name_matches = proposed_name and str(candidate.get("canonical_name") or "").casefold() == proposed_name.casefold()
        if id_matches or name_matches:
            if matched is not None:
                return {
                    **dict(correction_target),
                    "manager_target_proposal_validation": {
                        "status": "rejected",
                        "failure_family": "manager_target_proposal_ambiguous",
                        "truth_owner": "deterministic_target_validator",
                    },
                }
            matched = candidate
    if matched is None:
        return {
            **dict(correction_target),
            "manager_target_proposal_validation": {
                "status": "rejected",
                "failure_family": "manager_target_proposal_not_found",
                "truth_owner": "deterministic_target_validator",
            },
        }
    return {
        **dict(correction_target),
        "meal_thread_id": matched.get("meal_thread_id") or correction_target.get("meal_thread_id"),
        "meal_version_id": matched.get("meal_version_id") or correction_target.get("meal_version_id"),
        "meal_item_id": matched.get("meal_item_id"),
        "canonical_name": matched.get("canonical_name"),
        "observed_canonical_name": matched.get("canonical_name"),
        **({"correction_operation": operation, "operation": operation} if operation else {}),
        "target_resolution_source": "manager_target_proposal_validated",
        "correction_confidence": "high",
        "manager_target_proposal_validation": {
            "status": "accepted",
            "truth_owner": "deterministic_target_validator",
            "proposal_source": str(proposal.get("target_proposal_source") or "manager_structured_output"),
        },
    }

def attach_correction_target_ref_to_payload(
    *,
    payload: Any | None,
    correction_target: dict[str, Any],
    source: str = "phase_a_resolved_target_reference",
) -> None:
    if payload is None or not correction_target_resolved(correction_target):
        return
    trace_contract = payload_trace_contract(payload)
    trace_contract["correction_target_ref"] = {
        "meal_thread_id": correction_target.get("meal_thread_id"),
        "meal_version_id": correction_target.get("meal_version_id"),
        "meal_item_id": correction_target.get("meal_item_id"),
        "canonical_name": correction_target.get("canonical_name"),
        "operation": correction_target.get("operation") or correction_target.get("correction_operation"),
    }
    trace_contract["correction_target_ref_source"] = source
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
        trace_contract = payload_trace_contract(payload)
        if payload_is_target_evidence(payload):
            target_contract = dict(trace_contract.get("target_evidence_contract") or {})
            evidence["target_evidence_payload"] = {
                "evidence_type": "target_evidence",
                "operation": trace_contract.get("correction_operation"),
                "nutrition_evidence_present": False,
                "target_evidence_is_nutrition_evidence": False,
                "canonical_remaining_item_totals": dict(trace_contract.get("canonical_remaining_item_totals") or {}),
            }
            if target_contract.get("source") is not None:
                evidence["target_evidence_payload"]["source"] = target_contract.get("source")
        else:
            evidence["nutrition_payload"] = {
                "meal_title": getattr(payload, "meal_title", ""),
                "estimated_kcal": int(getattr(payload, "estimated_kcal", 0) or 0),
                "route_target": getattr(payload, "route_target", ""),
                "action_taken": getattr(payload, "action_taken", ""),
                "followup_question": getattr(payload, "followup_question", ""),
                "reply_text": getattr(payload, "reply_text", ""),
                "unresolved_info": payload_unresolved_info(payload),
                "trace_contract": trace_contract,
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
    target_attachment = dict(semantic_decision.get("target_attachment") or {})
    correction_operation = str(answer_contract.get("correction_operation") or answer_contract.get("operation") or target_attachment.get("correction_operation") or target_attachment.get("operation") or "").strip()
    if correction_operation:
        trace_contract["correction_operation"] = correction_operation
        trace_contract["correction_operation_source"] = "manager_structured_decision"
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
        arguments = dict(call.get("arguments") or {}) if isinstance(call.get("arguments"), dict) else {}
        if name == "resolve_correction_target":
            proposed_target = dict(arguments)
            resolved_target = validate_manager_target_proposal(
                correction_target=correction_target,
                proposal=proposed_target,
            )
            tool_state["correction_target"] = resolved_target
            results.append(
                {
                    "tool_name": name,
                    "evidence": {},
                    "mutation_result": {},
                    "provenance": {"correction_target": resolved_target},
                    "confidence": "available" if resolved_target else "none",
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
                active_correction_target = dict(tool_state.get("correction_target") or correction_target)
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
                    manager_semantic_decision=manager_semantic_decision_from_tool_arguments(arguments),
                    force_new_meal_context=(
                        not bool(((state_before.injected_context or {}).get("PENDING_FOLLOWUP") or {}).get("is_open"))
                        and not correction_target_resolved(active_correction_target)
                    ),
                    contextualized_query=contextualized_query_for_estimation(raw_user_input=raw_user_input, state_before=state_before),
                )
                payload = getattr(artifact, "payload", None)
                budget_summary = None
                if payload is not None:
                    attach_correction_target_ref_to_payload(
                        payload=payload,
                        correction_target=active_correction_target,
                    )
                    budget_summary = compare_against_budget_tool(
                        current_budget_view=state_before.current_budget_view,
                        estimated_kcal=int(getattr(payload, "estimated_kcal", 0) or 0),
                        replaced_kcal=0,
                    )
                tool_state["nutrition_artifact"] = artifact
                tool_state["budget_summary"] = budget_summary
                results.append(nutrition_tool_output(raw_user_input=raw_user_input, nutrition_artifact=artifact, correction_target=active_correction_target, budget_summary=budget_summary))
            except Exception as exc:
                results.append(nutrition_tool_output(raw_user_input=raw_user_input, nutrition_artifact=None, correction_target=dict(tool_state.get("correction_target") or correction_target), budget_summary=None, failure_family="tool_execution_error", error_message=str(exc)))
            continue
        results.append({"tool_name": name or "unknown", "evidence": {}, "mutation_result": {}, "provenance": {}, "confidence": "none", "failure_family": "unknown_tool"})
    return results
