from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_record_session_artifact import (
    memory_record_blocked_session,
)
from app.advanced_shadow_lab.product_lab_memory_record_session_state import (
    MemoryRecordSessionState,
)
from app.advanced_shadow_lab.product_lab_session_policy import session_blockers
from app.advanced_shadow_lab.product_lab_session_store import write_session_record
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_memory_record_session"
)


def run_advanced_product_lab_memory_record_session(
    *,
    artifact_root: Path | str,
    session_id: str,
    fixture_inputs: Mapping[str, Any],
    turns: list[Mapping[str, Any]],
) -> dict[str, Any]:
    blockers = session_blockers(session_id=session_id, turns=turns)
    if blockers:
        return memory_record_blocked_session(session_id, blockers)

    state = MemoryRecordSessionState()
    for turn_spec in turns:
        state.run_turn(
            artifact_root=artifact_root,
            session_id=session_id,
            fixture_inputs=fixture_inputs,
            turn_spec=turn_spec,
        )
    artifact = state.artifact(session_id)
    session_path = write_session_record(
        artifact_root=artifact_root,
        session_id=session_id,
        artifact=artifact,
    )
    artifact["session_artifact_path"] = str(session_path)
    write_session_record(
        artifact_root=artifact_root,
        session_id=session_id,
        artifact=artifact,
    )
    return artifact


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_advanced_product_lab_memory_record_session"]
