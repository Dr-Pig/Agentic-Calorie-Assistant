from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_session_records import (
    blocked_session,
    session_artifact,
)


def memory_record_session_artifact(
    *,
    session_id: str,
    blockers: list[str],
    turn_summaries: list[dict[str, Any]],
    turn_paths: list[str],
    journal: list[Mapping[str, Any]],
    history_event_ids: list[str],
    memory_records: list[Mapping[str, Any]],
    memory_tool_calls: list[Mapping[str, Any]],
    memory_context_used: bool,
    action_state: Mapping[str, Any],
    write_artifacts: list[Mapping[str, Any]],
) -> dict[str, Any]:
    artifact = session_artifact(
        session_id=session_id,
        blockers=blockers,
        turn_summaries=turn_summaries,
        turn_paths=turn_paths,
        journal=journal,
        history_event_ids=history_event_ids,
        memory_record_ids=[str(record["id"]) for record in memory_records],
        memory_tool_calls=memory_tool_calls,
        memory_context_injected=memory_context_used,
        action_state=action_state,
    )
    artifact.update(
        {
            "owner": "app/advanced_shadow_lab/product_lab_memory_record_session.py",
            "memory_record_session_replay_enabled": True,
            "memory_record_context_pack_used": memory_context_used,
            "memory_record_write_artifacts": [
                public_write(item) for item in write_artifacts
            ],
            "mainline_activation_enabled": False,
            "durable_product_memory_written": False,
            "canonical_product_mutation_allowed": False,
        }
    )
    return artifact


def memory_record_blocked_session(session_id: str, blockers: list[str]) -> dict[str, Any]:
    artifact = blocked_session(session_id=session_id, blockers=blockers)
    artifact["memory_record_session_replay_enabled"] = True
    artifact["memory_record_context_pack_used"] = False
    return artifact


def public_write(write: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in write.items() if key != "records"}


__all__ = [
    "memory_record_blocked_session",
    "memory_record_session_artifact",
    "public_write",
]
