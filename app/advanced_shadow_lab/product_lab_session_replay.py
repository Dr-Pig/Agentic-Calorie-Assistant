from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_chat_actions import (
    apply_product_lab_chat_actions,
)
from app.advanced_shadow_lab.product_lab_memory import (
    ProductLabMemoryStore,
    build_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.advanced_shadow_lab.product_lab_session_controls import (
    event_ids,
    post_turn_control_state,
    post_turn_events,
    release_completed_controls,
)
from app.advanced_shadow_lab.product_lab_session_memory_pipeline import (
    run_product_lab_turn_memory_pipeline,
)
from app.advanced_shadow_lab.product_lab_session_manager_loop import turn_manager_script
from app.advanced_shadow_lab.product_lab_session_policy import (
    LAB_MODE,
    session_blockers,
    turn_input,
)
from app.advanced_shadow_lab.product_lab_session_records import (
    blocked_session,
    session_artifact,
    turn_blockers,
    turn_record,
    turn_summary,
)
from app.advanced_shadow_lab.product_lab_session_store import (
    write_session_record,
    write_turn_record,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_session_replay"
)


def run_advanced_product_lab_dogfood_session(
    *,
    artifact_root: Path | str,
    session_id: str,
    fixture_inputs: Mapping[str, Any],
    turns: list[Mapping[str, Any]],
) -> dict[str, Any]:
    blockers = session_blockers(session_id=session_id, turns=turns)
    if blockers:
        return blocked_session(session_id=session_id, blockers=blockers)

    memory_store = ProductLabMemoryStore(artifact_root)
    journal: list[Mapping[str, Any]] = []
    history_event_ids: list[str] = []
    memory_record_ids: list[str] = []
    memory_tool_calls: list[dict[str, Any]] = []
    memory_surface_paths: dict[str, str] = {}
    memory_context_injected = False
    turn_summaries: list[dict[str, Any]] = []
    turn_paths: list[str] = []
    run_blockers: list[str] = []
    for turn_spec in turns:
        turn_id = str(turn_spec.get("turn_id") or "")
        memory_context_pack = build_product_lab_memory_context_pack(
            store=memory_store,
            session_id=session_id,
            turn_id=turn_id,
            consumers=["recommendation", "rescue", "proactive"],
            token_budget=180,
        )
        memory_tool_calls.extend(
            dict(call) for call in memory_context_pack.get("memory_tool_calls") or []
        )
        memory_context_injected = (
            memory_context_injected
            or memory_context_pack.get("memory_context_injected") is True
        )
        turn_artifact = run_advanced_product_lab_turn(
            lab_mode=LAB_MODE,
            turn=turn_input(session_id=session_id, turn_spec=turn_spec),
            fixture_inputs=fixture_inputs,
            lab_memory_context_pack=memory_context_pack,
            prior_control_journal=journal,
            manager_script=turn_manager_script(turn_spec),
            manager_tool_store=memory_store,
        )
        released_journal = release_completed_controls(journal, turn_artifact)
        post_control = post_turn_control_state(
            session_id=session_id,
            turn_id=turn_id,
            turn_spec=turn_spec,
            turn_artifact=turn_artifact,
            prior_journal=released_journal,
        )
        history_event_ids.extend(event_ids(post_turn_events(turn_spec)))
        memory_pipeline = run_product_lab_turn_memory_pipeline(
            store=memory_store,
            session_id=session_id,
            turn_id=turn_id,
            turn_spec=turn_spec,
        )
        memory_write = dict(memory_pipeline.get("memory_write_artifact") or {})
        memory_record_ids = list(memory_write.get("all_record_ids") or memory_record_ids)
        if memory_write.get("surface_paths"):
            memory_surface_paths = {
                key: str(value)
                for key, value in dict(memory_write.get("surface_paths") or {}).items()
            }
        journal = list(post_control["journal_entries"])
        run_blockers.extend(turn_blockers(turn_id, turn_artifact, post_control))
        if memory_pipeline.get("status") != "pass":
            run_blockers.append(f"{turn_id}.memory_pipeline_blocked")
        chat_action_outcomes = apply_product_lab_chat_actions(
            messages=_chat_messages(turn_artifact),
            action_specs=_post_turn_chat_actions(turn_spec),
        )
        run_blockers.extend(
            f"{turn_id}.chat_action.{blocker}"
            for outcome in chat_action_outcomes
            for blocker in outcome.get("blockers") or []
        )
        record = turn_record(
            turn_artifact,
            post_control,
            chat_action_outcomes=chat_action_outcomes,
        )
        record["memory_pipeline_artifact"] = memory_pipeline
        path = write_turn_record(
            artifact_root=artifact_root,
            session_id=session_id,
            turn_id=turn_id,
            record=record,
        )
        turn_paths.append(str(path))
        turn_summaries.append(
            turn_summary(
                turn_id,
                turn_artifact,
                post_control,
                memory_context_pack=memory_context_pack,
                memory_write_artifact=memory_write,
                chat_action_outcomes=chat_action_outcomes,
            )
        )

    artifact = session_artifact(
        session_id=session_id,
        blockers=run_blockers,
        turn_summaries=turn_summaries,
        turn_paths=turn_paths,
        journal=journal,
        history_event_ids=history_event_ids,
        memory_record_ids=memory_record_ids,
        memory_tool_calls=memory_tool_calls,
        memory_surface_paths=memory_surface_paths,
        memory_context_injected=memory_context_injected,
    )
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


def _post_turn_chat_actions(turn_spec: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        item
        for item in turn_spec.get("post_turn_chat_actions") or []
        if isinstance(item, Mapping)
    ]


def _chat_messages(turn_artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    surface = turn_artifact.get("lab_chat_surface")
    if not isinstance(surface, Mapping):
        return []
    return [
        item for item in surface.get("messages") or [] if isinstance(item, Mapping)
    ]


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "run_advanced_product_lab_dogfood_session",
]
