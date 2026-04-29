from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from ...runtime.contracts.phase_a import TransitionGuardResult


_BLOCKING_GUARD_VERDICTS = {"answer_only", "clarify_required", "block"}
FINAL_ACTION_EFFECT_CLASSES: dict[str, str] = {
    "commit": "canonical_write",
    "correction_applied": "correction_persistence",
    "overshoot_note": "ledger_mutation",
    "ask_followup": "draft_pending_persistence",
}
PERSISTENCE_EFFECT_ACTIONS = frozenset(FINAL_ACTION_EFFECT_CLASSES)


@dataclass(frozen=True)
class FinalActionMutationClassification:
    checked: bool
    manager_final_action: str
    mutation_like: bool
    mutation_effect_class: str
    blocked: bool
    failure_family: str | None
    transition_guard_verdict: str
    transition_guard_reason: str
    blocked_mutation: str | None
    affected_object_type: str
    affected_object_id: str | None

    def trace_payload(
        self,
        *,
        repair_attempted: bool = False,
        repair_result: str | None = None,
    ) -> dict[str, Any]:
        return {
            "checked": self.checked,
            "blocked": self.blocked,
            "transition_guard_verdict": self.transition_guard_verdict,
            "transition_guard_reason": self.transition_guard_reason,
            "blocked_mutation": self.blocked_mutation,
            "manager_final_action": self.manager_final_action,
            "mutation_like": self.mutation_like,
            "mutation_effect_class": self.mutation_effect_class,
            "failure_family": self.failure_family,
            "affected_object_type": self.affected_object_type,
            "affected_object_id": self.affected_object_id,
            "repair_attempted": repair_attempted,
            "repair_result": repair_result,
        }


def final_action_effect_class(
    final_action: str,
    *,
    persistence_effect_actions: Collection[str] | None = None,
) -> str:
    action = str(final_action or "")
    if persistence_effect_actions is not None and action not in persistence_effect_actions:
        return "none"
    if persistence_effect_actions is not None and action in persistence_effect_actions:
        return FINAL_ACTION_EFFECT_CLASSES.get(action, "persistence_effect")
    return FINAL_ACTION_EFFECT_CLASSES.get(action, "none")


def final_action_has_persistence_effect(final_action: str) -> bool:
    return final_action_effect_class(final_action) != "none"


def classify_final_action_mutation(
    *,
    manager_payload: Mapping[str, Any],
    transition_guard_result: TransitionGuardResult,
    persistence_effect_actions: Collection[str] | None = None,
) -> FinalActionMutationClassification:
    final_action = str(manager_payload.get("final_action") or "no_commit")
    effect_class = final_action_effect_class(
        final_action,
        persistence_effect_actions=persistence_effect_actions,
    )
    mutation_like = effect_class != "none"
    blocked = mutation_like and transition_guard_result.verdict in _BLOCKING_GUARD_VERDICTS
    return FinalActionMutationClassification(
        checked=True,
        manager_final_action=final_action,
        mutation_like=mutation_like,
        mutation_effect_class=effect_class,
        blocked=blocked,
        failure_family="phase_a_transition_guard_blocked" if blocked else None,
        transition_guard_verdict=transition_guard_result.verdict,
        transition_guard_reason=transition_guard_result.reason,
        blocked_mutation=transition_guard_result.blocked_mutation,
        affected_object_type=transition_guard_result.affected_object_type,
        affected_object_id=transition_guard_result.affected_object_id,
    )


__all__ = [
    "FINAL_ACTION_EFFECT_CLASSES",
    "FinalActionMutationClassification",
    "PERSISTENCE_EFFECT_ACTIONS",
    "classify_final_action_mutation",
    "final_action_effect_class",
    "final_action_has_persistence_effect",
]
