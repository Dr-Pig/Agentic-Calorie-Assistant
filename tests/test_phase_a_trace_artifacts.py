from __future__ import annotations

from pathlib import Path

import app.runtime.application.request_trace_artifacts as trace_artifacts


def _capture_writer(monkeypatch, tmp_path: Path) -> dict[str, object]:
    captured: dict[str, object] = {}

    def _fake_write(request_id: str, payload: dict[str, object]) -> Path:
        captured["request_id"] = request_id
        captured["payload"] = payload
        return tmp_path / f"{request_id}.json"

    monkeypatch.setattr(trace_artifacts, "write_request_trace_artifact", _fake_write)
    return captured


def test_write_intake_turn_trace_artifact_includes_phase_a_trace(monkeypatch, tmp_path: Path) -> None:
    captured = _capture_writer(monkeypatch, tmp_path)
    phase_a_trace = {
        "current_turn_context": {"user_utterance": "I ate oatmeal"},
        "interaction_event": {"source": "chat"},
        "attachment_decision": {"disposition": "create_new_workflow"},
        "transition_guard_result": {"verdict": "pass"},
    }

    trace_artifacts.write_intake_turn_trace_artifact(
        request_id="intake_turn-phase-a",
        user_external_id="user-1",
        local_date="2026-04-29",
        raw_user_input="I ate oatmeal",
        onboarding_payload=None,
        allow_search=False,
        state_before={},
        manager_decision={},
        onboarding_result=None,
        nutrition_artifact=None,
        persistence_result=None,
        remaining_budget=None,
        state_after={},
        assistant_message="ok",
        sidecar={},
        state_delta={},
        phase_a_trace=phase_a_trace,
        latency_tracking={},
    )

    assert captured["request_id"] == "intake_turn-phase-a"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["phase_a_trace"] == phase_a_trace


def test_write_intake_execution_trace_artifact_includes_phase_a_trace(monkeypatch, tmp_path: Path) -> None:
    captured = _capture_writer(monkeypatch, tmp_path)
    phase_a_trace = {
        "current_turn_context": {"user_utterance": "half bowl of rice"},
        "interaction_event": {"source": "chat"},
        "attachment_decision": {"disposition": "attach_existing_thread"},
        "transition_guard_result": {"verdict": "pass"},
    }

    trace_artifacts.write_intake_execution_trace_artifact(
        request_id="intake_execution-phase-a",
        user_external_id="user-2",
        local_date="2026-04-29",
        raw_user_input="half bowl of rice",
        allow_search=False,
        state_before={},
        manager_round_1={},
        injected_context_summary={},
        tool_plan=[],
        tool_outputs={},
        manager_final_decision={},
        state_after={},
        assistant_message="ok",
        sidecar={},
        state_delta={},
        phase_a_trace=phase_a_trace,
        latency_tracking={},
    )

    assert captured["request_id"] == "intake_execution-phase-a"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["phase_a_trace"] == phase_a_trace


def test_write_intake_execution_trace_artifact_includes_separate_phase_c_trace(monkeypatch, tmp_path: Path) -> None:
    captured = _capture_writer(monkeypatch, tmp_path)
    phase_c_trace = {
        "mutation_outcome": {"canonical_commit_status": "committed"},
        "same_truth_read_result": {"owner_alignment": "aligned"},
    }

    trace_artifacts.write_intake_execution_trace_artifact(
        request_id="intake_execution-phase-c",
        user_external_id="user-2",
        local_date="2026-04-29",
        raw_user_input="half bowl of rice",
        allow_search=False,
        state_before={},
        manager_round_1={},
        injected_context_summary={},
        tool_plan=[],
        tool_outputs={},
        manager_final_decision={},
        state_after={},
        assistant_message="ok",
        sidecar={},
        state_delta={},
        phase_a_trace={},
        phase_c_trace=phase_c_trace,
        latency_tracking={},
    )

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["phase_a_trace"] == {}
    assert payload["phase_c_trace"] == phase_c_trace


