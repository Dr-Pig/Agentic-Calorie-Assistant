from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.intake.application.context_injection_policy import build_manager_context_pack
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.history_expansion_manager_runtime import (
    activate_manager_triggered_history_expansion,
    manager_history_expansion_eligibility,
)
from app.intake.application.attachment_resolver import resolve_attachment_decision
from app.intake.application.transition_guard import resolve_transition_guard
from app.runtime.application.manager_service import run_intake_manager
from app.runtime.contracts.phase_a import InteractionEvent


def test_manager_history_expansion_runtime_uses_public_shared_boundaries() -> None:
    source = Path("app/intake/application/history_expansion_manager_runtime.py").read_text(encoding="utf-8")

    assert "from .history_expansion_runtime import" not in source
    assert "_candidate_temporal_match" not in source
    assert "_candidate_lexical_match" not in source
    assert "_enrich_current_turn_context" not in source
    assert "manager_fallback_policy" not in source
    assert "looks_like_correction" not in source
    assert "looks_like_budget_query" not in source


def _meal_chunk(
    *,
    meal_thread_id: int = 77,
    meal_version_id: int = 88,
    title: str = "milk tea",
    content: str = "milk tea bubble tea half sugar",
    local_date: str = "2026-04-29",
) -> dict[str, object]:
    return {
        "chunk_id": f"meal:{meal_thread_id}",
        "source_type": "meal_record",
        "source_id": meal_thread_id,
        "content": content,
        "timestamp": f"{local_date}T09:00:00Z",
        "linked_meal_id": meal_thread_id,
        "score": 10.0,
        "matched_terms": ["milk", "tea"],
        "metadata": {
            "title": title,
            "meal_thread_id": meal_thread_id,
            "meal_version_id": meal_version_id,
            "local_date": local_date,
            "relative_time_label": "today",
        },
    }


