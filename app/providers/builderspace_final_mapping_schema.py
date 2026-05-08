from __future__ import annotations

from typing import Any

from ..runtime.agent.founder_live_manager_contract import FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS

_EVIDENCE_PRESENT_FINAL_ACTIONS = [
    action
    for action in FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS
    if action != "no_commit"
]

_EVIDENCE_PRESENT_WORKFLOW_EFFECTS = [
    "answer_only",
    "ask_followup",
    "canonical_write",
    "commit",
    "correction",
    "correction_applied",
    "correction_write",
    "manual_daily_target_update",
    "onboarding_required",
    "overshoot_note",
    "safe_failure",
    "target_updated",
]


def nutrition_evidence_present(constraints: dict[str, Any] | None) -> bool:
    evidence_state = constraints.get("manager_contract_evidence_state") if isinstance(constraints, dict) else None
    return isinstance(evidence_state, dict) and evidence_state.get("nutrition_evidence_present") is True


def apply_evidence_present_final_mapping_schema(
    base_schema: dict[str, Any],
    constraints: dict[str, Any] | None,
) -> None:
    if not nutrition_evidence_present(constraints):
        return
    properties = base_schema.get("properties")
    if not isinstance(properties, dict):
        return
    properties["final_action"] = {
        "type": "string",
        "enum": _EVIDENCE_PRESENT_FINAL_ACTIONS,
        "description": (
            "Evidence-present intake final mapping cannot use no_commit. Use commit, "
            "correction_applied, ask_followup, answer_only, or another explicit final action "
            "consistent with the Manager semantic decision."
        ),
    }
    properties["workflow_effect"] = {
        "type": "string",
        "enum": _EVIDENCE_PRESENT_WORKFLOW_EFFECTS,
        "description": (
            "Evidence-present intake final mapping must not remain in route_to_intake; "
            "use a concrete final workflow effect such as commit, correction_write, "
            "correction_applied, answer_only, or ask_followup."
        ),
    }
