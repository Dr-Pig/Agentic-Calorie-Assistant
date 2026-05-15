from __future__ import annotations

from typing import Any


def validate_ask_followup_contract(
    *,
    payload: dict[str, Any],
    semantic_decision: dict[str, Any],
    final_action: str,
    final_action_candidate: str,
    workflow_effect: str,
) -> None:
    semantic_workflow_effect = str(semantic_decision.get("workflow_effect") or "")
    if str(payload.get("manager_action") or "") != "final":
        return
    if workflow_effect != "ask_followup" and final_action_candidate != "ask_followup":
        return
    if final_action != "ask_followup":
        raise RuntimeError("founder live manager contract ask_followup requires top-level final_action='ask_followup'")
    if workflow_effect != "ask_followup" or (semantic_workflow_effect and semantic_workflow_effect != "ask_followup"):
        raise RuntimeError("founder live manager contract ask_followup requires workflow_effect='ask_followup'")
    if not (_answer_followup_question(payload) or str(semantic_decision.get("followup_question") or "").strip()):
        raise RuntimeError("founder live manager contract ask_followup requires a concrete followup_question")


def _answer_followup_question(payload: dict[str, Any]) -> str:
    answer_contract = payload.get("answer_contract")
    if not isinstance(answer_contract, dict):
        return ""
    return str(answer_contract.get("followup_question") or "").strip()
