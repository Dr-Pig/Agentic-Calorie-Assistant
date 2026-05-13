from __future__ import annotations

from typing import Any, Mapping

from app.rescue.application.proposal_audit_projection import append_audit_event_once
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("rescue.application.proposal_inbox_history_audit")
ACTIONABLE_STATUSES = {"open", "presented", "negotiating"}
VISIBLE_INBOX_STATUSES = ACTIONABLE_STATUSES | {"accepted"}
PRIMARY_ACTIONS = ["accept_rescue_plan", "dismiss_rescue_plan"]
PRODUCTION_DORMANT_FLAGS = {
    "mainline_activation_enabled": False,
    "mainline_route_or_api_mount_allowed": False,
    "production_scheduler_delivery_allowed": False,
    "production_db_mutation_allowed": False,
    "canonical_mutation_changed": False,
    "durable_product_memory_written_in_mainline": False,
}


def build_rescue_proposal_inbox_history_audit_read_model(
    *,
    proposal_artifacts: list[Mapping[str, Any]],
) -> dict[str, Any]:
    proposals: dict[str, dict[str, Any]] = {}
    audit_events: list[dict[str, Any]] = []
    blockers: list[str] = []
    for artifact in proposal_artifacts:
        artifact_type = str(artifact.get("artifact_type") or "")
        if artifact_type == "rescue_response_card_packet":
            _merge_presented(proposals, artifact)
        elif artifact_type == "accept_rescue_plan_lab_contract":
            _merge_accept_contract(proposals, audit_events, artifact)
        elif artifact_type == "isolated_lab_rescue_commit_effect":
            _merge_accepted(proposals, audit_events, artifact)
        elif artifact_type == "dismiss_rescue_plan_lab_contract":
            _merge_dismissed(proposals, audit_events, artifact)
        else:
            blockers.append(f"unsupported_artifact_type:{artifact_type}")

    history = _sorted_items(proposals.values())
    inbox = [item for item in history if item["proposal_status"] in VISIBLE_INBOX_STATUSES]
    active = [item for item in inbox if item["proposal_status"] in ACTIONABLE_STATUSES]
    return {
        "artifact_type": "rescue_proposal_inbox_history_audit_read_model",
        "status": "pass" if not blockers else "blocked",
        "owner": "app/rescue",
        "consumer": "lab_rescue_user_visible_mirror",
        "chat_first_primary_surface": True,
        "ui_is_mirror_only": True,
        "lab_enabled": True,
        "lab_isolated": True,
        "active_proposal_inbox": active,
        "proposal_inbox_mirror": inbox,
        "history_items": history,
        "audit_events": audit_events,
        "raw_trace_exposed": False,
        "sidecar_diagnostic_exposed": False,
        "internal_reasoning_exposed": False,
        "blockers": blockers,
        **dict(PRODUCTION_DORMANT_FLAGS),
    }


def _merge_presented(proposals: dict[str, dict[str, Any]], artifact: Mapping[str, Any]) -> None:
    card = _mapping(artifact.get("rescue_response_card"))
    proposal_id = str(card.get("proposal_id") or "")
    if not proposal_id:
        return
    proposals[proposal_id] = _base_item(
        proposal_id=proposal_id,
        status="presented",
        recommended_days=_int(card.get("recommended_days")),
        daily_kcal_adjustment=_int(card.get("daily_kcal_adjustment")),
        cap_mode=str(card.get("cap_mode") or ""),
    )


def _merge_accepted(
    proposals: dict[str, dict[str, Any]],
    audit_events: list[dict[str, Any]],
    artifact: Mapping[str, Any],
) -> None:
    overlay = _mapping(artifact.get("proposal_status_overlay"))
    effect = _mapping(artifact.get("rescue_commit_effect"))
    proposal_id = str(overlay.get("proposal_id") or effect.get("proposal_id") or "")
    if not proposal_id:
        return
    item = proposals.get(proposal_id) or _base_item(proposal_id=proposal_id, status="accepted")
    item.update(
        {
            "proposal_status": "accepted",
            "primary_actions": [],
            "accepted_at": str(overlay.get("accepted_at") or ""),
            "summary": _accepted_summary(effect),
            "expandable_explanation": _accepted_explanation(effect),
        }
    )
    proposals[proposal_id] = item
    append_audit_event_once(
        audit_events,
        event_type="accepted",
        proposal_id=proposal_id,
        occurred_at=overlay.get("accepted_at"),
        artifact=artifact,
    )


