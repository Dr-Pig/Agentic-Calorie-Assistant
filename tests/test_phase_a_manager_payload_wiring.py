from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.intake.application.context_injection_policy import build_manager_context_pack
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.runtime.application.manager_service import run_intake_manager


def _resolved_state() -> object:
    return SimpleNamespace(
        onboarding_ready=True,
        user_id=1,
        user_external_id="user-1",
        local_date="2026-04-29",
        active_body_plan_view=None,
        current_budget_view=None,
        conversation_state=None,
        injected_context={
            "ACTIVE_MEAL": {
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_title": "milk tea",
            },
            "PENDING_FOLLOWUP": {
                "is_open": True,
                "meal_id": 10,
                "meal_thread_id": 77,
                "pending_question": "What size was it?",
            },
            "RECENT_COMMITTED_MEALS_SUMMARY": [
                {
                    "meal_thread_id": 77,
                    "meal_version_id": 88,
                    "meal_title": "milk tea",
                }
            ],
            "TARGET_MEAL_REFERENCE": {
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_title": "milk tea",
                "target_resolution_source": "pending_followup_state",
                "correction_confidence": "high",
            },
            "SESSION_SUMMARY": {
                "latest_assistant_turns": ["What size was it?"],
            },
        },
    )


class _FakeProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def readiness(self) -> dict[str, object]:
        return {"configured": True}

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        return (
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "no_commit",
                "workflow_effect": "safe_failure",
                "target_attachment": {"mode": "new_meal"},
                "exactness": "anchored",
                "confidence": "medium",
                "evidence_posture": "generic_with_uncertainty",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "generic_with_uncertainty",
            },
            {"source": "fake"},
        )


class _CommitProvider(_FakeProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        return (
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "commit",
                "workflow_effect": "commit",
                "target_attachment": {"mode": "target_committed_thread", "target_object_id": "77"},
                "exactness": "anchored",
                "confidence": "medium",
                "evidence_posture": "generic_with_uncertainty",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "generic_with_uncertainty",
            },
            {"source": "fake"},
        )


@pytest.mark.asyncio
async def test_run_intake_manager_sends_structured_phase_a_payload_to_provider() -> None:
    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=resolved_state,
    )
    manager_context_pack = build_manager_context_pack(current_turn_context=current_turn_context)
    provider = _FakeProvider()

    result = await run_intake_manager(
        provider=provider,
        raw_user_input="half sugar",
        resolved_state=resolved_state,
        current_turn_context=current_turn_context,
        manager_context_pack=manager_context_pack,
        available_tools=("read_day_budget",),
    )

    payload = provider.calls[0]["user_payload"]
    assert isinstance(payload, dict)
    assert payload["phase_a_current_turn_context"]["current_interaction_event"]["surface_mode"] == "chat_freeform"
    assert set(payload["phase_a_manager_context_pack"].keys()) == {
        "policy",
        "manager_context",
        "available_if_needed",
    }
    assert payload["phase_a_manager_context_pack"]["manager_context"]["pending_followup"]["meal_thread_id"] == 77
    assert payload["phase_a_manager_context_pack"]["policy"]["must_inject"] == [
        "interaction_event",
        "active_meal_thread_ref",
        "pending_followup",
        "candidate_attachment_targets",
    ]
    assert "recent_committed_meal_refs" not in payload["phase_a_manager_context_pack"]["manager_context"]
    assert payload["phase_a_manager_context_pack"]["available_if_needed"]["recent_committed_meal_refs"][0]["meal_thread_id"] == 77
    assert payload["phase_a_surface_mode"] == "chat_freeform"
    assert payload["phase_a_history_expansion_enabled"] is False
    assert payload["phase_a_manager_context_pack_role"] == "primary_structured_context"
    assert payload["resolved_state_role"] == "compatibility_legacy"
    assert result.trace["manager_rounds"][0]["phase_a_input"]["phase_a_manager_context_pack_role"] == "primary_structured_context"
    assert result.trace["manager_rounds"][0]["phase_a_input"]["resolved_state_role"] == "compatibility_legacy"


