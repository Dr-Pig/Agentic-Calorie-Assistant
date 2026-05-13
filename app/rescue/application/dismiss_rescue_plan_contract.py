from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.dismiss_rescue_plan_contract"
)
SUPPORTED_DISMISS_SOURCES = {"chat", "ui", "smart_chip"}
REQUIRED_NEXT_EFFECTS = [
    "update_proposal_container_status",
    "remove_from_active_proposal_inbox",
    "append_history_audit_entry",
    "suppress_same_proposal_redelivery",
]
FALSE_OUTPUT_FLAGS = {
    "runtime_effect_allowed": False,
    "canonical_mutation_changed": False,
    "mainline_activation_enabled": False,
    "production_db_mutation_allowed": False,
    "production_scheduler_delivery_allowed": False,
    "proposal_committed": False,
    "ledger_entry_created": False,
    "durable_product_memory_written_in_mainline": False,
    "manager_context_packet_changed_in_mainline": False,
}


def build_dismiss_rescue_plan_lab_contract(
    *,
    rescue_response_card_packet: Mapping[str, Any],
    dismiss_request: Mapping[str, Any],
) -> dict[str, Any]:
    card = _card(rescue_response_card_packet)
    blockers = [
        *_packet_blockers(rescue_response_card_packet, card),
        *_request_blockers(dismiss_request, card),
    ]
    if blockers:
        return _artifact(status="blocked", blockers=blockers)
    return _artifact(
        status="pass",
        dismissed_projection=_dismissed_projection(dismiss_request),
        lab_isolated_mutation_allowed=True,
    )


def _artifact(
    *,
    status: str,
    blockers: list[str] | None = None,
    dismissed_projection: dict[str, Any] | None = None,
    lab_isolated_mutation_allowed: bool = False,
) -> dict[str, Any]:
    return {
        "artifact_type": "dismiss_rescue_plan_lab_contract",
        "status": status,
        "owner": "app/rescue",
        "consumer": "proposal_inbox_history_audit_read_model",
        "dismissed_projection": dismissed_projection,
        "required_next_effects": list(REQUIRED_NEXT_EFFECTS) if status == "pass" else [],
        "backup_switching_allowed": False,
        "dismiss_reason_required": False,
        "permanent_rescue_suppression": False,
        "snooze_created": False,
        "same_proposal_redelivery_allowed": False,
        "ledger_entry_creation_allowed": False,
        "recommendation_posture_refresh_required": False,
        "lab_isolated_mutation_allowed": lab_isolated_mutation_allowed,
        "blockers": blockers or [],
        **dict(FALSE_OUTPUT_FLAGS),
    }


def _packet_blockers(
    packet: Mapping[str, Any],
    card: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if packet.get("artifact_type") != "rescue_response_card_packet":
        blockers.append("rescue_response_card_packet.unsupported_artifact_type")
    if packet.get("status") != "pass":
        blockers.append("rescue_response_card_packet.status_not_pass")
    if not card:
        blockers.append("rescue_response_card_packet.card_missing")
    for flag in FALSE_OUTPUT_FLAGS:
        if packet.get(flag) is True:
            blockers.append(f"rescue_response_card_packet.{flag}")
    return blockers


def _request_blockers(
    request: Mapping[str, Any],
    card: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if request.get("action_id") != "dismiss_rescue_plan":
        blockers.append("dismiss_request.action_id_not_dismiss_rescue_plan")
    if not str(request.get("proposal_id") or ""):
        blockers.append("dismiss_request.proposal_id_missing")
    elif card and request.get("proposal_id") != card.get("proposal_id"):
        blockers.append("dismiss_request.proposal_id_mismatch")
    if not str(request.get("user_id") or ""):
        blockers.append("dismiss_request.user_id_missing")
    if not _valid_iso_datetime(request.get("dismissed_at")):
        blockers.append("dismiss_request.dismissed_at_not_iso_datetime")
    dismiss_source = str(request.get("dismiss_source") or "")
    if dismiss_source not in SUPPORTED_DISMISS_SOURCES:
        blockers.append(f"dismiss_request.dismiss_source_unsupported:{dismiss_source}")
    blockers.extend(_source_audit_blockers(_mapping(request.get("source_audit"))))
    blockers.extend(_forbidden_side_effect_blockers(request))
    return blockers


def _dismissed_projection(request: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "proposal_id": str(request.get("proposal_id") or ""),
        "proposal_status": "dismissed",
        "user_id": str(request.get("user_id") or ""),
        "dismissed_at": str(request.get("dismissed_at") or ""),
        "dismiss_source": str(request.get("dismiss_source") or ""),
        "dismiss_reason": str(request.get("dismiss_reason") or "") or None,
        "source_audit": dict(_mapping(request.get("source_audit"))),
    }


def _forbidden_side_effect_blockers(request: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if str(request.get("switch_to_backup_proposal_id") or ""):
        blockers.append("dismiss_request.backup_switching_forbidden")
    if request.get("permanent_rescue_suppression") is True:
        blockers.append("dismiss_request.permanent_rescue_suppression_forbidden")
    if str(request.get("snooze_until") or ""):
        blockers.append("dismiss_request.snooze_forbidden")
    if request.get("dismiss_reason_required") is True:
        blockers.append("dismiss_request.dismiss_reason_required_forbidden")
    return blockers


def _source_audit_blockers(source_audit: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not str(source_audit.get("surface") or ""):
        blockers.append("dismiss_request.source_audit.surface_missing")
    if not str(source_audit.get("source_event_id") or ""):
        blockers.append("dismiss_request.source_audit.source_event_id_missing")
    if not str(source_audit.get("run_id") or ""):
        blockers.append("dismiss_request.source_audit.run_id_missing")
    return blockers


def _valid_iso_datetime(value: Any) -> bool:
    raw = str(value or "")
    if "T" not in raw:
        return False
    try:
        datetime.fromisoformat(raw)
    except ValueError:
        return False
    return True


def _card(packet: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(packet.get("rescue_response_card"))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "SUPPORTED_DISMISS_SOURCES",
    "build_dismiss_rescue_plan_lab_contract",
]
