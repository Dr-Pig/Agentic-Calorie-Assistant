from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.nutrition.application.b2_final_mapping import map_b2_final_item_result
from app.nutrition.application.b2_source_selection import select_b2_evidence_source
from app.nutrition.application.retrieval_intent import RetrievalGoal, RetrievalIntent


def attach_b2_owner_lineage_trace(
    *,
    payload: Any | None,
    manager_semantic_decision: dict[str, Any],
    manager_final_action: str,
) -> None:
    """Attach B2 owner-lineage observability without changing runtime decisions."""
    if payload is None:
        return

    trace_contract = dict(getattr(payload, "trace_contract", None) or {})
    retrieval_goal = _retrieval_goal_from_runtime_trace(
        trace_contract=trace_contract,
        manager_semantic_decision=manager_semantic_decision,
        manager_final_action=manager_final_action,
    )
    intent = RetrievalIntent(
        base_dish=None,
        aliases=[],
        brand_hint=None,
        size_hint=None,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal=retrieval_goal,
    )
    source_selection = asdict(select_b2_evidence_source(intent))
    packet_consumption_trace = _packet_consumption_trace(trace_contract)
    final_mapping = map_b2_final_item_result(
        _item_result_from_payload(payload, trace_contract=trace_contract, manager_semantic_decision=manager_semantic_decision),
        canonical_write_decision=trace_contract.get("canonical_write_decision"),
        interaction_type=_interaction_type(manager_semantic_decision=manager_semantic_decision, manager_final_action=manager_final_action),
    )

    trace_contract["retrieval_intent_source"] = "manager_semantic_decision"
    trace_contract["retrieval_intent_trace"] = {
        "source": "manager_semantic_decision",
        "retrieval_goal": retrieval_goal,
        "trace_role": "observability_only",
        "semantic_authority": manager_semantic_decision.get("semantic_authority"),
        "semantic_owner": manager_semantic_decision.get("semantic_owner"),
    }
    trace_contract["source_selection"] = source_selection
    trace_contract["packet_consumption_trace"] = packet_consumption_trace
    trace_contract["b2_final_mapping"] = final_mapping
    trace_contract["b2_owner_lineage_role"] = "trace_only_no_runtime_authority_change"
    payload.trace_contract = trace_contract


def _retrieval_goal_from_runtime_trace(
    *,
    trace_contract: dict[str, Any],
    manager_semantic_decision: dict[str, Any],
    manager_final_action: str,
) -> RetrievalGoal:
    workflow_effect = str(manager_semantic_decision.get("workflow_effect") or "").strip()
    estimation_posture = str(manager_semantic_decision.get("estimation_posture") or "").strip()
    final_action = str(manager_final_action or manager_semantic_decision.get("final_action_candidate") or "").strip()

    if final_action == "answer_only" or workflow_effect == "answer_only":
        return "query_only_answer"
    if final_action == "request_clarification" or workflow_effect == "ask_first_unresolved" or estimation_posture == "ask_first_unresolved":
        return "composition_clarification"
    if str(trace_contract.get("db_hit_type") or "").strip() == "exact_truth":
        return "exact_brand_lookup"
    return "generic_anchor_lookup"


def _packet_consumption_trace(trace_contract: dict[str, Any]) -> dict[str, Any]:
    web_trace = trace_contract.get("web_runtime_trace")
    if isinstance(web_trace, dict) and isinstance(web_trace.get("packet_consumption_trace"), dict):
        trace = dict(web_trace["packet_consumption_trace"])
    else:
        trace = {"accepted_packets": [], "rejected_candidates": []}
    trace["trace_role"] = "observability_only"
    trace["source"] = "active_runtime_payload_trace"
    return trace


def _item_result_from_payload(
    payload: Any,
    *,
    trace_contract: dict[str, Any],
    manager_semantic_decision: dict[str, Any],
) -> dict[str, Any]:
    estimated_kcal = int(getattr(payload, "estimated_kcal", 0) or 0)
    exactness_posture = "exact" if str(trace_contract.get("db_hit_type") or "") == "exact_truth" else "estimated"
    if estimated_kcal <= 0:
        exactness_posture = "unresolved"
    followup_question = str(manager_semantic_decision.get("followup_question") or getattr(payload, "followup_question", "") or "").strip()
    return {
        "food_name": str(getattr(payload, "meal_title", None) or "meal"),
        "likely_kcal": estimated_kcal if estimated_kcal > 0 else None,
        "kcal_range": _kcal_range(estimated_kcal, exactness_posture=exactness_posture),
        "exactness_posture": exactness_posture,
        "suggested_followup_question": followup_question or None,
    }


def _kcal_range(estimated_kcal: int, *, exactness_posture: str) -> list[int] | None:
    if estimated_kcal <= 0:
        return None
    if exactness_posture == "exact":
        return [estimated_kcal, estimated_kcal]
    return [max(0, round(estimated_kcal * 0.8)), round(estimated_kcal * 1.2)]


def _interaction_type(*, manager_semantic_decision: dict[str, Any], manager_final_action: str) -> str:
    workflow_effect = str(manager_semantic_decision.get("workflow_effect") or "").strip()
    if str(manager_final_action or "").strip() == "answer_only" or workflow_effect == "answer_only":
        return "nutrition_info_query"
    return "food_logging"


__all__ = ["attach_b2_owner_lineage_trace"]