def _resolved_state(
    *,
    retrieved_meal_records: list[dict[str, object]] | None = None,
    recent_meals: list[dict[str, object]] | None = None,
    pending_followup: bool = False,
) -> object:
    return SimpleNamespace(
        onboarding_ready=True,
        user_id=1,
        user_external_id="user-1",
        local_date="2026-04-29",
        active_body_plan_view=None,
        current_budget_view=None,
        conversation_state=SimpleNamespace(
            retrieved_meal_records=list(retrieved_meal_records or []),
            historical_meal_chunks=[],
            transcript_chunks=[
                {
                    "chunk_id": "transcript:1",
                    "content": "raw transcript should stay support-only",
                }
            ],
        ),
        injected_context={
            "ACTIVE_MEAL": None,
            "PENDING_FOLLOWUP": {
                "is_open": pending_followup,
                "meal_id": 10 if pending_followup else None,
                "meal_thread_id": 77 if pending_followup else None,
                "pending_question": "What size was it?" if pending_followup else None,
            },
            "RECENT_COMMITTED_MEALS_SUMMARY": list(recent_meals or []),
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


class _HistoryRequestProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def readiness(self) -> dict[str, object]:
        return {"configured": True}

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        payload = kwargs["user_payload"]
        assert isinstance(payload, dict)
        if len(self.calls) == 1:
            assert payload["phase_a_history_expansion_enabled"] is True
            assert "phase_a_expand_history" in payload["available_tools"]
            return (
                {
                    "manager_action": "call_tools",
                    "tool_calls": [
                        {
                            "name": "phase_a_expand_history",
                            "arguments": {"reason": "target_ambiguity", "scope": "recent_meals"},
                        }
                    ],
                },
                {"round": 1},
        )
        assert payload["phase_a_history_expansion_enabled"] is False
        tool_result = payload["tool_results"][-1]
        assert tool_result["tool_name"] == "phase_a_expand_history"
        history_result = (tool_result.get("evidence") or {}).get("history_expansion_result") or {}
        if history_result:
            assert history_result["meal_candidates"][0]["meal_thread_id"] == "77"
        context_packet = payload["manager_context_packet_v1"]
        if context_packet is not None:
            target_candidates = context_packet["target_candidates"]
            if "candidate_count" in target_candidates:
                assert target_candidates["candidate_count"] >= 1
            else:
                assert len(target_candidates["for_correction_or_removal"]) >= 1
        else:
            manager_context_pack = payload["phase_a_manager_context_pack"]
            manager_context = manager_context_pack.get("manager_context_summary") or manager_context_pack.get("manager_context")
            assert manager_context["candidate_attachment_targets"][0]["target_object_id"] == "77"
        return (
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "no_commit",
                "workflow_effect": "safe_failure",
                "target_attachment": {"mode": "target_committed_thread", "target_object_id": "77"},
                "exactness": "anchored",
                "confidence": "medium",
                "evidence_posture": "generic_with_uncertainty",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "generic_with_uncertainty",
            },
            {"round": 2},
        )


class _RepeatedHistoryRequestProvider(_HistoryRequestProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        payload = kwargs["user_payload"]
        assert isinstance(payload, dict)
        if len(self.calls) <= 2:
            return (
                {
                    "manager_action": "call_tools",
                    "tool_calls": [
                        {
                            "name": "phase_a_expand_history",
                            "arguments": {"reason": "target_ambiguity", "scope": "recent_meals"},
                        }
                    ],
                },
                {"round": len(self.calls)},
            )
        assert payload["tool_results"][-1]["failure_family"] == "phase_a_history_expansion_budget_exhausted"
        return (
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "no_commit",
                "workflow_effect": "safe_failure",
                "target_attachment": {"mode": "none"},
                "exactness": "unknown",
                "confidence": "low",
                "evidence_posture": "generic_with_uncertainty",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "generic_with_uncertainty",
            },
            {"round": 3},
        )


def test_manager_triggered_runtime_uses_existing_surfaces_and_reruns_attachment_guard() -> None:
    state = _resolved_state(retrieved_meal_records=[_meal_chunk()])
    context = build_current_turn_context_v1(
        raw_user_input="that milk tea half sugar",
        resolved_state=state,
    )
    pre_attachment = resolve_attachment_decision(context)
    pre_guard = resolve_transition_guard(context, pre_attachment)

    result = activate_manager_triggered_history_expansion(
        current_turn_context=context,
        resolved_state=state,
        pre_attachment_decision=pre_attachment,
        pre_transition_guard_result=pre_guard,
        manager_tool_arguments={"reason": "target_ambiguity", "scope": "recent_meals"},
    )

    assert result.attempted is True
    assert result.request.reason == "target_ambiguity"
    assert result.result.meal_candidates[0].meal_thread_id == "77"
    assert result.transcript_support_inventory == ("transcript:1",)
    assert result.post_attachment_decision.disposition == "answer_only"
    assert result.post_transition_guard_result.verdict == "answer_only"
    assert result.resolution_gain is False
    assert result.selected_candidate_ids == ("77",)
    tool_result = result.tool_result()
    assert tool_result["tool_name"] == "phase_a_expand_history"
    assert tool_result["mutation_result"] == {}
    assert tool_result["provenance"]["primary_truth"] == "structured_candidates"
    assert tool_result["evidence"]["history_expansion_result"]["meal_candidates"][0]["meal_thread_id"] == "77"
    assert tool_result["evidence"]["history_expansion_result"]["transcript_snippets"] == []


def test_manager_triggered_history_eligibility_is_surface_only_and_does_not_classify_budget_text() -> None:
    state = _resolved_state(retrieved_meal_records=[_meal_chunk()], pending_followup=True)
    resolved_context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=state,
    )
    resolved_attachment = resolve_attachment_decision(resolved_context)
    resolved_guard = resolve_transition_guard(resolved_context, resolved_attachment)
    resolved = manager_history_expansion_eligibility(
        current_turn_context=resolved_context,
        attachment_decision=resolved_attachment,
        transition_guard_result=resolved_guard,
    )
    budget_context = build_current_turn_context_v1(
        raw_user_input="how many calories are left today?",
        resolved_state=_resolved_state(retrieved_meal_records=[_meal_chunk()]),
    )
    budget_attachment = resolve_attachment_decision(budget_context)
    budget_guard = resolve_transition_guard(budget_context, budget_attachment)
    budget = manager_history_expansion_eligibility(
        current_turn_context=budget_context,
        attachment_decision=budget_attachment,
        transition_guard_result=budget_guard,
    )

    assert resolved.eligible is False
    assert resolved.reason == "pending_followup_pinned_for_manager_resolution"
    assert budget.eligible is True
    assert budget.reason == "manager_scope_required"
    assert budget.request_reason is None
    assert budget.request_scope is None


def test_manager_triggered_history_eligibility_skips_explicit_ui_target() -> None:
    event = InteractionEvent(
        source="ui",
        surface_mode="ui_anchored_action",
        event_type="edit_item",
        raw_text="half sugar",
        target_object_type="meal_thread",
        target_object_id="77",
    )
    context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=_resolved_state(retrieved_meal_records=[_meal_chunk()]),
        interaction_event=event,
    )
    attachment = resolve_attachment_decision(context)
    guard = resolve_transition_guard(context, attachment)

    result = manager_history_expansion_eligibility(
        current_turn_context=context,
        attachment_decision=attachment,
        transition_guard_result=guard,
    )

    assert result.eligible is False
    assert result.reason == "explicit_ui_target"