@pytest.mark.asyncio
async def test_run_intake_manager_sends_shadow_hypothesis_to_provider_payload() -> None:
    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="that milk tea half sugar",
        resolved_state=resolved_state,
    )
    manager_context_pack = build_manager_context_pack(current_turn_context=current_turn_context)
    provider = _FakeProvider()
    shadow_payload = {
        "role": "tentative_non_authoritative",
        "hypothesis_id": "shadow-77",
        "candidate_target_object_type": "meal_thread",
        "candidate_target_object_id": "77",
        "candidate_intent": "back_reference",
        "confidence": "medium",
        "visibility_posture": "uncertainty_visible",
        "mutation_authority": False,
    }

    result = await run_intake_manager(
        provider=provider,
        raw_user_input="that milk tea half sugar",
        resolved_state=resolved_state,
        current_turn_context=current_turn_context,
        manager_context_pack=manager_context_pack,
        phase_a_shadow_hypothesis=shadow_payload,
        available_tools=("read_day_budget",),
    )

    payload = provider.calls[0]["user_payload"]
    assert isinstance(payload, dict)
    assert payload["phase_a_shadow_hypothesis"]["role"] == "tentative_non_authoritative"
    assert payload["phase_a_shadow_hypothesis"]["mutation_authority"] is False
    assert payload["phase_a_shadow_hypothesis"]["candidate_target_object_id"] == "77"
    assert "target_object_id" not in payload["phase_a_shadow_hypothesis"]
    assert payload["phase_a_shadow_hypothesis_instruction"] == {
        "not_confirmation": True,
        "must_not_authorize_mutation": True,
        "must_not_upgrade_final_action": True,
        "must_not_upgrade_attachment_or_guard": True,
    }
    assert (
        result.trace["manager_rounds"][0]["phase_a_input"]["phase_a_shadow_hypothesis_role"]
        == "tentative_non_authoritative"
    )


@pytest.mark.asyncio
async def test_shadow_payload_does_not_bypass_existing_manager_guard() -> None:
    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="that milk tea half sugar",
        resolved_state=resolved_state,
    )
    provider = _CommitProvider()
    shadow_payload = {
        "role": "tentative_non_authoritative",
        "hypothesis_id": "shadow-77",
        "candidate_target_object_type": "meal_thread",
        "candidate_target_object_id": "77",
        "candidate_intent": "back_reference",
        "confidence": "medium",
        "visibility_posture": "uncertainty_visible",
        "mutation_authority": False,
    }

    async def _guard_checker(**_: object) -> dict[str, object]:
        return {
            "ok": False,
            "repair_request": False,
            "failure_family": "phase_a_transition_guard_blocked",
            "phase_a_transition_guard_preflight": {
                "checked": True,
                "blocked": True,
                "transition_guard_verdict": "answer_only",
                "blocked_mutation": True,
            },
        }

    result = await run_intake_manager(
        provider=provider,
        raw_user_input="that milk tea half sugar",
        resolved_state=resolved_state,
        current_turn_context=current_turn_context,
        manager_context_pack=build_manager_context_pack(current_turn_context=current_turn_context),
        phase_a_shadow_hypothesis=shadow_payload,
        guard_checker=_guard_checker,
        available_tools=("read_day_budget",),
    )

    assert result.final_action == "no_commit"
    assert result.request_failure_family == "phase_a_transition_guard_blocked"
    assert (
        result.guard_outcome["phase_a_transition_guard_preflight"]["repair_result"]
        == "not_attempted"
    )


