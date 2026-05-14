from __future__ import annotations

from typing import Any, Mapping


def build_rescue_proactive_candidate_bridge(
    *,
    rescue_artifact: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        rescue_artifact.get("status") != "pass"
        or rescue_artifact.get("proposal_presented_to_lab") is not True
    ):
        return _artifact(status="omitted", reason="rescue_not_eligible_for_proactive")
    card = _mapping(rescue_artifact.get("proposal_card"))
    guardrail = _mapping(rescue_artifact.get("guardrail_math"))
    pending_commit = _mapping(rescue_artifact.get("pending_rescue_commit_packet"))
    blockers = _blockers(
        rescue_artifact=rescue_artifact,
        card=card,
        pending_commit=pending_commit,
    )
    source_trace = _source_bridge_trace(
        card=card,
        guardrail=guardrail,
        pending_commit=pending_commit,
    )
    return _artifact(
        status="blocked" if blockers else "pass",
        blockers=blockers,
        proposal_kind=str(card.get("card_kind") or ""),
        proposal_committed=rescue_artifact.get("proposal_committed") is True,
        day_budget_mutated=rescue_artifact.get("day_budget_mutated") is True,
        candidate_spec={
            "trigger_type": "rescue_nudge",
            "candidate_kind": "same_day_rescue_proposal",
            "source_output_refs": [
                str(rescue_artifact.get("artifact_type") or ""),
                f"proposal:{card.get('card_kind') or ''}",
                f"pending_commit:{pending_commit.get('handoff_state') or ''}",
            ],
            "source_status": str(rescue_artifact.get("status") or ""),
            "downstream_workflow_family": "rescue",
            "source_bridge_trace": source_trace,
            "control_model": dict(_control_model(fixture_inputs)),
            "next_signal_fallback": "material_budget_change_or_user_reopens_rescue",
        }
        if not blockers
        else None,
    )


def omitted_rescue_proactive_candidate_bridge(reason: str) -> dict[str, Any]:
    return _artifact(status="omitted", reason=reason)


def _artifact(
    *,
    status: str,
    reason: str = "",
    blockers: list[str] | None = None,
    proposal_kind: str = "",
    proposal_committed: bool = False,
    day_budget_mutated: bool = False,
    candidate_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_rescue_proactive_candidate_bridge",
        "status": status,
        "reason": reason,
        "reads_rescue_outputs": status in {"pass", "blocked"},
        "candidate_created": status == "pass",
        "proposal_kind": proposal_kind,
        "proposal_committed": proposal_committed,
        "day_budget_mutated": day_budget_mutated,
        "candidate_spec": candidate_spec,
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "served_to_mainline_user": False,
        "canonical_product_mutation_allowed": False,
        "blockers": blockers or [],
    }


def _blockers(
    *,
    rescue_artifact: Mapping[str, Any],
    card: Mapping[str, Any],
    pending_commit: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if not str(card.get("card_kind") or ""):
        blockers.append("rescue.proposal_card_missing")
    if rescue_artifact.get("proposal_committed") is True:
        blockers.append("rescue.proposal_committed_not_allowed")
    if rescue_artifact.get("day_budget_mutated") is True:
        blockers.append("rescue.day_budget_mutated_not_allowed")
    if pending_commit.get("canonical_commit_requested") is True:
        blockers.append("rescue.pending_commit_requested_not_allowed")
    return blockers


def _source_bridge_trace(
    *,
    card: Mapping[str, Any],
    guardrail: Mapping[str, Any],
    pending_commit: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "downstream_workflow_family": "rescue",
        "proposal_kind": str(card.get("card_kind") or ""),
        "recovery_viability": str(guardrail.get("recovery_viability") or ""),
        "recommended_days": _int(card.get("recommended_days")),
        "daily_kcal_adjustment": _int(card.get("daily_kcal_adjustment")),
        "pending_commit_handoff_state": str(pending_commit.get("handoff_state") or ""),
        "requires_explicit_user_rescue_commit": (
            pending_commit.get("requires_explicit_user_rescue_commit") is True
        ),
        "rescue_handoff_mode": "chat_first_independent_message",
    }


def _control_model(fixture_inputs: Mapping[str, Any]) -> Mapping[str, Any]:
    models = _mapping(fixture_inputs.get("user_control_models"))
    model = _mapping(models.get("rescue_nudge"))
    return {
        "dismiss_reason_choices": [
            str(item) for item in model.get("dismiss_reason_choices") or []
        ],
        "snooze_window": dict(_mapping(model.get("snooze_window"))),
        "next_signal_required": str(model.get("next_signal_required") or ""),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = [
    "build_rescue_proactive_candidate_bridge",
    "omitted_rescue_proactive_candidate_bridge",
]
