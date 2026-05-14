from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.composition.phase_a_boundary_projection import build_intake_boundary_projection
from app.intake.application.commit_evidence_policy import (
    apply_commit_evidence_policy_to_payload,
    commit_evidence_blockers,
    commit_evidence_failure_family,
)
from app.intake.application.final_action_mutation_classifier import final_action_effect_class
from app.runtime.contracts.phase_a import PhaseABoundaryProjection
from app.shared.contracts.correction_target import validate_correction_target_ref
from app.shared.contracts.intake_results import EstimatePayload


@dataclass(frozen=True)
class CommitBoundaryPreflightResult:
    checked: bool
    bypassed: bool
    bypass_reason: str | None
    blocked: bool
    failure_family: str | None
    manager_final_action: str
    mutation_effect_class: str
    projected_commit_intent: str | None
    predicted_meal_status: str | None
    canonical_write_allowed: bool | None
    ledger_mutation_allowed: bool | None
    correction_target_resolved: bool | None
    correction_target_validation: dict[str, Any] | None = None
    projection: PhaseABoundaryProjection | None = None

    def trace_payload(self) -> dict[str, Any]:
        return {
            "checked": self.checked,
            "bypassed": self.bypassed,
            "bypass_reason": self.bypass_reason,
            "blocked": self.blocked,
            "failure_family": self.failure_family,
            "manager_final_action": self.manager_final_action,
            "mutation_effect_class": self.mutation_effect_class,
            "projected_commit_intent": self.projected_commit_intent,
            "predicted_meal_status": self.predicted_meal_status,
            "canonical_write_allowed": self.canonical_write_allowed,
            "ledger_mutation_allowed": self.ledger_mutation_allowed,
            "correction_target_resolved": self.correction_target_resolved,
            "correction_target_validation": self.correction_target_validation,
        }


def _correction_target_resolved(correction_target: Any | None) -> bool | None:
    resolved = validate_correction_target_ref(correction_target).get("resolved")
    return resolved if isinstance(resolved, bool) else None


def _effect_allowed(
    *,
    mutation_effect_class: str,
    intent: str,
    canonical_write_allowed: bool,
    ledger_mutation_allowed: bool,
    correction_target_resolved: bool | None,
) -> bool:
    if mutation_effect_class == "canonical_write":
        return intent == "commit" and canonical_write_allowed
    if mutation_effect_class == "correction_persistence":
        return intent == "commit" and canonical_write_allowed and correction_target_resolved is True
    if mutation_effect_class == "ledger_mutation":
        return intent == "commit" and ledger_mutation_allowed
    if mutation_effect_class == "draft_pending_persistence":
        return intent == "draft" and not canonical_write_allowed and not ledger_mutation_allowed
    return False


def _manager_semantic_decision_authorizes_canonical_write(
    *,
    manager_final_action: str,
    manager_semantic_decision: dict[str, Any] | None,
    payload: EstimatePayload,
) -> bool:
    if manager_final_action != "commit":
        return False
    decision = dict(manager_semantic_decision or {})
    if decision.get("semantic_authority") not in {"manager_llm", "deterministic_fake_provider"}:
        return False
    if decision.get("current_turn_intent") != "log_meal":
        return False
    if decision.get("final_action_candidate") != "commit":
        return False
    if decision.get("mutation_intent_candidate") != "canonical_write":
        return False
    trace_contract = dict(payload.trace_contract or {})
    if trace_contract.get("response_mode_hint") == "clarify_first":
        return False
    if [item for item in trace_contract.get("blocking_slots", []) if str(item).strip()]:
        return False
    if commit_evidence_blockers(trace_contract):
        return False
    return int(payload.estimated_kcal or 0) > 0


def _apply_manager_semantic_canonical_write_decision(
    *,
    payload: EstimatePayload,
    manager_final_action: str,
    manager_semantic_decision: dict[str, Any] | None,
) -> None:
    if not _manager_semantic_decision_authorizes_canonical_write(
        manager_final_action=manager_final_action,
        manager_semantic_decision=manager_semantic_decision,
        payload=payload,
    ):
        return
    trace_contract = dict(payload.trace_contract or {})
    trace_contract["canonical_write_decision"] = {
        "can_write_canonical": True,
        "source": "manager_semantic_decision",
        "semantic_authority": str((manager_semantic_decision or {}).get("semantic_authority") or ""),
        "mutation_intent_candidate": "canonical_write",
    }
    payload.trace_contract = trace_contract


def run_commit_boundary_preflight(
    *,
    payload: EstimatePayload | None,
    manager_final_action: str,
    active_body_plan_present: bool,
    correction_target: Any | None = None,
    manager_semantic_decision: dict[str, Any] | None = None,
) -> CommitBoundaryPreflightResult:
    effect_class = final_action_effect_class(manager_final_action)
    if effect_class == "none":
        return CommitBoundaryPreflightResult(
            checked=True,
            bypassed=True,
            bypass_reason="non_persistence_effect",
            blocked=False,
            failure_family=None,
            manager_final_action=str(manager_final_action or "no_commit"),
            mutation_effect_class=effect_class,
            projected_commit_intent=None,
            predicted_meal_status=None,
            canonical_write_allowed=None,
            ledger_mutation_allowed=None,
            correction_target_resolved=None,
            correction_target_validation=None,
            projection=None,
        )
    if payload is None:
        return CommitBoundaryPreflightResult(
            checked=True,
            bypassed=False,
            bypass_reason=None,
            blocked=True,
            failure_family="phase_a_commit_boundary_blocked",
            manager_final_action=str(manager_final_action or "no_commit"),
            mutation_effect_class=effect_class,
            projected_commit_intent=None,
            predicted_meal_status=None,
            canonical_write_allowed=None,
            ledger_mutation_allowed=None,
            correction_target_resolved=None,
            correction_target_validation=None,
            projection=None,
        )

    apply_commit_evidence_policy_to_payload(payload)
    _apply_manager_semantic_canonical_write_decision(
        payload=payload,
        manager_final_action=str(manager_final_action or ""),
        manager_semantic_decision=manager_semantic_decision,
    )
    projection = build_intake_boundary_projection(
        payload=payload,
        persistence_result=None,
        active_body_plan_present=active_body_plan_present,
    )
    decision = projection.commit_boundary_decision
    target_validation = validate_correction_target_ref(correction_target)
    target_resolved = _correction_target_resolved(correction_target)
    if effect_class == "correction_persistence" and target_resolved is None:
        target_resolved = False
    allowed = _effect_allowed(
        mutation_effect_class=effect_class,
        intent=decision.intent,
        canonical_write_allowed=decision.canonical_write_allowed,
        ledger_mutation_allowed=decision.ledger_mutation_allowed,
        correction_target_resolved=target_resolved,
    )
    failure_family = None if allowed else (
        commit_evidence_failure_family(payload.trace_contract) or "phase_a_commit_boundary_blocked"
    )
    return CommitBoundaryPreflightResult(
        checked=True,
        bypassed=False,
        bypass_reason=None,
        blocked=not allowed,
        failure_family=failure_family,
        manager_final_action=str(manager_final_action or "no_commit"),
        mutation_effect_class=effect_class,
        projected_commit_intent=decision.intent,
        predicted_meal_status=decision.predicted_meal_status,
        canonical_write_allowed=decision.canonical_write_allowed,
        ledger_mutation_allowed=decision.ledger_mutation_allowed,
        correction_target_resolved=target_resolved,
        correction_target_validation=target_validation,
        projection=projection,
    )


__all__ = [
    "CommitBoundaryPreflightResult",
    "run_commit_boundary_preflight",
]
