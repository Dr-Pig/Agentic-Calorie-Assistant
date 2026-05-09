from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_no_send_review_sink"
)

FALSE_FLAGS = {
    "runtime_effect_allowed": False,
    "delivery_attempted": False,
    "proactive_sent": False,
    "scheduler_enabled": False,
    "scheduler_enqueued": False,
    "live_delivery_allowed": False,
    "push_or_line_delivery_connected": False,
    "scheduler_activation_allowed": False,
    "manager_context_injected": False,
    "manager_context_packet_changed": False,
    "recommendation_served": False,
    "rescue_committed": False,
    "proposal_committed": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "meal_thread_mutated": False,
    "durable_memory_written": False,
    "durable_snooze_written": False,
    "mutation_changed": False,
    "user_facing_behavior_changed": False,
}
CLAIM_FLAGS = tuple(FALSE_FLAGS.keys()) + (
    "canonical_mutation_changed",
    "durable_product_memory_written",
    "user_facing_visible",
)
NON_CLAIMS = [
    "not_notification",
    "not_scheduler_queue",
    "not_live_delivery",
    "not_user_facing_route",
    "not_durable_outbox",
    "not_runtime_mutation",
]


def build_no_send_review_sink(
    *,
    no_send_candidates: list[Mapping[str, Any]],
    interaction_artifacts: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    interactions = list(interaction_artifacts or [])
    blockers = [
        *_candidate_blockers(no_send_candidates),
        *_interaction_blockers(interactions),
        *_shape_blockers(no_send_candidates, interactions),
    ]
    records = [] if blockers else _records(no_send_candidates, interactions)
    return {
        "artifact_type": "proactive_no_send_review_sink_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/runtime",
        "consumer": "future_proactive_shadow_e2e_review",
        "retirement_trigger": "approved_proactive_scheduler_runtime_activation_plan",
        "record_count": len(records),
        "records": records,
        "blockers": blockers,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _candidate_blockers(candidates: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for index, candidate in enumerate(candidates):
        prefix = f"candidate[{index}]"
        if candidate.get("artifact_type") != "proactive_no_send_nudge_candidate":
            blockers.append(f"{prefix}.unsupported_artifact_type")
        if candidate.get("status") != "pass":
            blockers.append(f"{prefix}.status_not_pass")
        blockers.extend(_claim_blockers(prefix, candidate))
        blockers.extend(_control_blockers(prefix, candidate))
    return blockers


def _interaction_blockers(interactions: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for index, interaction in enumerate(interactions):
        prefix = f"interaction[{index}]"
        if (
            interaction.get("artifact_type")
            != "proactive_no_send_interaction_model_artifact"
        ):
            blockers.append(f"{prefix}.unsupported_artifact_type")
        if interaction.get("status") != "pass":
            blockers.append(f"{prefix}.status_not_pass")
        blockers.extend(_claim_blockers(prefix, interaction))
    return blockers


def _shape_blockers(
    candidates: list[Mapping[str, Any]],
    interactions: list[Mapping[str, Any]],
) -> list[str]:
    if len(interactions) <= len(candidates):
        return []
    return ["interaction.count_exceeds_candidate_count"]


def _claim_blockers(prefix: str, artifact: Mapping[str, Any]) -> list[str]:
    return [
        f"{prefix}.{flag}"
        for flag in CLAIM_FLAGS
        if artifact.get(flag) is True
    ]


def _control_blockers(prefix: str, candidate: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not _has_nonempty_list(candidate.get("dismiss_reason_choices")):
        blockers.append(f"{prefix}.dismiss_reason_choices_missing")
    if not _has_nonempty_mapping(candidate.get("snooze_window")):
        blockers.append(f"{prefix}.snooze_window_missing")
    if not str(candidate.get("undo_scope") or "").strip():
        blockers.append(f"{prefix}.undo_scope_missing")
    if not str(candidate.get("next_signal_required") or "").strip():
        blockers.append(f"{prefix}.next_signal_required_missing")
    return blockers


def _records(
    candidates: list[Mapping[str, Any]],
    interactions: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        _record(candidate, interactions[index] if index < len(interactions) else None)
        for index, candidate in enumerate(candidates)
    ]


def _record(
    candidate: Mapping[str, Any],
    interaction: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "trigger_type": str(candidate.get("trigger_type") or ""),
        "candidate_kind": str(candidate.get("candidate_kind") or ""),
        "candidate_status": str(candidate.get("status") or ""),
        "interaction_status": str(interaction.get("status") or "")
        if interaction is not None
        else "not_provided",
        "interaction_action": str(interaction.get("action") or "")
        if interaction is not None
        else None,
        "delivery_attempted": False,
        "scheduler_enqueued": False,
        "user_facing_visible": False,
        "next_signal_required": str(candidate.get("next_signal_required") or ""),
        "dismiss_reason_choices_present": _has_nonempty_list(
            candidate.get("dismiss_reason_choices")
        ),
        "snooze_window_present": _has_nonempty_mapping(candidate.get("snooze_window")),
        "undo_scope": str(candidate.get("undo_scope") or ""),
    }


def _has_nonempty_list(value: object) -> bool:
    return isinstance(value, list) and len(value) > 0


def _has_nonempty_mapping(value: object) -> bool:
    return isinstance(value, Mapping) and bool(value)


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_no_send_review_sink",
]