def test_write_intake_execution_trace_artifact_includes_react_trace(monkeypatch, tmp_path: Path) -> None:
    captured = _capture_writer(monkeypatch, tmp_path)
    react_trace = {
        "trace_schema_version": "manager_react_trace.v1",
        "manager_pass_1": {"manager_action": "call_tools"},
        "requested_tools": ["budget.get_today_summary"],
        "executed_tools": ["budget.get_today_summary"],
        "manager_pass_final": {"manager_action": "final", "final_action": "answer_only"},
        "guard_result": {},
        "request_failure_family": None,
    }

    trace_artifacts.write_intake_execution_trace_artifact(
        request_id="intake_execution-react-trace",
        user_external_id="user-2",
        local_date="2026-04-29",
        raw_user_input="how many calories left",
        allow_search=False,
        state_before={},
        manager_round_1={},
        injected_context_summary={},
        tool_plan=[],
        tool_outputs={},
        manager_final_decision={},
        state_after={},
        assistant_message="ok",
        sidecar={},
        state_delta={},
        phase_a_trace={},
        phase_c_trace={},
        react_trace=react_trace,
        latency_tracking={},
    )

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["react_trace"] == react_trace


def test_write_intake_turn_trace_artifact_preserves_history_expansion_activation(monkeypatch, tmp_path: Path) -> None:
    captured = _capture_writer(monkeypatch, tmp_path)
    phase_a_trace = {
        "current_turn_context": {"user_utterance": "actually change that milk tea to half sugar"},
        "interaction_event": {"source": "chat"},
        "attachment_decision": {"disposition": "target_committed_thread"},
        "transition_guard_result": {"verdict": "pass"},
        "history_expansion_activation": {
            "triggered": True,
            "reason": "correction_reference",
            "scope": "recent_meals",
            "resolution_gain": True,
            "selected_candidate_ids": ["77"],
        },
    }

    trace_artifacts.write_intake_turn_trace_artifact(
        request_id="intake_turn-history-phase-a",
        user_external_id="user-1",
        local_date="2026-04-29",
        raw_user_input="actually change that milk tea to half sugar",
        onboarding_payload=None,
        allow_search=False,
        state_before={},
        manager_decision={},
        onboarding_result=None,
        nutrition_artifact=None,
        persistence_result=None,
        remaining_budget=None,
        state_after={},
        assistant_message="ok",
        sidecar={},
        state_delta={},
        phase_a_trace=phase_a_trace,
        latency_tracking={},
    )

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["phase_a_trace"]["history_expansion_activation"]["triggered"] is True
    assert payload["phase_a_trace"]["history_expansion_activation"]["selected_candidate_ids"] == ["77"]


def test_write_general_chat_request_trace_artifact_includes_phase_a_boundary_projection(
    monkeypatch, tmp_path: Path
) -> None:
    captured = _capture_writer(monkeypatch, tmp_path)
    phase_a_trace = {
        "current_turn_context": {"user_utterance": "how many calories can I still eat?"},
        "interaction_event": {"source": "chat"},
        "attachment_decision": {"disposition": "answer_only"},
        "transition_guard_result": {"verdict": "answer_only"},
        "boundary_projection": {
            "fallback_honesty_decision": {"budget_answer_mode": "degraded"},
        },
    }

    trace_artifacts.write_general_chat_request_trace_artifact(
        request_id="general-chat-phase-a",
        user_external_id="user-3",
        local_date="2026-04-29",
        raw_user_input="how many calories can I still eat?",
        state_before={},
        general_chat_result={"workflow_effect": "answer_budget_summary_without_state_mutation"},
        assistant_message="please finish onboarding first",
        phase_a_trace=phase_a_trace,
    )

    assert captured["request_id"] == "general-chat-phase-a"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["phase_a_trace"]["boundary_projection"]["fallback_honesty_decision"]["budget_answer_mode"] == (
        "degraded"
    )


def test_write_intake_execution_trace_artifact_bounds_large_sections(monkeypatch, tmp_path: Path) -> None:
    captured = _capture_writer(monkeypatch, tmp_path)
    tool_outputs = {
        "long_text": "x" * 1205,
        "items": [{"index": idx} for idx in range(30)],
    }

    trace_artifacts.write_intake_execution_trace_artifact(
        request_id="intake_execution-bounded-trace",
        user_external_id="user-4",
        local_date="2026-04-29",
        raw_user_input="hello",
        allow_search=False,
        state_before={},
        manager_round_1={},
        injected_context_summary={},
        tool_plan=[],
        tool_outputs=tool_outputs,
        manager_final_decision={},
        state_after={},
        assistant_message="ok",
        sidecar={},
        state_delta={},
        phase_a_trace={},
        phase_c_trace={},
        latency_tracking={},
    )

    payload = captured["payload"]
    assert isinstance(payload, dict)
    bounded_outputs = payload["tool_outputs"]
    assert bounded_outputs["long_text"].endswith("...[truncated]")
    assert bounded_outputs["items"][-1] == {"_truncated_item_count": 6}