def _merge_accept_contract(
    proposals: dict[str, dict[str, Any]],
    audit_events: list[dict[str, Any]],
    artifact: Mapping[str, Any],
) -> None:
    accepted = _mapping(artifact.get("accepted_projection"))
    proposal_id = str(accepted.get("proposal_id") or "")
    if not proposal_id:
        return
    item = proposals.get(proposal_id) or _base_item(proposal_id=proposal_id, status="accepted")
    item.update(
        {
            "proposal_status": "accepted",
            "primary_actions": [],
            "accepted_at": str(accepted.get("accepted_at") or ""),
        }
    )
    proposals[proposal_id] = item
    append_audit_event_once(
        audit_events,
        event_type="accepted",
        proposal_id=proposal_id,
        occurred_at=accepted.get("accepted_at"),
        artifact=artifact,
    )


def _merge_dismissed(
    proposals: dict[str, dict[str, Any]],
    audit_events: list[dict[str, Any]],
    artifact: Mapping[str, Any],
) -> None:
    dismissed = _mapping(artifact.get("dismissed_projection"))
    proposal_id = str(dismissed.get("proposal_id") or "")
    if not proposal_id:
        return
    item = proposals.get(proposal_id) or _base_item(proposal_id=proposal_id, status="dismissed")
    reason = str(dismissed.get("dismiss_reason") or "")
    item.update(
        {
            "proposal_status": "dismissed",
            "primary_actions": [],
            "dismissed_at": str(dismissed.get("dismissed_at") or ""),
            "summary": "Dismissed rescue proposal for this instance.",
            "expandable_explanation": reason or "The proposal remains visible in history and audit.",
            "same_proposal_redelivery_allowed": False,
        }
    )
    proposals[proposal_id] = item
    append_audit_event_once(
        audit_events,
        event_type="dismissed",
        proposal_id=proposal_id,
        occurred_at=dismissed.get("dismissed_at"),
        artifact=artifact,
    )


def _base_item(
    *,
    proposal_id: str,
    status: str,
    recommended_days: int = 0,
    daily_kcal_adjustment: int = 0,
    cap_mode: str = "",
) -> dict[str, Any]:
    summary = _summary(recommended_days, daily_kcal_adjustment)
    return {
        "proposal_id": proposal_id,
        "proposal_status": status,
        "title": "Rescue plan",
        "summary": summary,
        "expandable_explanation": f"{summary} Cap mode: {cap_mode or 'unknown'}.",
        "primary_actions": list(PRIMARY_ACTIONS) if status in ACTIONABLE_STATUSES else [],
        "raw_trace_exposed": False,
        "sidecar_diagnostic_exposed": False,
    }


def _sorted_items(items: Any) -> list[dict[str, Any]]:
    return sorted((dict(item) for item in items), key=lambda item: item["proposal_id"], reverse=True)


def _accepted_summary(effect: Mapping[str, Any]) -> str:
    days = _int(effect.get("recommended_days"))
    daily = abs(_int(effect.get("daily_kcal_adjustment")))
    return f"Accepted rescue plan: {daily} kcal per day for {days} days."


def _accepted_explanation(effect: Mapping[str, Any]) -> str:
    remaining = effect.get("refreshed_remaining_kcal")
    return f"Budget mirror refreshed for the lab. Remaining kcal after overlay: {remaining}."


def _summary(days: int, daily_adjustment: int) -> str:
    if days <= 0 or daily_adjustment == 0:
        return "Rescue proposal."
    return f"Recover about {abs(daily_adjustment)} kcal per day for {days} days."


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return int(value or 0)


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_rescue_proposal_inbox_history_audit_read_model"]