@pytest.mark.asyncio
async def test_execute_intake_turn_passes_current_turn_context_to_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.composition import intake_turn_orchestrator as module

    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="what's left today?",
        resolved_state=resolved_state,
    )
    captured: dict[str, object] = {}

    async def _fake_run_intake_manager(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(
            intent_type="answer_remaining_budget",
            workflow_effect="none",
            response_summary="budget",
            pending_followup=None,
            tool_calls=(),
            llm_used=False,
            trace={},
        )

    monkeypatch.setattr(module, "run_intake_manager", _fake_run_intake_manager)
    monkeypatch.setattr(
        module,
        "build_remaining_budget_answer_contract",
        lambda *_, **__: SimpleNamespace(
            status="ready",
            daily_target_kcal=1800,
            consumed_kcal=600,
            remaining_kcal=1200,
            meal_count=1,
        ),
    )
    monkeypatch.setattr(module, "render_intake_reply", lambda **_: "ok")
    monkeypatch.setattr(module, "build_deterministic_sidecar", lambda **_: {})
    monkeypatch.setattr(module, "write_intake_turn_trace_artifact", lambda **_: None)
    monkeypatch.setattr(module, "build_trace_refs", lambda **_: {})
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)

    result = await module.execute_intake_turn(
        None,
        user_external_id="user-1",
        raw_user_input="what's left today?",
        onboarding_payload=None,
        local_date="2026-04-29",
        allow_search=False,
        provider=object(),
        state_before=resolved_state,
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    assert captured["current_turn_context"] == current_turn_context
    assert captured["manager_context_pack"] is not None
    assert result["assistant_message"] == "ok"


@pytest.mark.asyncio
async def test_process_intake_execution_turn_passes_current_turn_context_to_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.composition import intake_execution_orchestrator as module

    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=resolved_state,
    )
    captured: dict[str, object] = {}

    async def _fake_run_intake_manager(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(
            final_action="no_commit",
            workflow_effect="safe_failure",
            request_failure_family=None,
            manager_rounds=(),
            tool_results=(),
        )

    monkeypatch.setattr(module, "run_intake_manager", _fake_run_intake_manager)
    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "apply_final_action_to_payload", lambda **_: None)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", lambda *_, **__: None)
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(module, "build_intake_execution_response", lambda *_, **kwargs: {"captured_phase_a_trace": kwargs["phase_a_trace"]})

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="half sugar",
        local_date="2026-04-29",
        allow_search=False,
        provider=object(),
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal"),
        request_id="req-1",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    assert captured["current_turn_context"] == current_turn_context
    assert captured["manager_context_pack"] is not None
    assert result["captured_phase_a_trace"]["phase_a_commit_boundary_preflight"]["bypassed"] is True
    assert (
        result["captured_phase_a_trace"]["phase_a_commit_boundary_preflight"]["bypass_reason"]
        == "non_persistence_effect"
    )


@pytest.mark.asyncio
async def test_process_intake_execution_turn_skips_shadow_when_back_reference_resolves_before_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    resolved_state = SimpleNamespace(
        onboarding_ready=True,
        user_id=1,
        user_external_id="user-1",
        local_date="2026-04-29",
        active_body_plan_view=None,
        current_budget_view=None,
        conversation_state=None,
        injected_context={
            "ACTIVE_MEAL": None,
            "PENDING_FOLLOWUP": {
                "is_open": False,
                "meal_id": None,
                "meal_thread_id": None,
                "pending_question": None,
            },
            "RECENT_COMMITTED_MEALS_SUMMARY": [
                {
                    "meal_thread_id": 77,
                    "meal_version_id": 88,
                    "meal_title": "milk tea",
                    "local_date": "2026-04-29",
                }
            ],
            "TARGET_MEAL_REFERENCE": {
                "meal_thread_id": None,
                "meal_version_id": None,
                "meal_title": None,
                "target_resolution_source": "none",
                "correction_confidence": "low",
            },
            "SESSION_SUMMARY": {},
        },
    )
    captured: dict[str, object] = {}

    async def _fake_run_intake_manager(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(
            final_action="no_commit",
            workflow_effect="safe_failure",
            request_failure_family=None,
            manager_rounds=(),
            tool_results=(),
        )

    monkeypatch.setattr(module, "run_intake_manager", _fake_run_intake_manager)
    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "apply_final_action_to_payload", lambda **_: None)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", lambda *_, **__: None)
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(module, "build_intake_execution_response", lambda *_, **kwargs: {"captured_phase_a_trace": kwargs["phase_a_trace"]})

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="that milk tea half sugar",
        local_date="2026-04-29",
        allow_search=False,
        provider=object(),
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal"),
        request_id="req-1",
        stage_timings=[],
        current_turn_context=None,
        phase_a_trace=None,
    )

    assert captured["phase_a_shadow_hypothesis"] is None
    trace = result["captured_phase_a_trace"]["shadow_hypothesis_runtime"]
    assert trace["created"] is False
    assert trace["skip_reason"] == "already_safe_pass"
    assert trace["candidate_target_object_id"] is None


