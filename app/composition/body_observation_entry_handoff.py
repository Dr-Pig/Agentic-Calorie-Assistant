from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.composition.body_observation_manager_turn import execute_body_observation_manager_turn
from app.runtime.agent.manager import IntakeManagerResult
from app.runtime.contracts.phase_a import CurrentTurnContextV1, ManagerContextPack


def manager_requests_body_observation_handoff(manager_decision: IntakeManagerResult) -> bool:
    return (
        manager_decision.intent_type == "body_observation"
        or manager_decision.workflow_effect == "route_to_body_observation"
    )


async def execute_body_observation_entry_handoff(
    db: Session,
    *,
    request_id: str,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    allow_search: bool,
    manager_provider: Any,
    state_before: Any,
    current_turn_context: CurrentTurnContextV1 | None,
    manager_context_pack: ManagerContextPack | None,
    manager_context_packet_v1: dict[str, Any] | None,
    phase_a_trace: dict[str, Any] | None,
    entry_manager_decision: IntakeManagerResult,
) -> dict[str, Any]:
    handoff_trace = {
        **dict(phase_a_trace or {}),
        "entry_manager_body_observation_handoff": {
            "semantic_owner": "manager",
            "intent_type": entry_manager_decision.intent_type,
            "workflow_effect": entry_manager_decision.workflow_effect,
            "final_action": entry_manager_decision.final_action,
            "deterministic_raw_text_routing": False,
        },
    }
    return await execute_body_observation_manager_turn(
        db,
        request_id=request_id,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date,
        allow_search=allow_search,
        manager_provider=manager_provider,
        state_before=state_before,
        current_turn_context=current_turn_context,
        manager_context_pack=manager_context_pack,
        manager_context_packet_v1=manager_context_packet_v1,
        phase_a_trace=handoff_trace,
    )


__all__ = [
    "execute_body_observation_entry_handoff",
    "manager_requests_body_observation_handoff",
]