def test_manager_triggered_history_keeps_multi_candidate_ambiguity_conservative() -> None:
    state = _resolved_state(
        retrieved_meal_records=[
            _meal_chunk(meal_thread_id=77, meal_version_id=88),
            _meal_chunk(meal_thread_id=78, meal_version_id=89),
        ]
    )
    context = build_current_turn_context_v1(
        raw_user_input="that milk tea half sugar",
        resolved_state=state,
    )

    result = activate_manager_triggered_history_expansion(
        current_turn_context=context,
        resolved_state=state,
        manager_tool_arguments={"reason": "target_ambiguity", "scope": "recent_meals"},
    )

    assert result.attempted is True
    assert result.ambiguity_detected is True
    assert result.selected_candidate_ids == ()
    assert result.post_attachment_decision.disposition == "answer_only"


def test_manager_triggered_history_rejects_missing_manager_reason_scope() -> None:
    state = _resolved_state(retrieved_meal_records=[_meal_chunk()])
    context = build_current_turn_context_v1(
        raw_user_input="that milk tea half sugar",
        resolved_state=state,
    )

    result = activate_manager_triggered_history_expansion(
        current_turn_context=context,
        resolved_state=state,
        manager_tool_arguments={},
    )

    assert result.attempted is False
    assert result.request is None
    assert result.result is None
    assert result.failure_family == "phase_a_history_expansion_manager_scope_missing"
    assert result.enriched_current_turn_context == context


@pytest.mark.asyncio
async def test_run_intake_manager_refreshes_phase_a_payload_after_history_tool() -> None:
    state = _resolved_state(retrieved_meal_records=[_meal_chunk()])
    context = build_current_turn_context_v1(
        raw_user_input="that milk tea half sugar",
        resolved_state=state,
    )
    enriched = context.model_copy(
        update={
            "candidate_attachment_targets": [
                {
                    "target_object_type": "meal_thread",
                    "target_object_id": "77",
                    "source": "manager_triggered_history_expansion",
                    "confidence": "high",
                }
            ]
        }
    )
    provider = _HistoryRequestProvider()

    async def _tool_executor(**_: object) -> list[dict[str, object]]:
        return [
            {
                "tool_name": "phase_a_expand_history",
                "evidence": {"resolution_gain": True},
                "mutation_result": {},
                "provenance": {"phase_a_owner": "intake/application"},
                "confidence": "available",
                "failure_family": None,
            }
        ]

    async def _refresher(**_: object) -> dict[str, object]:
        return {
            "current_turn_context": enriched,
            "manager_context_pack": build_manager_context_pack(current_turn_context=enriched),
            "phase_a_history_expansion_enabled": False,
        }

    result = await run_intake_manager(
        provider=provider,
        raw_user_input="that milk tea half sugar",
        resolved_state=state,
        available_tools=("phase_a_expand_history",),
        current_turn_context=context,
        manager_context_pack=build_manager_context_pack(current_turn_context=context),
        phase_a_history_expansion_enabled=True,
        tool_executor=_tool_executor,
        manager_context_refresher=_refresher,
    )

    assert result.final_action == "no_commit"
    assert len(provider.calls) == 2
    assert result.trace["manager_rounds"][1]["phase_a_input"]["history_expansion_enabled"] is False


@pytest.mark.asyncio
async def test_process_intake_execution_turn_handles_manager_triggered_history_expansion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    state = _resolved_state(retrieved_meal_records=[_meal_chunk()])
    provider = _HistoryRequestProvider()

    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "apply_final_action_to_payload", lambda **_: None)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", lambda *_, **__: None)
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: state)
    monkeypatch.setattr(module, "build_intake_execution_response", lambda *_, **kwargs: {"captured_phase_a_trace": kwargs["phase_a_trace"]})

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="that milk tea half sugar",
        local_date="2026-04-29",
        allow_search=False,
        provider=provider,
        state_before=state,
        manager_decision=SimpleNamespace(intent_type="log_meal"),
        request_id="req-history-manager",
        stage_timings=[],
    )

    trace = result["captured_phase_a_trace"]["manager_triggered_history_expansion"]
    assert trace["triggered"] is True
    assert trace["selected_candidate_ids"] == ["77"]
    assert trace["post_decision"]["disposition"] == "answer_only"
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_process_intake_execution_turn_enforces_one_manager_triggered_history_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    state = _resolved_state(retrieved_meal_records=[_meal_chunk()])
    provider = _RepeatedHistoryRequestProvider()

    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "apply_final_action_to_payload", lambda **_: None)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", lambda *_, **__: None)
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: state)
    monkeypatch.setattr(module, "build_intake_execution_response", lambda *_, **kwargs: {"captured_phase_a_trace": kwargs["phase_a_trace"]})

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="that milk tea half sugar",
        local_date="2026-04-29",
        allow_search=False,
        provider=provider,
        state_before=state,
        manager_decision=SimpleNamespace(intent_type="log_meal"),
        request_id="req-history-repeat",
        stage_timings=[],
    )

    assert len(provider.calls) == 3
    assert result["captured_phase_a_trace"]["manager_triggered_history_expansion"]["triggered"] is True
