from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...runtime.contracts.phase_a import PhaseABoundaryProjection
from ...shared.contracts.intake_results import EstimatePayload
from .final_action_mutation_classifier import final_action_effect_class
from .phase_a_boundary_projection import build_intake_boundary_projection


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
        }


def _correction_target_resolved(correction_target: Any | None) -> bool | None:
    if not isinstance(correction_target, dict) or not correction_target:
        return None
    source = str(correction_target.get("target_resolution_source") or "").strip().lower()
    has_evidence = source not in {"", "none", "unknown"}
    if not has_evidence:
        return None
    return any(
        correction_target.get(key) is not None
        for key in ("meal_thread_id", "meal_version_id", "meal_id", "target_object_id")
    )


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
        target_allowed = correction_target_resolved is not False
        return intent == "commit" and canonical_write_allowed and target_allowed
    if mutation_effect_class == "ledger_mutation":
        return intent == "commit" and ledger_mutation_allowed
    if mutation_effect_class == "draft_pending_persistence":
        return intent == "draft" and not canonical_write_allowed and not ledger_mutation_allowed
    return False


def run_commit_boundary_preflight(
    *,
    payload: EstimatePayload | None,
    manager_final_action: str,
    active_body_plan_present: bool,
    correction_target: Any | None = None,
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
            projection=None,
        )

    projection = build_intake_boundary_projection(
        payload=payload,
        persistence_result=None,
        active_body_plan_present=active_body_plan_present,
    )
    decision = projection.commit_boundary_decision
    target_resolved = _correction_target_resolved(correction_target)
    allowed = _effect_allowed(
        mutation_effect_class=effect_class,
        intent=decision.intent,
        canonical_write_allowed=decision.canonical_write_allowed,
        ledger_mutation_allowed=decision.ledger_mutation_allowed,
        correction_target_resolved=target_resolved,
    )
    return CommitBoundaryPreflightResult(
        checked=True,
        bypassed=False,
        bypass_reason=None,
        blocked=not allowed,
        failure_family=None if allowed else "phase_a_commit_boundary_blocked",
        manager_final_action=str(manager_final_action or "no_commit"),
        mutation_effect_class=effect_class,
        projected_commit_intent=decision.intent,
        predicted_meal_status=decision.predicted_meal_status,
        canonical_write_allowed=decision.canonical_write_allowed,
        ledger_mutation_allowed=decision.ledger_mutation_allowed,
        correction_target_resolved=target_resolved,
        projection=projection,
    )


__all__ = [
    "CommitBoundaryPreflightResult",
    "run_commit_boundary_preflight",
]
