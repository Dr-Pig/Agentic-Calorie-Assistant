from __future__ import annotations

from typing import Any


def structured_correction_operation(payload: dict[str, Any] | None) -> str:
    """Return a manager-owned correction operation from structured fields only."""

    if not isinstance(payload, dict):
        return ""
    candidates: list[Any] = [
        payload.get("correction_operation"),
        payload.get("operation"),
        payload.get("action_type"),
        payload.get("correction_type"),
    ]
    top_target = payload.get("target_attachment")
    if isinstance(top_target, dict):
        candidates.extend([
            top_target.get("correction_operation"),
            top_target.get("operation"),
            top_target.get("action_type"),
            top_target.get("correction_type"),
        ])
    answer_contract = payload.get("answer_contract")
    if isinstance(answer_contract, dict):
        candidates.extend([
            answer_contract.get("correction_operation"),
            answer_contract.get("operation"),
            answer_contract.get("action_type"),
            answer_contract.get("correction_type"),
        ])
    semantic_decision = payload.get("semantic_decision")
    if isinstance(semantic_decision, dict):
        candidates.extend([
            semantic_decision.get("correction_operation"),
            semantic_decision.get("operation"),
            semantic_decision.get("action_type"),
            semantic_decision.get("correction_type"),
        ])
        semantic_target = semantic_decision.get("target_attachment")
        if isinstance(semantic_target, dict):
            candidates.extend([
                semantic_target.get("correction_operation"),
                semantic_target.get("operation"),
                semantic_target.get("action_type"),
                semantic_target.get("correction_type"),
            ])
    for operation in payload.get("operations") or []:
        if isinstance(operation, dict):
            candidates.extend([operation.get("correction_operation"), operation.get("operation"), operation.get("action")])
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value:
            return value
    return ""


def structured_payload_requests_remove_item(payload: dict[str, Any] | None) -> bool:
    return structured_correction_operation(payload) == "remove_item"


__all__ = ["structured_correction_operation", "structured_payload_requests_remove_item"]
