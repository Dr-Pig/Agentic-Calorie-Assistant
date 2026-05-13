from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.accept_rescue_plan_contract"
)
SUPPORTED_COMMIT_SOURCES = {"chat", "ui", "smart_chip"}
REQUIRED_NEXT_EFFECTS = [
    "update_proposal_container_status",
    "create_rescue_overlay_ledger_entries",
    "refresh_current_budget_view",
    "request_recommendation_posture_refresh",
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


def build_accept_rescue_plan_lab_contract(
    *,
    rescue_response_card_packet: Mapping[str, Any],
    accept_request: Mapping[str, Any],
) -> dict[str, Any]:
    card = _card(rescue_response_card_packet)
    blockers = [
        *_packet_blockers(rescue_response_card_packet, card),
        *_request_blockers(accept_request, card),
    ]
    if blockers:
        return _artifact(status="blocked", blockers=blockers)
    return _artifact(
        status="pass",
        accepted_projection=_accepted_projection(accept_request),
        lab_isolated_mutation_allowed=True,
    )


def _artifact(
    *,
    status: str,
    blockers: list[str] | None = None,
    accepted_projection: dict[str, Any] | None = None,
    lab_isolated_mutation_allowed: bool = False,
) -> dict[str, Any]:
    return {
        "artifact_type": "accept_rescue_plan_lab_contract",
        "status": status,
        "owner": "app/rescue",
        "consumer": "isolated_lab_commit_effect_and_ledger_overlay",
        "accepted_projection": accepted_projection,
        "required_next_effects": list(REQUIRED_NEXT_EFFECTS) if status == "pass" else [],
        "ledger_entry_creation_deferred_to_pr19": status == "pass",
        "budget_view_refresh_deferred_to_pr19": status == "pass",
        "recommendation_posture_refresh_deferred_to_pr21": status == "pass",
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
    if request.get("action_id") != "accept_rescue_plan":
        blockers.append("accept_request.action_id_not_accept_rescue_plan")
    if not str(request.get("proposal_id") or ""):
        blockers.append("accept_request.proposal_id_missing")
    elif card and request.get("proposal_id") != card.get("proposal_id"):
        blockers.append("accept_request.proposal_id_mismatch")
    if not str(request.get("user_id") or ""):
        blockers.append("accept_request.user_id_missing")
    if not _valid_iso_datetime(request.get("accepted_at")):
        blockers.append("accept_request.accepted_at_not_iso_datetime")
    if not str(request.get("cap_mode") or ""):
        blockers.append("accept_request.cap_mode_missing")
    elif card and request.get("cap_mode") != card.get("cap_mode"):
        blockers.append("accept_request.cap_mode_mismatch")
    commit_source = str(request.get("commit_source") or "")
    if commit_source not in SUPPORTED_COMMIT_SOURCES:
        blockers.append(f"accept_request.commit_source_unsupported:{commit_source}")
    blockers.extend(_source_audit_blockers(_mapping(request.get("source_audit"))))
    return blockers


def _accepted_projection(request: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "proposal_id": str(request.get("proposal_id") or ""),
        "proposal_status": "accepted",
        "user_id": str(request.get("user_id") or ""),
        "accepted_at": str(request.get("accepted_at") or ""),
        "cap_mode": str(request.get("cap_mode") or ""),
        "commit_source": str(request.get("commit_source") or ""),
        "source_audit": dict(_mapping(request.get("source_audit"))),
    }


def _source_audit_blockers(source_audit: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not str(source_audit.get("surface") or ""):
        blockers.append("accept_request.source_audit.surface_missing")
    if not str(source_audit.get("source_event_id") or ""):
        blockers.append("accept_request.source_audit.source_event_id_missing")
    if not str(source_audit.get("run_id") or ""):
        blockers.append("accept_request.source_audit.run_id_missing")
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
    "SUPPORTED_COMMIT_SOURCES",
    "build_accept_rescue_plan_lab_contract",
]
