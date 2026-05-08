from __future__ import annotations

from typing import Any

from app.composition.intake_manager_tool_batch import validate_manager_target_proposal
from app.shared.contracts.correction_target import validate_correction_target_ref


def manager_result_target_proposals(manager_result: Any) -> list[tuple[str, dict[str, Any]]]:
    proposals: list[tuple[str, dict[str, Any]]] = []
    top_target = getattr(manager_result, "target_attachment", None)
    if isinstance(top_target, dict) and top_target:
        proposals.append(("manager_result.target_attachment", dict(top_target)))
    semantic_decision = getattr(manager_result, "semantic_decision", None)
    if isinstance(semantic_decision, dict):
        semantic_target = semantic_decision.get("target_attachment")
        if isinstance(semantic_target, dict) and semantic_target:
            proposals.append(("manager_result.semantic_decision.target_attachment", dict(semantic_target)))
    answer_contract = getattr(manager_result, "answer_contract", None)
    if isinstance(answer_contract, dict):
        answer_target = answer_contract.get("target_attachment")
        if isinstance(answer_target, dict) and answer_target:
            proposals.append(("manager_result.answer_contract.target_attachment", dict(answer_target)))
    return proposals


def validate_final_manager_target_attachment(
    *,
    correction_target: dict[str, Any],
    manager_result: Any,
) -> dict[str, Any]:
    if str(getattr(manager_result, "final_action", "") or "") != "correction_applied":
        return dict(correction_target)
    if validate_correction_target_ref(correction_target).get("resolved") is True:
        return dict(correction_target)
    last_validation = dict(correction_target)
    for source, proposal in manager_result_target_proposals(manager_result):
        resolved = validate_manager_target_proposal(
            correction_target=correction_target,
            proposal={**proposal, "target_proposal_source": source},
        )
        last_validation = resolved
        if validate_correction_target_ref(resolved).get("resolved") is True:
            return resolved
    return last_validation
