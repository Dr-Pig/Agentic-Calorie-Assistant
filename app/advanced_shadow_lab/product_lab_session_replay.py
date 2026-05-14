from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory import (
    ProductLabMemoryStore,
    build_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab import product_lab_rescue_proposal_read_model as rm
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.advanced_shadow_lab.product_lab_session_controls import (
    post_turn_control_state_and_event_ids,
    release_completed_controls,
)
from app.advanced_shadow_lab.product_lab_session_memory_pipeline import (
    run_product_lab_turn_memory_pipeline,
)
from app.advanced_shadow_lab.product_lab_proactive_control_store import ProductLabProactiveControlStore
from app.advanced_shadow_lab.product_lab_session_manager_loop import turn_manager_script
from app.advanced_shadow_lab.product_lab_session_action_state import (
    initial_session_action_state,
    post_turn_chat_actions_and_state,
)
from app.advanced_shadow_lab.product_lab_session_policy import (
    LAB_MODE,
    lab_now_minute,
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
    write_final_session_record,
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
    control_store = ProductLabProactiveControlStore(artifact_root)
    journal: list[Mapping[str, Any]] = control_store.read_journal(session_id=session_id)
    history_event_ids: list[str] = []
    memory_record_ids: list[str] = []
    memory_tool_calls: list[dict[str, Any]] = []
    memory_surface_paths: dict[str, str] = {}
    memory_context_injected = False
    action_state = initial_session_action_state()
    rescue_proposal_read_model = rm.empty()
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
            lab_now_minute=lab_now_minute(turn_spec),
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
            prior_action_state=action_state,
        )
        released_journal = release_completed_controls(journal, turn_artifact)
        post_control, control_event_ids = post_turn_control_state_and_event_ids(
            session_id=session_id,
            turn_id=turn_id,
            turn_spec=turn_spec,
            turn_artifact=turn_artifact,
            prior_journal=released_journal,
        )
        history_event_ids.extend(control_event_ids)
        memory_pipeline = run_product_lab_turn_memory_pipeline(
            store=memory_store,
            session_id=session_id,
            turn_id=turn_id,
            turn_spec=turn_spec,
            turn_artifact=turn_artifact,
        )
        memory_write = dict(memory_pipeline.get("memory_write_artifact") or {})
        memory_record_ids = list(memory_write.get("all_record_ids") or memory_record_ids)
        if memory_write.get("surface_paths"):
            memory_surface_paths = {
                key: str(value)
                for key, value in dict(memory_write.get("surface_paths") or {}).items()
            }
        journal = list(post_control["journal_entries"])
        control_store_artifact = control_store.write_journal(session_id=session_id, journal_entries=journal)
        run_blockers.extend(turn_blockers(turn_id, turn_artifact, post_control))
        if memory_pipeline.get("status") != "pass":
            run_blockers.append(f"{turn_id}.memory_pipeline_blocked")
        (
            chat_action_outcomes,
            action_state,
            action_state_delta,
            chat_action_blockers,
        ) = post_turn_chat_actions_and_state(
            turn_spec=turn_spec,
            turn_artifact=turn_artifact,
            prior_state=action_state,
        )
        run_blockers.extend(
            f"{turn_id}.chat_action.{blocker}" for blocker in chat_action_blockers
        )
        rescue_proposal_read_model = rm.update(
            rescue_proposal_read_model, turn_id, turn_artifact, chat_action_outcomes
        )
        record = turn_record(
            turn_artifact,
            post_control,
            chat_action_outcomes=chat_action_outcomes,
            action_state_delta=action_state_delta,
            action_state=action_state,
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
                action_state_delta=action_state_delta,
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
        action_state=action_state,
        proactive_control_store_artifact=control_store_artifact if turns else None,
    )
    artifact = rm.attach(artifact, rescue_proposal_read_model)
    return write_final_session_record(
        artifact_root=artifact_root, session_id=session_id, artifact=artifact
    )


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "run_advanced_product_lab_dogfood_session",
]
