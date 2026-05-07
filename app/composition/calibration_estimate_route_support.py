from __future__ import annotations

from datetime import datetime
from typing import Any

from app.composition.calibration_proposal_inbox import (
    load_open_calibration_proposal_inbox,
)
from app.database import get_or_create_user
from app.schemas import EstimateRequest


def has_explicit_calibration_action_request(request: EstimateRequest) -> bool:
    return (
        request.calibration_action is not None
        or request.calibration_proposal_container_id is not None
    )


def has_explicit_calibration_preview_request(request: EstimateRequest) -> bool:
    return request.calibration_preview_requested is True and not has_explicit_calibration_action_request(request)


def parse_calibration_action_accepted_at(request: EstimateRequest) -> datetime | None:
    if request.calibration_action_accepted_at is None:
        return None
    try:
        return datetime.fromisoformat(request.calibration_action_accepted_at)
    except ValueError as exc:
        raise ValueError("calibration_action_accepted_at must be an ISO datetime") from exc


def has_open_calibration_proposal_followup_without_explicit_route_action(
    db: Any,
    *,
    user_external_id: str,
    request: EstimateRequest,
) -> bool:
    if request.persist_calibration_proposal is not True:
        return False
    if has_explicit_calibration_preview_request(request) or has_explicit_calibration_action_request(request):
        return False
    user = get_or_create_user(db, user_external_id)
    return bool(load_open_calibration_proposal_inbox(db, user_id=user.id, limit=1))


def build_calibration_action_route_payload(general_chat_result: Any) -> dict[str, Any]:
    ui_hints = dict(general_chat_result.ui_hints or {})
    action_result = general_chat_result.calibration_action_result
    proposal_status = action_result.get("proposal_status") if isinstance(action_result, dict) else None
    state_delta = {
        "calibration_action_processed": action_result is not None,
        "proposal_status": proposal_status,
        "plan_mutated": bool(ui_hints.get("plan_mutation_authorized")),
        "ledger_mutated": bool(ui_hints.get("ledger_mutation_authorized")),
    }
    manager_decision = {
        "intent_type": "calibration",
        "workflow_effect": general_chat_result.workflow_effect,
        "tool_calls": [],
        "explicit_structured_action": True,
    }
    return {
        "manager_decision": manager_decision,
        "intake_execution_manager": {
            "final": {
                "final_action": "calibration_action",
                "workflow_effect": general_chat_result.workflow_effect,
            },
            "persistence_result": action_result,
        },
        "state_delta": state_delta,
        "sidecar": {},
        "ui_hints": ui_hints,
        "required_read_surfaces": list(general_chat_result.required_read_surfaces),
        "calibration_action_result": action_result,
    }


def build_calibration_preview_route_payload(general_chat_result: Any) -> dict[str, Any]:
    ui_hints = dict(general_chat_result.ui_hints or {})
    proposal_artifact = general_chat_result.proposal_artifact
    state_delta = {
        "calibration_preview_processed": True,
        "proposal_persisted": proposal_artifact is not None,
        "proposal_container_id": (
            proposal_artifact.get("proposal_container_id") if isinstance(proposal_artifact, dict) else None
        ),
        "plan_mutated": False,
        "ledger_mutated": False,
    }
    manager_decision = {
        "intent_type": "calibration",
        "workflow_effect": general_chat_result.workflow_effect,
        "tool_calls": [],
        "explicit_structured_preview": True,
    }
    return {
        "manager_decision": manager_decision,
        "intake_execution_manager": {
            "final": {
                "final_action": "calibration_preview",
                "workflow_effect": general_chat_result.workflow_effect,
            },
            "persistence_result": proposal_artifact,
        },
        "state_delta": state_delta,
        "sidecar": {
            "calibration_diagnostic": general_chat_result.calibration_diagnostic,
            "input_assembly": general_chat_result.input_assembly,
            "proposal_artifact": proposal_artifact,
        },
        "ui_hints": ui_hints,
        "required_read_surfaces": list(general_chat_result.required_read_surfaces),
        "calibration_diagnostic": general_chat_result.calibration_diagnostic,
        "input_assembly": general_chat_result.input_assembly,
        "proposal_response": general_chat_result.proposal_response,
        "proposal_artifact": proposal_artifact,
    }


def build_calibration_raw_text_fallback_route_payload(general_chat_result: Any) -> dict[str, Any]:
    ui_hints = {
        **dict(general_chat_result.ui_hints or {}),
        "raw_text_authorized_mutation": False,
    }
    workflow_effect = "raw_text_route_fallback_without_calibration_state_mutation"
    return {
        "manager_decision": {
            "intent_type": "calibration",
            "workflow_effect": workflow_effect,
            "tool_calls": [],
            "explicit_structured_action": False,
        },
        "intake_execution_manager": {
            "final": {
                "final_action": "answer_only",
                "workflow_effect": workflow_effect,
            },
            "persistence_result": None,
        },
        "state_delta": {
            "proposal_persisted": False,
            "plan_mutated": False,
            "ledger_mutated": False,
        },
        "sidecar": {},
        "ui_hints": ui_hints,
        "required_read_surfaces": list(general_chat_result.required_read_surfaces),
    }
