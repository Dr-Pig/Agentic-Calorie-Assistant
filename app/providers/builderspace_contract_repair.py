from __future__ import annotations

from typing import Any


def contract_repair_message(parse_attempt: dict[str, Any]) -> str:
    scoped_hint = _scoped_repair_hint(parse_attempt)
    return (
        "CONTRACT_REPAIR: Return the same manager decision using the required structured schema. "
        "Do not change user intent, target_attachment, exactness, confidence, or evidence_posture. "
        "Fix only the contract fields named by the validation error; if final_action and workflow_effect "
        "are inconsistent, update both consistently. "
        f"{scoped_hint}"
        f"Previous validation error: {parse_attempt.get('error')}"
    )


def _scoped_repair_hint(parse_attempt: dict[str, Any]) -> str:
    observed = parse_attempt.get("observed_value")
    if not isinstance(observed, dict):
        return ""
    semantic_decision = observed.get("semantic_decision")
    semantic_intent = (
        str(semantic_decision.get("current_turn_intent") or "")
        if isinstance(semantic_decision, dict)
        else ""
    )
    error = str(parse_attempt.get("error") or "")
    if "listed_item_lookup requires semantic_decision.listed_items" in error:
        return (
            "If you chose retrieval_goal='listed_item_lookup', include the concrete food components you, "
            "the Manager, identified in semantic_decision.listed_items. Do not ask the user for component "
            "names that were already explicitly supplied; rough portions can remain optional refinement. "
        )
    if str(observed.get("intent_type") or "") != "body_observation" and semantic_intent != "body_observation":
        return ""
    if "final_action invalid" not in error and "call_tools cannot use" not in error:
        return ""
    return (
        "For body_observation, commit is intake-only and is not a valid body action. "
        "If calling body.record_observation, use manager_action='call_tools' and "
        "final_action='record_observation'. If confirming an already successful body.record_observation "
        "tool result, use manager_action='final', final_action='answer_only', and "
        "workflow_effect='record_weight'. "
    )
