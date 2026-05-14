from __future__ import annotations

from typing import Any

from app.composition.commit_boundary_preflight import run_commit_boundary_preflight
from app.shared.contracts.intake_results import EstimatePayload


def commit_boundary_guard_repair_outcome(
    *,
    payload: EstimatePayload | None,
    final_action: str,
    active_body_plan_present: bool,
    correction_target: Any,
    manager_semantic_decision: dict[str, Any],
    transition_preflight_trace: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if final_action not in {"commit", "correction_applied", "overshoot_note"} or payload is None:
        return None
    commit_preflight = run_commit_boundary_preflight(
        payload=payload,
        manager_final_action=final_action,
        active_body_plan_present=active_body_plan_present,
        correction_target=correction_target,
        manager_semantic_decision=manager_semantic_decision,
    )
    if not commit_preflight.blocked:
        return None
    return {
        "ok": False,
        "repair_request": True,
        "failure_family": commit_preflight.failure_family or "phase_a_commit_boundary_blocked",
        "guard_feedback_source": {
            "source": "commit_evidence_policy",
            "input_authority": "manager_owned_candidate_evidence",
            "input_kind": "nutrition_evidence_packet",
            "manager_semantic_authority": str(manager_semantic_decision.get("semantic_authority") or ""),
            "raw_user_input_used": False,
            "deterministic_food_classification_used": False,
        },
        "deterministic_final_action": False,
        "deterministic_followup_text": False,
        "phase_a_transition_guard_preflight": dict(transition_preflight_trace or {}),
        "phase_a_commit_boundary_preflight": commit_preflight.trace_payload(),
        "repair_instruction": {
            "role": "bounded_manager_repair",
            "deterministic_role": "reject_evidence_ineligible_commit_only",
            "manager_role": "choose legal final action",
            "allowed_repairs": [
                {
                    "manager_action": "final",
                    "final_action": "ask_followup",
                    "workflow_effect": "ask_followup",
                    "tool_calls": [],
                    "semantic_decision": {
                        "final_action_candidate": "ask_followup",
                        "mutation_intent_candidate": "no_mutation",
                        "estimation_posture": "composition_unknown_basket",
                    },
                }
            ],
        },
    }