@pytest.mark.asyncio
async def test_execute_intake_turn_does_not_pre_manager_enrich_history_without_manager_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_turn_orchestrator as module

    resolved_state = SimpleNamespace(
        onboarding_ready=True,
        user_id=1,
        user_external_id="user-1",
        local_date="2026-04-29",
        active_body_plan_view=None,
        current_budget_view=None,
        conversation_state=SimpleNamespace(
            retrieved_meal_records=[
                {
                    "chunk_id": "meal:501",
                    "source_type": "meal_record",
                    "source_id": 501,
                    "content": "milk tea bubble tea half sugar",
                    "timestamp": "2026-04-29T09:00:00Z",
                    "linked_meal_id": 501,
                    "score": 10.0,
                    "matched_terms": ["milk", "tea"],
                    "metadata": {
                        "title": "milk tea",
                        "meal_thread_id": 77,
                        "meal_version_id": 88,
                        "local_date": "2026-04-29",
                        "relative_time_label": "today",
                    },
                }
            ],
            historical_meal_chunks=[],
            transcript_chunks=[],
        ),
        injected_context={
            "ACTIVE_MEAL": None,
            "PENDING_FOLLOWUP": {
                "is_open": False,
                "meal_id": None,
                "meal_thread_id": None,
                "pending_question": None,
            },
            "RECENT_COMMITTED_MEALS_SUMMARY": [],
            "TARGET_MEAL_REFERENCE": {
                "meal_thread_id": None,
                "meal_version_id": None,
                "meal_title": None,
                "target_resolution_source": "none",
                "correction_confidence": "low",
            },
            "SESSION_SUMMARY": {},
        },
    )
    captured: dict[str, object] = {}

    async def _fake_run_intake_manager(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(
            intent_type="answer_remaining_budget",
            workflow_effect="none",
            response_summary="budget",
            pending_followup=None,
            tool_calls=(),
            llm_used=False,
            trace={},
        )

    monkeypatch.setattr(module, "run_intake_manager", _fake_run_intake_manager)
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(
        module,
        "build_remaining_budget_answer_contract",
        lambda *_, **__: SimpleNamespace(
            status="ready",
            daily_target_kcal=1800,
            consumed_kcal=600,
            remaining_kcal=1200,
            meal_count=1,
        ),
    )
    monkeypatch.setattr(module, "render_intake_reply", lambda **_: "ok")
    monkeypatch.setattr(module, "build_deterministic_sidecar", lambda **_: {})
    monkeypatch.setattr(module, "write_intake_turn_trace_artifact", lambda **_: None)
    monkeypatch.setattr(module, "build_trace_refs", lambda **_: {})

    result = await module.execute_intake_turn(
        None,
        user_external_id="user-1",
        raw_user_input="actually change that milk tea to half sugar",
        onboarding_payload=None,
        local_date="2026-04-29",
        allow_search=False,
        provider=object(),
        state_before=resolved_state,
        current_turn_context=None,
        phase_a_trace=None,
    )

    current_turn_context = captured["current_turn_context"]
    assert current_turn_context is not None
    assert current_turn_context.candidate_attachment_targets == []
    manager_context_pack = captured["manager_context_pack"]
    assert manager_context_pack is not None
    assert manager_context_pack.manager_context["candidate_attachment_targets"] == []
    assert captured["history_expansion_policy"] is not None
    assert result["assistant_message"] == "ok"
