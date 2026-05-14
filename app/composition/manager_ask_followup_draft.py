from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.composition.request_runtime_context import load_request_runtime_context
from app.nutrition.application.estimate_artifacts import EstimatedNutritionArtifact
from app.shared.contracts.common import EstimateRequest
from app.shared.contracts.intake import EstimatePayload


def build_manager_ask_followup_draft_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    request_id: str,
    manager_result: Any,
) -> EstimatedNutritionArtifact | None:
    if not _manager_ask_followup_support_ready(manager_result):
        return None
    followup_question = _manager_ask_followup_question(manager_result)
    answer_contract = dict(getattr(manager_result, "answer_contract", {}) or {})
    semantic_decision = dict(getattr(manager_result, "semantic_decision", {}) or {})
    request = EstimateRequest(text=raw_user_input, allow_search=False, user_id=user_external_id)
    runtime_context = load_request_runtime_context(
        request=request,
        db=db,
        provider=type("ManagerAskFollowupDraftProvider", (), {"readiness": lambda self: {"configured": False}})(),
    )
    payload = EstimatePayload(
        request_id=request_id,
        meal_title=_meal_title(semantic_decision, answer_contract, raw_user_input),
        estimated_kcal=0,
        source_decision="ask_user",
        answer_mode=None,
        action_taken="clarify_before_estimate",
        route_target="clarify_user_private",
        followup_question=followup_question,
        follow_up_needed=True,
        follow_up_reasoning="manager_final_ask_followup",
        reply_text=str(answer_contract.get("reply_text") or followup_question),
        trace_contract=_trace_contract(local_date, followup_question, semantic_decision),
        quality_signals={"estimate_mode": "ask_followup_only"},
    )
    return EstimatedNutritionArtifact(request=request, runtime_context=runtime_context, payload=payload)


def _manager_ask_followup_question(manager_result: Any) -> str:
    answer_contract = dict(getattr(manager_result, "answer_contract", {}) or {})
    semantic_decision = dict(getattr(manager_result, "semantic_decision", {}) or {})
    return str(answer_contract.get("followup_question") or semantic_decision.get("followup_question") or "").strip()


def _manager_ask_followup_support_ready(manager_result: Any) -> bool:
    if str(getattr(manager_result, "manager_action", "") or "") != "final":
        return False
    if str(getattr(manager_result, "final_action", "") or "") != "ask_followup":
        return False
    semantic_decision = dict(getattr(manager_result, "semantic_decision", {}) or {})
    if str(semantic_decision.get("final_action_candidate") or "ask_followup") != "ask_followup":
        return False
    if str(semantic_decision.get("workflow_effect") or "ask_followup") != "ask_followup":
        return False
    if str(semantic_decision.get("mutation_intent_candidate") or "no_mutation") not in {"", "no_mutation"}:
        return False
    return bool(_manager_ask_followup_question(manager_result))


def _meal_title(
    semantic_decision: dict[str, Any],
    answer_contract: dict[str, Any],
    raw_user_input: str,
) -> str:
    return str(
        semantic_decision.get("meal_title")
        or answer_contract.get("meal_title")
        or raw_user_input
        or "pending meal"
    ).strip() or "pending meal"


def _trace_contract(
    local_date: str,
    followup_question: str,
    semantic_decision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "local_date": local_date,
        "occurred_at": f"{local_date}T12:00:00+08:00",
        "timezone": "Asia/Taipei",
        "response_mode_hint": "clarify_first",
        "followup_question": followup_question,
        "missing_slots": ["composition_details"],
        "blocking_slots": ["composition_details"],
        "unresolved_info": ["composition_details"],
        "route_family": "component_driven_meal",
        "canonical_write_decision": {
            "can_write_canonical": False,
            "source": "manager_ask_followup_draft",
        },
        "manager_ask_followup_draft_contract": {
            "source": "manager_structured_final_action",
            "manager_final_action": "ask_followup",
            "nutrition_evidence_required": False,
            "deterministic_role": "persist_manager_owned_pending_followup_only",
            "raw_text_semantic_inference": False,
            "manager_semantic_decision": semantic_decision,
        },
    }
