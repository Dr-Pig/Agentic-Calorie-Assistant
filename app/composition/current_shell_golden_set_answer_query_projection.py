from __future__ import annotations

from typing import Any


def attach_answer_query_no_mutation_outcome(
    *,
    runtime: dict[str, Any],
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
    state_delta: dict[str, Any],
) -> None:
    semantic_decision = _dict(manager_final.get("semantic_decision")) or _dict(
        manager_decision.get("semantic_decision")
    )
    current_turn_intent = str(semantic_decision.get("current_turn_intent") or "")
    workflow_effect = str(
        semantic_decision.get("workflow_effect")
        or manager_final.get("workflow_effect")
        or manager_decision.get("workflow_effect")
        or ""
    )
    mutation_intent = str(semantic_decision.get("mutation_intent_candidate") or "")
    final_action = str(manager_final.get("final_action") or manager_decision.get("final_action") or "")
    if (
        current_turn_intent == "answer_query"
        and workflow_effect == "answer_only"
        and mutation_intent == "no_mutation"
        and final_action == "answer_only"
    ):
        runtime.setdefault("inquiry_may_be_treated_as_correction", False)
    answer_contract = _dict(manager_final.get("answer_contract")) or _dict(
        manager_decision.get("answer_contract")
    )
    basis_source = str(semantic_decision.get("source") or "")
    if (
        basis_source == "active_meal_estimate_basis"
        or str(semantic_decision.get("estimation_posture") or "") == "basis_explained"
        or str(answer_contract.get("answer_basis") or "").strip()
    ):
        runtime.setdefault("estimate_basis_required", True)
    if state_delta_has_no_meal_change(state_delta):
        runtime.setdefault("mutation_allowed", False)


def state_delta_has_no_meal_change(state_delta: dict[str, Any]) -> bool:
    if not state_delta:
        return False
    return all(
        state_delta.get(field) is False
        for field in (
            "canonical_commit",
            "meal_logged",
            "draft_saved",
            "new_meal_version_created",
            "old_version_superseded",
            "ledger_updated",
        )
        if field in state_delta
    )


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


__all__ = ["attach_answer_query_no_mutation_outcome", "state_delta_has_no_meal_change"]
