from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_session_action_summary import (
    session_chat_action_summary,
    turn_chat_action_summary,
)
from app.advanced_shadow_lab.product_lab_session_controls import event_ids
from app.advanced_shadow_lab.product_lab_session_product_summary import (
    session_product_summary,
    turn_product_summary,
)


NON_CLAIMS = [
    "not_production_database",
    "not_mainline_runtime_activation",
    "not_scheduler_delivery",
    "not_durable_product_memory",
    "not_canonical_mutation",
]


def session_artifact(
    *,
    session_id: str,
    blockers: list[str],
    turn_summaries: list[dict[str, Any]],
    turn_paths: list[str],
    journal: list[Mapping[str, Any]],
    history_event_ids: list[str],
    memory_record_ids: list[str] | None = None,
    memory_tool_calls: list[Mapping[str, Any]] | None = None,
    memory_surface_paths: Mapping[str, str] | None = None,
    memory_context_injected: bool = False,
) -> dict[str, Any]:
    has_memory = bool(memory_record_ids)
    return {
        "artifact_type": "advanced_product_lab_dogfood_session_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab/product_lab_session_replay.py",
        "consumer": "advanced_product_lab_live_and_e2e_diagnostics",
        "retirement_trigger": "approved_advanced_product_lab_promotion_plan",
        "session_id": session_id,
        "turn_count": len(turn_summaries),
        "turn_summaries": turn_summaries,
        "turn_artifact_paths": list(turn_paths),
        **session_product_summary(turn_summaries),
        "control_event_history_ids": list(history_event_ids),
        "final_control_journal_event_ids": event_ids(journal),
        **session_chat_action_summary(turn_summaries),
        "lab_session_store_written": not blockers,
        "lab_memory_store_written": not blockers and has_memory,
        "lab_memory_record_ids": list(memory_record_ids or []),
        "lab_memory_tool_calls": [dict(call) for call in memory_tool_calls or []],
        "lab_memory_surface_paths": dict(memory_surface_paths or {}),
        "lab_memory_context_injected": bool(memory_context_injected),
        "memory_context_injected": bool(memory_context_injected),
        "memory_tools_enabled": True,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "lab_user_facing_behavior_changed": not blockers,
        "blockers": blockers,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def blocked_session(*, session_id: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_dogfood_session_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked",
        "session_id": session_id,
        "turn_count": 0,
        "turn_summaries": [],
        "turn_artifact_paths": [],
        "control_event_history_ids": [],
        "final_control_journal_event_ids": [],
        "session_artifact_path": "",
        "lab_session_store_written": False,
        "lab_memory_store_written": False,
        "lab_memory_record_ids": [],
        "lab_memory_tool_calls": [],
        "lab_memory_surface_paths": {},
        "lab_memory_context_injected": False,
        "memory_context_injected": False,
        "memory_tools_enabled": False,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "lab_user_facing_behavior_changed": False,
        "blockers": blockers,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def turn_record(
    turn_artifact: Mapping[str, Any],
    post_control: Mapping[str, Any],
    *,
    chat_action_outcomes: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_dogfood_turn_record",
        "turn_artifact": dict(turn_artifact),
        "post_turn_control_state": dict(post_control),
        "post_turn_chat_action_outcomes": [
            dict(item) for item in chat_action_outcomes or []
        ],
    }


def turn_summary(
    turn_id: str,
    turn_artifact: Mapping[str, Any],
    post_control: Mapping[str, Any],
    *,
    memory_context_pack: Mapping[str, Any] | None = None,
    memory_write_artifact: Mapping[str, Any] | None = None,
    chat_action_outcomes: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    context_pack = memory_context_pack or {}
    memory_write = memory_write_artifact or {}
    action_outcomes = list(chat_action_outcomes or [])
    return {
        "turn_id": turn_id,
        "status": str(turn_artifact.get("status") or "blocked"),
        "visible_candidate_ids": [
            str(message.get("candidate_id") or "")
            for message in messages(turn_artifact)
        ],
        "post_turn_control_event_ids": event_ids(
            post_control.get("journal_entries") or []
        ),
        "memory_context_injected": context_pack.get("memory_context_injected") is True,
        "lab_memory_selected_record_ids": list(
            context_pack.get("selected_record_ids") or []
        ),
        "lab_memory_written_record_ids": list(
            memory_write.get("written_record_ids") or []
        ),
        **turn_chat_action_summary(action_outcomes),
        **turn_product_summary(turn_artifact),
    }


def turn_blockers(
    turn_id: str,
    turn_artifact: Mapping[str, Any],
    post_control: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if turn_artifact.get("status") != "pass":
        blockers.append(f"{turn_id}.turn_status_blocked")
    if post_control.get("status") != "pass":
        blockers.append(f"{turn_id}.post_turn_control_status_blocked")
    return blockers


def messages(turn_artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    surface = turn_artifact.get("lab_chat_surface")
    if not isinstance(surface, Mapping):
        return []
    return [item for item in surface.get("messages") or [] if isinstance(item, Mapping)]


__all__ = [
    "blocked_session",
    "session_artifact",
    "turn_blockers",
    "turn_record",
    "turn_summary",
]
