from __future__ import annotations

from typing import Any


def manager_result_payload(manager_result: Any) -> dict[str, Any]:
    return {
        "final_action": str(getattr(manager_result, "final_action", "") or ""),
        "target_attachment": dict(getattr(manager_result, "target_attachment", {}) or {}),
        "answer_contract": dict(getattr(manager_result, "answer_contract", {}) or {}),
        "semantic_decision": dict(getattr(manager_result, "semantic_decision", {}) or {}),
    }
