from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_record_runtime import (
    run_advanced_product_lab_turn_with_memory_records,
)
from app.advanced_shadow_lab.product_lab_memory_record_session_artifact import (
    memory_record_session_artifact,
    public_write,
)
from app.advanced_shadow_lab.product_lab_memory_record_session_support import (
    memory_context_pack,
    memory_write,
    tool_call,
)
from app.advanced_shadow_lab.product_lab_session_action_state import (
    initial_session_action_state,
    post_turn_chat_actions_and_state,
)
from app.advanced_shadow_lab.product_lab_session_controls import (
    post_turn_control_state_and_event_ids,
    release_completed_controls,
)
from app.advanced_shadow_lab.product_lab_session_policy import LAB_MODE, turn_input
from app.advanced_shadow_lab.product_lab_session_records import (
    turn_blockers,
    turn_record,
    turn_summary,
)
from app.advanced_shadow_lab.product_lab_session_store import write_turn_record


class MemoryRecordSessionState:
    def __init__(self) -> None:
        self.memory_records: list[dict[str, Any]] = []
        self.journal: list[Mapping[str, Any]] = []
        self.action_state = initial_session_action_state()
        self.history_event_ids: list[str] = []
        self.turn_summaries: list[dict[str, Any]] = []
        self.turn_paths: list[str] = []
        self.memory_tool_calls: list[dict[str, Any]] = []
        self.memory_context_used = False
        self.run_blockers: list[str] = []
        self.write_artifacts: list[dict[str, Any]] = []

    def run_turn(
        self,
        *,
        artifact_root: Path | str,
        session_id: str,
        fixture_inputs: Mapping[str, Any],
        turn_spec: Mapping[str, Any],
    ) -> None:
        turn_id = str(turn_spec.get("turn_id") or "")
        context_pack = memory_context_pack(session_id, turn_id, self.memory_records)
        self.memory_tool_calls.append(tool_call(turn_id, context_pack))
        self.memory_context_used = self.memory_context_used or bool(
            context_pack["selected_record_ids"]
        )
        turn_artifact = run_advanced_product_lab_turn_with_memory_records(
            lab_mode=LAB_MODE,
            turn=turn_input(session_id=session_id, turn_spec=turn_spec),
            fixture_inputs=fixture_inputs,
            shadow_memory_context_pack=context_pack,
            enable_lab_memory_record_bridge=True,
            prior_control_journal=self.journal,
            prior_action_state=self.action_state,
        )
        self._finish_turn(artifact_root, session_id, turn_id, turn_spec, context_pack, turn_artifact)

    def _finish_turn(
        self,
        artifact_root: Path | str,
        session_id: str,
        turn_id: str,
        turn_spec: Mapping[str, Any],
        context_pack: Mapping[str, Any],
        turn_artifact: Mapping[str, Any],
    ) -> None:
        released = release_completed_controls(self.journal, turn_artifact)
        post_control, event_ids = post_turn_control_state_and_event_ids(
            session_id=session_id,
            turn_id=turn_id,
            turn_spec=turn_spec,
            turn_artifact=turn_artifact,
            prior_journal=released,
        )
        outcomes, self.action_state, delta, chat_blockers = post_turn_chat_actions_and_state(
            turn_spec=turn_spec,
            turn_artifact=turn_artifact,
            prior_state=self.action_state,
        )
        write_artifact = memory_write(turn_spec, session_id=session_id)
        self.memory_records.extend(write_artifact["records"])
        self.write_artifacts.append(write_artifact)
        self.journal = list(post_control["journal_entries"])
        self.history_event_ids.extend(event_ids)
        self.run_blockers.extend(turn_blockers(turn_id, turn_artifact, post_control))
        self.run_blockers.extend(f"{turn_id}.chat_action.{item}" for item in chat_blockers)
        if write_artifact["status"] != "pass":
            self.run_blockers.append(f"{turn_id}.memory_record_write_blocked")
        self._record_turn(
            artifact_root=artifact_root,
            session_id=session_id,
            turn_id=turn_id,
            context_pack=context_pack,
            turn_artifact=turn_artifact,
            post_control=post_control,
            outcomes=outcomes,
            delta=delta,
            write_artifact=write_artifact,
        )

    def _record_turn(
        self,
        *,
        artifact_root: Path | str,
        session_id: str,
        turn_id: str,
        context_pack: Mapping[str, Any],
        turn_artifact: Mapping[str, Any],
        post_control: Mapping[str, Any],
        outcomes: list[Mapping[str, Any]],
        delta: Mapping[str, Any],
        write_artifact: Mapping[str, Any],
    ) -> None:
        record = turn_record(
            turn_artifact,
            post_control,
            chat_action_outcomes=outcomes,
            action_state_delta=delta,
            action_state=self.action_state,
        )
        record["memory_record_context_pack"] = context_pack
        record["memory_record_write_artifact"] = public_write(write_artifact)
        path = write_turn_record(
            artifact_root=artifact_root,
            session_id=session_id,
            turn_id=turn_id,
            record=record,
        )
        self.turn_paths.append(str(path))
        self.turn_summaries.append(
            turn_summary(
                turn_id,
                turn_artifact,
                post_control,
                memory_context_pack=turn_artifact["lab_memory_context_pack"],
                memory_write_artifact=public_write(write_artifact),
                chat_action_outcomes=outcomes,
                action_state_delta=delta,
            )
        )

    def artifact(self, session_id: str) -> dict[str, Any]:
        return memory_record_session_artifact(
            session_id=session_id,
            blockers=self.run_blockers,
            turn_summaries=self.turn_summaries,
            turn_paths=self.turn_paths,
            journal=self.journal,
            history_event_ids=self.history_event_ids,
            memory_records=self.memory_records,
            memory_tool_calls=self.memory_tool_calls,
            memory_context_used=self.memory_context_used,
            action_state=self.action_state,
            write_artifacts=self.write_artifacts,
        )


__all__ = ["MemoryRecordSessionState"]
