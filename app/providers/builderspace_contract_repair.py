from __future__ import annotations

from typing import Any


def contract_repair_message(parse_attempt: dict[str, Any]) -> str:
    return (
        "CONTRACT_REPAIR: Return the same manager decision using the required structured schema. "
        "Do not change user intent, target_attachment, exactness, confidence, or evidence_posture. "
        "Fix only the contract fields named by the validation error; if final_action and workflow_effect "
        "are inconsistent, update both consistently. "
        f"Previous validation error: {parse_attempt.get('error')}"
    )
