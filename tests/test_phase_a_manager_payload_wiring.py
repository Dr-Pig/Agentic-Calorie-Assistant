from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.intake.application.context_injection_policy import build_manager_context_pack
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.manager_context_policy import (
    MANAGER_CONTEXT_POLICY_VERSION,
    build_manager_context_packet_v1,
)
from app.runtime.application.manager_service import run_intake_manager
from app.runtime.agent.manager_result_builder import IntakeManagerResult
from app.shared.contracts.intake_results import EstimatePayload


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
            "CURRENT_BUDGET": {
                "budget_kcal": 1800,
                "consumed_kcal": 600,
                "remaining_kcal": 1200,
                "active_meal_count": 1,
            },
            "ACTIVE_BODY_PLAN": {
                "body_plan_id": 5,
                "goal_type": "lose_weight",
                "daily_budget_kcal": 1800,
            },
            "SESSION_SUMMARY": {
                "latest_assistant_turns": ["What size was it?"],
            },
        },
    )


def _resolved_state_with_recent_chat_turns() -> object:
    state = _resolved_state()
    state.injected_context["RECENT_CHAT_TURNS"] = [
        {
            "message_id": 41,
            "role": "user",
            "content": "我吃了滷味",
            "created_at": "2026-04-29T12:00:00+08:00",
            "trace_id": "turn-bare-luwei",
            "linked_meal_log_id": 10,
            "local_date": "2026-04-29",
        },
        {
            "message_id": 42,
            "role": "assistant",
            "content": "請列出滷味品項與大致份量。",
            "created_at": "2026-04-29T12:00:01+08:00",
            "trace_id": "turn-bare-luwei",
            "linked_meal_log_id": 10,
            "local_date": "2026-04-29",
            "structured_followup_question": "請列出滷味品項與大致份量。",
        },
    ]
    return state


def _empty_resolved_state() -> object:
    return SimpleNamespace(
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


def _correction_payload() -> EstimatePayload:
    return EstimatePayload(
        request_id="req-target-attachment",
        meal_title="chicken rice",
        estimated_kcal=320,
        source_decision="ready",
        answer_mode="direct_answer",
        action_taken="direct_answer",
        route_target="direct_answer",
        trace_contract={"canonical_write_decision": {"can_write_canonical": True}},
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
        available_tools=("budget.get_today_summary",),
    )

    payload = provider.calls[0]["user_payload"]
    assert isinstance(payload, dict)
    assert payload["phase_a_current_turn_context"]["prompt_payload_kind"] == "current_turn_context_compact_summary"
    assert payload["phase_a_current_turn_context"]["current_interaction_event"]["surface_mode"] == "chat_freeform"
    assert payload["phase_a_current_turn_context"]["candidate_attachment_targets"][0]["target_object_id"] == "77"
    assert "recent_chat_turns" in payload["phase_a_current_turn_context"]["omitted_fields"]
    assert "recent_chat_turns" not in payload["phase_a_current_turn_context"]
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
        "current_budget_snapshot",
        "recent_chat_turns",
    ]
    assert payload["phase_a_manager_context_pack"]["manager_context"]["current_budget_snapshot"]["read_only"] is True
    assert (
        payload["phase_a_manager_context_pack"]["manager_context"]["current_budget_snapshot"]["truth_owner"]
        == "budget_read_model"
    )
    assert "mutation_authority" not in payload["phase_a_manager_context_pack"]["manager_context"]["current_budget_snapshot"]
    assert payload["phase_a_manager_context_pack"]["available_if_needed"]["active_body_plan_snapshot"]["read_only"] is True
    assert "recent_committed_meal_refs" not in payload["phase_a_manager_context_pack"]["manager_context"]
    assert payload["phase_a_manager_context_pack"]["available_if_needed"]["recent_committed_meal_refs"][0]["meal_thread_id"] == 77
    assert payload["phase_a_surface_mode"] == "chat_freeform"
    assert payload["phase_a_history_expansion_enabled"] is False
    assert payload["phase_a_manager_context_pack_role"] == "primary_structured_context"
    assert payload["resolved_state_role"] == "compatibility_legacy"
    assert result.trace["manager_rounds"][0]["phase_a_input"]["phase_a_manager_context_pack_role"] == "primary_structured_context"
    assert result.trace["manager_rounds"][0]["phase_a_input"]["resolved_state_role"] == "compatibility_legacy"
    assert "injected_fields" in result.trace["manager_rounds"][0]["phase_a_input"]
    assert "promotion_reasons" in result.trace["manager_rounds"][0]["phase_a_input"]
    assert "raw_transcript" in result.trace["manager_rounds"][0]["phase_a_input"]["trace_only_inventory"]


@pytest.mark.asyncio
async def test_run_intake_manager_sends_bounded_recent_chat_turns_in_context_pack() -> None:
    resolved_state = _resolved_state_with_recent_chat_turns()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="有豆干、海帶、貢丸",
        resolved_state=resolved_state,
    )
    manager_context_pack = build_manager_context_pack(current_turn_context=current_turn_context)
    provider = _FakeProvider()

    result = await run_intake_manager(
        provider=provider,
        raw_user_input="有豆干、海帶、貢丸",
        resolved_state=resolved_state,
        current_turn_context=current_turn_context,
        manager_context_pack=manager_context_pack,
        available_tools=("budget.get_today_summary",),
    )

    payload = provider.calls[0]["user_payload"]
    recent_chat_turns = payload["phase_a_manager_context_pack"]["manager_context"]["recent_chat_turns"]
    assert [turn["role"] for turn in recent_chat_turns] == ["user", "assistant"]
    assert recent_chat_turns[1]["structured_followup_question"] == "請列出滷味品項與大致份量。"
    assert recent_chat_turns[1]["trace_id"] == "turn-bare-luwei"
    assert recent_chat_turns[1]["role"] == "assistant"
    assert recent_chat_turns[1]["read_only"] is True
    assert recent_chat_turns[1]["mutation_authority"] is False
    assert payload["phase_a_manager_context_pack"]["policy"]["must_inject"] == [
        "interaction_event",
        "active_meal_thread_ref",
        "pending_followup",
        "candidate_attachment_targets",
        "current_budget_snapshot",
        "recent_chat_turns",
    ]
    assert "recent_chat_turns" in result.trace["manager_rounds"][0]["phase_a_input"]["injected_fields"]


@pytest.mark.asyncio
async def test_run_intake_manager_sends_manager_context_packet_v1_sidecar_without_changing_decision() -> None:
    resolved_state = _resolved_state_with_recent_chat_turns()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=resolved_state,
    )
    packet = build_manager_context_packet_v1(
        current_turn_context=current_turn_context,
        user_id="user-1",
        local_date="2026-04-29",
        session_id="session-1",
    )
    provider = _FakeProvider()

    result = await run_intake_manager(
        provider=provider,
        raw_user_input="half sugar",
        resolved_state=resolved_state,
        current_turn_context=current_turn_context,
        manager_context_pack=build_manager_context_pack(current_turn_context=current_turn_context),
        manager_context_packet_v1=packet,
        available_tools=("budget.get_today_summary",),
    )

    payload = provider.calls[0]["user_payload"]
    sidecar_trace = result.trace["manager_rounds"][0]["phase_a_input"]["manager_context_packet_v1"]
    assert payload["phase_a_manager_context_pack"]["prompt_payload_kind"] == "manager_context_pack_lineage_summary"
    assert payload["phase_a_manager_context_pack"]["primary_context_source"] == "manager_context_packet_v1"
    assert payload["phase_a_manager_context_pack"]["legacy_payload_mode"] == "packet_primary_reference"
    assert "manager_context" not in payload["phase_a_manager_context_pack"]
    assert payload["phase_a_manager_context_pack"]["context_packet_carries_full_fields"] is True
    assert payload["manager_context_packet_v1"]["prompt_payload_kind"] == "manager_context_packet_v1_prompt_compact"
    assert payload["manager_context_packet_v1"]["metadata"]["context_policy_version"] == MANAGER_CONTEXT_POLICY_VERSION
    assert payload["manager_context_packet_v1"]["recent_chat_window"]["loaded_message_count"] == 2
    assert "not_claiming" not in payload["manager_context_packet_v1"]
    assert "omitted_context" not in payload["manager_context_packet_v1"]
    assert sidecar_trace["context_policy_version"] == MANAGER_CONTEXT_POLICY_VERSION
    assert sidecar_trace["loaded_context_summary"]["recent_chat_messages"] == 2
    assert sidecar_trace["omitted_context_summary"]["recent_chat_messages_omitted"] == 0
    assert "messages" not in sidecar_trace["recent_chat_window"]
    assert result.final_action == "no_commit"
    assert result.workflow_effect == "safe_failure"


@pytest.mark.asyncio
async def test_run_intake_manager_uses_packet_primary_progressive_context_disclosure() -> None:
    resolved_state = _resolved_state_with_recent_chat_turns()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="remove the milk tea",
        resolved_state=resolved_state,
    )
    packet = build_manager_context_packet_v1(
        current_turn_context=current_turn_context,
        user_id="user-1",
        local_date="2026-04-29",
        session_id="session-1",
        target_candidates=current_turn_context.candidate_attachment_targets,
    )
    provider = _FakeProvider()

    result = await run_intake_manager(
        provider=provider,
        raw_user_input="remove the milk tea",
        resolved_state=resolved_state,
        current_turn_context=current_turn_context,
        manager_context_pack=build_manager_context_pack(current_turn_context=current_turn_context),
        manager_context_packet_v1=packet,
        available_tools=("resolve_correction_target",),
    )

    payload = provider.calls[0]["user_payload"]
    current_payload = payload["phase_a_current_turn_context"]
    context_pack_payload = payload["phase_a_manager_context_pack"]
    packet_payload = payload["manager_context_packet_v1"]

    assert current_payload["prompt_payload_kind"] == "current_turn_context_lineage_summary"
    assert current_payload["primary_context_source"] == "manager_context_packet_v1"
    assert current_payload["legacy_payload_mode"] == "packet_primary_reference"
    assert current_payload["full_context_omitted_from_prompt"] is True
    assert current_payload["context_packet_carries_full_fields"] is True
    assert "candidate_attachment_targets" not in current_payload
    assert "pending_followup" not in current_payload
    assert "recent_chat_turns" not in current_payload

    assert context_pack_payload["prompt_payload_kind"] == "manager_context_pack_lineage_summary"
    assert context_pack_payload["primary_context_source"] == "manager_context_packet_v1"
    assert context_pack_payload["legacy_payload_mode"] == "packet_primary_reference"
    assert context_pack_payload["full_context_omitted_from_prompt"] is True
    assert context_pack_payload["context_packet_carries_full_fields"] is True
    assert "manager_context" not in context_pack_payload
    assert "manager_context_summary" not in context_pack_payload
    assert len(json.dumps(current_payload, ensure_ascii=False)) < 500
    assert len(json.dumps(context_pack_payload, ensure_ascii=False)) < 500

    assert packet_payload["prompt_payload_kind"] == "manager_context_packet_v1_prompt_compact"
    assert packet_payload["hard_pins"]["pending_followup"]["meal_thread_id"] == 77
    assert packet_payload["target_candidates"]["for_correction_or_removal"]
    assert len(json.dumps(packet_payload, ensure_ascii=False)) < len(json.dumps(packet, ensure_ascii=False))
    progressive = result.manager_rounds[0]["prompt_layer_contract"]["progressive_disclosure"]
    assert progressive["context_packet_primary"] is True
    assert progressive["full_context_in_user_payload"] is False
    assert progressive["legacy_context_payload_mode"] == "packet_primary_reference"


@pytest.mark.asyncio
async def test_run_intake_manager_compacts_context_packet_after_tool_evidence() -> None:
    class _ToolThenFinalProvider(_FakeProvider):
        async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
            self.calls.append(dict(kwargs))
            if len(self.calls) == 1:
                return (
                    {"manager_action": "call_tools", "tool_calls": [{"name": "estimate_nutrition"}]},
                    {"source": "fake"},
                )
            return await super().complete_with_trace(**kwargs)

    resolved_state = _resolved_state_with_recent_chat_turns()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=resolved_state,
    )
    packet = build_manager_context_packet_v1(
        current_turn_context=current_turn_context,
        user_id="user-1",
        local_date="2026-04-29",
        session_id="session-1",
        target_candidates=current_turn_context.candidate_attachment_targets,
    )
    provider = _ToolThenFinalProvider()

    async def tool_executor(**_: object) -> list[dict[str, object]]:
        return [
            {
                "tool_name": "estimate_nutrition",
                "evidence": {"nutrition_payload": {"estimated_kcal": 520}},
                "failure_family": None,
            }
        ]

    result = await run_intake_manager(
        provider=provider,
        raw_user_input="half sugar",
        resolved_state=resolved_state,
        current_turn_context=current_turn_context,
        manager_context_pack=build_manager_context_pack(current_turn_context=current_turn_context),
        manager_context_packet_v1=packet,
        available_tools=("estimate_nutrition",),
        tool_executor=tool_executor,
    )

    first_packet = provider.calls[0]["user_payload"]["manager_context_packet_v1"]
    second_packet = provider.calls[1]["user_payload"]["manager_context_packet_v1"]
    assert first_packet["prompt_payload_kind"] == "manager_context_packet_v1_prompt_compact"
    assert first_packet["recent_chat_window"]["messages"]
    assert first_packet["target_candidates"]["for_correction_or_removal"]
    assert second_packet["prompt_payload_kind"] == "manager_context_packet_v1_post_tool_reference"
    assert "messages" not in second_packet["recent_chat_window"]
    assert second_packet["recent_chat_window"]["messages_omitted_after_tool_evidence"] is True
    assert second_packet["target_candidates"]["candidate_count"] == len(
        first_packet["target_candidates"]["for_correction_or_removal"]
    )
    assert "for_correction_or_removal" not in second_packet["target_candidates"]
    assert second_packet["hard_pins"]["pending_followup"]["meal_thread_id"] == 77
    assert result.final_action == "no_commit"


@pytest.mark.asyncio
async def test_run_intake_manager_compacts_legacy_resolved_state_prompt_payload() -> None:
    resolved_state = _resolved_state_with_recent_chat_turns()
    resolved_state.injected_context["TRACE_ONLY_BULK_STATE"] = {
        "debug_blob": "x" * 20_000,
        "full_transcript": ["not manager prompt input"] * 100,
    }
    resolved_state.injected_context["RECENT_COMMITTED_MEALS_SUMMARY"][0]["item_candidates"] = [
        {"meal_item_id": 501, "canonical_name": "soup", "estimated_kcal": 120},
    ]
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="remove soup",
        resolved_state=resolved_state,
    )
    packet = build_manager_context_packet_v1(
        current_turn_context=current_turn_context,
        user_id="user-1",
        local_date="2026-04-29",
        session_id="session-1",
    )
    provider = _FakeProvider()

    await run_intake_manager(
        provider=provider,
        raw_user_input="remove soup",
        resolved_state=resolved_state,
        current_turn_context=current_turn_context,
        manager_context_pack=build_manager_context_pack(current_turn_context=current_turn_context),
        manager_context_packet_v1=packet,
        available_tools=("budget.get_today_summary",),
    )

    payload = provider.calls[0]["user_payload"]
    resolved_payload = payload["resolved_state"]
    assert resolved_payload["prompt_payload_kind"] == "resolved_state_compact_summary"
    assert resolved_payload["full_state_omitted_from_prompt"] is True
    assert resolved_payload["primary_context_source"] == "manager_context_packet_v1"
    assert resolved_payload["summary"]["onboarding_ready"] is True
    assert "TRACE_ONLY_BULK_STATE" in resolved_payload["omitted_injected_context_keys"]
    assert "debug_blob" not in json.dumps(resolved_payload, ensure_ascii=False)
    assert len(json.dumps(resolved_payload, ensure_ascii=False)) < 1500
    assert payload["manager_context_packet_v1"]["target_candidates"]["for_correction_or_removal"]


@pytest.mark.asyncio
async def test_run_intake_manager_refreshes_manager_context_packet_v1_between_rounds() -> None:
    class _ToolThenFinalProvider(_FakeProvider):
        async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
            self.calls.append(dict(kwargs))
            if len(self.calls) == 1:
                return (
                    {"manager_action": "call_tools", "tool_calls": [{"name": "phase_a_expand_history"}]},
                    {"source": "fake"},
                )
            return await super().complete_with_trace(**kwargs)

    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=resolved_state,
    )
    initial_packet = build_manager_context_packet_v1(
        current_turn_context=current_turn_context,
        user_id="user-1",
        local_date="2026-04-29",
        session_id="session-1",
        max_recent_messages=1,
    )
    refreshed_context = current_turn_context.model_copy(
        update={"recent_chat_turns": [{"message_id": 99, "role": "assistant", "content": "expanded"}]}
    )
    refreshed_packet = build_manager_context_packet_v1(
        current_turn_context=refreshed_context,
        user_id="user-1",
        local_date="2026-04-29",
        session_id="session-1",
    )
    provider = _ToolThenFinalProvider()

    async def _tool_executor(**_: object) -> list[dict[str, object]]:
        return [{"tool_name": "phase_a_expand_history", "confidence": "medium"}]

    async def _refresher(**_: object) -> dict[str, object]:
        return {
            "current_turn_context": refreshed_context,
            "manager_context_packet_v1": refreshed_packet,
        }

    result = await run_intake_manager(
        provider=provider,
        raw_user_input="half sugar",
        resolved_state=resolved_state,
        current_turn_context=current_turn_context,
        manager_context_packet_v1=initial_packet,
        available_tools=("phase_a_expand_history",),
        tool_executor=_tool_executor,
        manager_context_refresher=_refresher,
    )

    second_payload = provider.calls[1]["user_payload"]
    assert second_payload["manager_context_packet_v1"]["recent_chat_window"]["messages"][0]["message_id"] == 99
    assert result.trace["manager_rounds"][1]["phase_a_input"]["manager_context_packet_v1"]["loaded_context_summary"][
        "recent_chat_messages"
    ] == 1


@pytest.mark.asyncio
async def test_promoted_context_visibility_does_not_change_provider_final_action() -> None:
    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=resolved_state,
    )
    provider = _FakeProvider()

    result = await run_intake_manager(
        provider=provider,
        raw_user_input="half sugar",
        resolved_state=resolved_state,
        current_turn_context=current_turn_context,
        manager_context_pack=build_manager_context_pack(current_turn_context=current_turn_context),
        available_tools=("budget.get_today_summary",),
    )

    manager_context = provider.calls[0]["user_payload"]["phase_a_manager_context_pack"]["manager_context"]
    assert "target_resolution_posture" in manager_context
    assert manager_context["target_resolution_posture"]["mutation_authority"] is False
    assert result.final_action == "no_commit"


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
        available_tools=("budget.get_today_summary",),
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
        available_tools=("budget.get_today_summary",),
    )

    assert result.final_action == "no_commit"
    assert result.request_failure_family == "phase_a_transition_guard_blocked"
    assert (
        result.guard_outcome["phase_a_transition_guard_preflight"]["repair_result"]
        == "not_attempted"
    )


@pytest.mark.asyncio
async def test_process_intake_execution_turn_validates_manager_final_target_attachment_for_correction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="unrelated surface text",
        resolved_state=resolved_state,
    )
    nutrition_artifact = SimpleNamespace(payload=_correction_payload())
    candidate_target = {
        "target_resolution_source": "manager_context_candidates",
        "meal_thread_id": 1,
        "meal_version_id": 1,
        "item_candidates": [
            {"meal_item_id": 11, "canonical_name": "chicken rice"},
            {"meal_item_id": 12, "canonical_name": "soup"},
        ],
    }
    persisted: list[dict[str, object]] = []

    async def _fake_execute_manager_tool_calls(**kwargs: object) -> list[dict[str, object]]:
        kwargs["tool_state"]["nutrition_artifact"] = nutrition_artifact
        return [{"tool_name": "estimate_nutrition", "failure_family": None}]

    async def _fake_run_intake_manager(**kwargs: object) -> object:
        await kwargs["tool_executor"](tool_calls=[{"name": "estimate_nutrition"}])
        target_attachment = {
            "target_object_type": "meal_item_candidate",
            "meal_thread_id": 1,
            "meal_version_id": 1,
            "meal_item_id": 11,
            "canonical_name": "chicken rice",
        }
        return IntakeManagerResult(
            intent="correct_meal",
            manager_action="final",
            final_action="correction_applied",
            workflow_effect="correction",
            target_attachment=target_attachment,
            exactness="medium",
            confidence="high",
            evidence_posture="evidence_present",
            repair_ack=False,
            answer_contract={},
            semantic_decision={
                "semantic_authority": "manager_llm",
                "current_turn_intent": "correct_meal",
                "target_attachment": target_attachment,
                "workflow_effect": "correction",
                "final_action_candidate": "correction_applied",
                "estimation_posture": "tool_complete",
                "followup_posture": "none",
                "mutation_intent_candidate": "correction_write",
                "uncertainty_posture": "low",
                "source": "manager_structured_target_attachment",
            },
            intent_type="log_meal",
            manager_rounds=(),
            tool_results=(),
            request_failure_family=None,
            trace={},
            guard_outcome={},
        )

    def _fake_persist(*_: object, **kwargs: object) -> dict[str, object]:
        persisted.append(dict(kwargs))
        return {"canonical_commit": True}

    monkeypatch.setattr(module, "execute_manager_tool_calls", _fake_execute_manager_tool_calls)
    monkeypatch.setattr(module, "run_intake_manager", _fake_run_intake_manager)
    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: candidate_target)
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", _fake_persist)
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(
        module,
        "build_intake_execution_response",
        lambda *_, **kwargs: {
            "persistence_result": kwargs["persistence_result"],
            "phase_a_trace": kwargs["phase_a_trace"],
            "nutrition_artifact": kwargs["nutrition_artifact"],
        },
    )

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="unrelated surface text",
        local_date="2026-04-29",
        allow_search=False,
        provider=_FakeProvider(),
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal", tool_calls=(), llm_used=False),
        request_id="req-target-attachment",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    preflight = result["phase_a_trace"]["phase_a_commit_boundary_preflight"]
    trace_contract = result["nutrition_artifact"].payload.trace_contract
    assert persisted
    assert preflight["blocked"] is False
    assert preflight["correction_target_resolved"] is True
    assert preflight["correction_target_validation"]["meal_item_id"] == 11
    assert trace_contract["correction_target_ref"] == {
        "meal_thread_id": 1,
        "meal_item_id": 11,
        "canonical_name": "chicken rice",
    }
    assert trace_contract["correction_target_ref_source"] == "manager_target_attachment_validated"


@pytest.mark.asyncio
async def test_process_intake_execution_turn_rejects_unmatched_manager_target_attachment_without_raw_text_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="remove soup please",
        resolved_state=resolved_state,
    )
    nutrition_artifact = SimpleNamespace(payload=_correction_payload())
    candidate_target = {
        "target_resolution_source": "manager_context_candidates",
        "meal_thread_id": 1,
        "meal_version_id": 1,
        "item_candidates": [
            {"meal_item_id": 11, "canonical_name": "chicken rice"},
            {"meal_item_id": 12, "canonical_name": "soup"},
        ],
    }
    persisted: list[object] = []

    async def _fake_execute_manager_tool_calls(**kwargs: object) -> list[dict[str, object]]:
        kwargs["tool_state"]["nutrition_artifact"] = nutrition_artifact
        return [{"tool_name": "estimate_nutrition", "failure_family": None}]

    async def _fake_run_intake_manager(**kwargs: object) -> object:
        await kwargs["tool_executor"](tool_calls=[{"name": "estimate_nutrition"}])
        target_attachment = {
            "target_object_type": "meal_item_candidate",
            "canonical_name": "salad",
        }
        return IntakeManagerResult(
            intent="correct_meal",
            manager_action="final",
            final_action="correction_applied",
            workflow_effect="correction",
            target_attachment=target_attachment,
            exactness="medium",
            confidence="high",
            evidence_posture="evidence_present",
            repair_ack=False,
            answer_contract={},
            semantic_decision={
                "semantic_authority": "manager_llm",
                "current_turn_intent": "correct_meal",
                "target_attachment": target_attachment,
                "workflow_effect": "correction",
                "final_action_candidate": "correction_applied",
                "estimation_posture": "tool_complete",
                "followup_posture": "none",
                "mutation_intent_candidate": "correction_write",
                "uncertainty_posture": "low",
                "source": "manager_structured_target_attachment",
            },
            intent_type="log_meal",
            manager_rounds=(),
            tool_results=(),
            request_failure_family=None,
            trace={},
            guard_outcome={},
        )

    monkeypatch.setattr(module, "execute_manager_tool_calls", _fake_execute_manager_tool_calls)
    monkeypatch.setattr(module, "run_intake_manager", _fake_run_intake_manager)
    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: candidate_target)
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(
        module,
        "persist_intake_execution_artifact",
        lambda *_, **kwargs: persisted.append(object()) if kwargs["nutrition_artifact"] is not None else None,
    )
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(
        module,
        "build_intake_execution_response",
        lambda *_, **kwargs: {
            "persistence_result": kwargs["persistence_result"],
            "phase_a_trace": kwargs["phase_a_trace"],
        },
    )

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="remove soup please",
        local_date="2026-04-29",
        allow_search=False,
        provider=_FakeProvider(),
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal", tool_calls=(), llm_used=False),
        request_id="req-target-attachment-rejected",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    preflight = result["phase_a_trace"]["phase_a_commit_boundary_preflight"]
    assert persisted == []
    assert preflight["blocked"] is True
    assert preflight["correction_target_resolved"] is False
    assert (
        preflight["correction_target_validation"]["manager_target_proposal_validation"]["failure_family"]
        == "manager_target_proposal_not_found"
    )


@pytest.mark.asyncio
async def test_execute_intake_turn_passes_current_turn_context_to_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.composition import intake_turn_orchestrator as module

    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="what's left today?",
        resolved_state=resolved_state,
    )
    packet = build_manager_context_packet_v1(
        current_turn_context=current_turn_context,
        user_id="user-1",
        local_date="2026-04-29",
        session_id="session-1",
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
        manager_context_packet_v1=packet,
        phase_a_trace={},
    )

    assert captured["current_turn_context"] == current_turn_context
    assert captured["manager_context_pack"] is not None
    assert captured["manager_context_packet_v1"] == packet
    assert result["assistant_message"] == "ok"


@pytest.mark.asyncio
async def test_process_intake_execution_turn_passes_current_turn_context_to_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.composition import intake_execution_orchestrator as module

    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=resolved_state,
    )
    packet = build_manager_context_packet_v1(
        current_turn_context=current_turn_context,
        user_id="user-1",
        local_date="2026-04-29",
        session_id="session-1",
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
        manager_context_packet_v1=packet,
        phase_a_trace={},
    )

    assert captured["current_turn_context"] == current_turn_context
    assert captured["manager_context_pack"] is not None
    assert captured["manager_context_packet_v1"] == packet
    assert result["captured_phase_a_trace"]["phase_a_commit_boundary_preflight"]["bypassed"] is True
    assert (
        result["captured_phase_a_trace"]["phase_a_commit_boundary_preflight"]["bypass_reason"]
        == "non_persistence_effect"
    )


@pytest.mark.asyncio
async def test_process_intake_execution_turn_persists_manager_ask_followup_as_draft_support_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    resolved_state = _empty_resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="bare basket",
        resolved_state=resolved_state,
    )
    persisted: list[dict[str, object]] = []

    async def _fake_run_intake_manager(**_: object) -> IntakeManagerResult:
        followup_question = "Which items and portions should I estimate?"
        return IntakeManagerResult(
            intent="log_meal",
            manager_action="final",
            final_action="ask_followup",
            workflow_effect="ask_followup",
            target_attachment={"mode": "new_meal"},
            exactness="unknown",
            confidence="medium",
            evidence_posture="composition_unknown",
            repair_ack=False,
            answer_contract={
                "reply_text": followup_question,
                "followup_question": followup_question,
            },
            uncertainty_posture="high",
            evidence_honesty_posture="insufficient_details",
            semantic_decision={
                "semantic_authority": "manager_llm",
                "current_turn_intent": "log_meal",
                "target_attachment": {"mode": "new_meal"},
                "workflow_effect": "ask_followup",
                "final_action_candidate": "ask_followup",
                "estimation_posture": "insufficient_details",
                "followup_posture": "ask_required",
                "followup_question": followup_question,
                "mutation_intent_candidate": "no_mutation",
                "uncertainty_posture": "high",
                "source": "manager_structured_ask_followup",
            },
            intent_type="log_meal",
            manager_rounds=(),
            tool_results=(),
            request_failure_family=None,
            trace={},
            guard_outcome={},
        )

    def _fake_persist(*_: object, **kwargs: object) -> SimpleNamespace:
        persisted.append(dict(kwargs))
        payload = kwargs["nutrition_artifact"].payload
        kwargs["state_mutation_summary"]["draft_saved"] = True
        return SimpleNamespace(
            action="save_draft_log",
            status="draft_unresolved",
            persisted_log_id=123,
            canonical_commit=None,
            payload=payload,
        )

    monkeypatch.setattr(module, "run_intake_manager", _fake_run_intake_manager)
    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", _fake_persist)
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(
        module,
        "build_intake_execution_response",
        lambda *_, **kwargs: {
            "manager_result": kwargs["manager_result"],
            "nutrition_artifact": kwargs["nutrition_artifact"],
            "persistence_result": kwargs["persistence_result"],
            "phase_a_trace": kwargs["phase_a_trace"],
            "state_mutation_summary": kwargs["state_mutation_summary"],
        },
    )

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="bare basket",
        local_date="2026-04-29",
        allow_search=False,
        provider=_FakeProvider(),
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal", tool_calls=(), llm_used=False),
        request_id="req-manager-ask-followup-draft",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    payload = result["nutrition_artifact"].payload
    preflight = result["phase_a_trace"]["phase_a_commit_boundary_preflight"]
    assert len(persisted) == 1
    assert persisted[0]["final_action"] == "ask_followup"
    assert result["manager_result"].final_action == "ask_followup"
    assert result["state_mutation_summary"]["draft_saved"] is True
    assert result["persistence_result"].canonical_commit is None
    assert payload.action_taken == "clarify_before_estimate"
    assert payload.estimated_kcal == 0
    assert payload.source_decision == "ask_user"
    assert payload.trace_contract["response_mode_hint"] == "clarify_first"
    assert payload.trace_contract["manager_ask_followup_draft_contract"]["deterministic_role"] == (
        "persist_manager_owned_pending_followup_only"
    )
    assert payload.trace_contract["canonical_write_decision"] == {
        "can_write_canonical": False,
        "source": "manager_ask_followup_draft",
    }
    assert payload.followup_question == "Which items and portions should I estimate?"
    assert preflight["blocked"] is False
    assert preflight["projected_commit_intent"] == "draft"


@pytest.mark.asyncio
async def test_process_intake_execution_turn_allows_manager_ask_followup_through_runtime_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    class _AskFollowupProvider:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def readiness(self) -> dict[str, object]:
            return {"configured": True}

        async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
            user_payload = dict(kwargs.get("user_payload") or {})
            self.calls.append(user_payload)
            followup_question = "Which items and portions should I estimate?"
            if {"body.get_active_plan", "budget.get_today_summary"}.intersection(set(user_payload.get("available_tools") or [])):
                return (
                    {
                        "manager_action": "final",
                        "intent": "log_meal",
                        "intent_type": "log_meal",
                        "final_action": "route_to_intake",
                        "workflow_effect": "route_to_intake",
                        "target_attachment": {"mode": "new_meal"},
                        "answer_contract": {"reply_text": "route_to_intake"},
                        "semantic_decision": {
                            "semantic_authority": "deterministic_fake_provider",
                            "current_turn_intent": "log_meal",
                            "target_attachment": {"mode": "new_meal"},
                            "workflow_effect": "route_to_intake",
                            "final_action_candidate": "route_to_intake",
                            "estimation_posture": "needs_manager_execution",
                            "followup_posture": "none",
                            "mutation_intent_candidate": "canonical_write",
                            "uncertainty_posture": "bounded",
                            "source": "test_fake_provider",
                        },
                    },
                    {"source": "test_fake_provider"},
                )
            return (
                {
                    "manager_action": "final",
                    "intent": "log_meal",
                    "intent_type": "log_meal",
                    "final_action": "ask_followup",
                    "workflow_effect": "ask_followup",
                    "target_attachment": {"mode": "new_meal"},
                    "answer_contract": {
                        "reply_text": followup_question,
                        "followup_question": followup_question,
                    },
                    "semantic_decision": {
                        "semantic_authority": "deterministic_fake_provider",
                        "current_turn_intent": "log_meal",
                        "target_attachment": {"mode": "new_meal"},
                        "workflow_effect": "ask_followup",
                        "final_action_candidate": "ask_followup",
                        "estimation_posture": "insufficient_details",
                        "followup_posture": "ask_required",
                        "followup_question": followup_question,
                        "mutation_intent_candidate": "no_mutation",
                        "uncertainty_posture": "high",
                        "source": "test_fake_provider",
                    },
                },
                {"source": "test_fake_provider"},
            )

    resolved_state = _empty_resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="bare basket",
        resolved_state=resolved_state,
    )
    persisted: list[dict[str, object]] = []

    def _fake_persist(*_: object, **kwargs: object) -> SimpleNamespace:
        persisted.append(dict(kwargs))
        payload = kwargs["nutrition_artifact"].payload
        kwargs["state_mutation_summary"]["draft_saved"] = True
        return SimpleNamespace(
            action="save_draft_log",
            status="draft_unresolved",
            persisted_log_id=321,
            canonical_commit=None,
            payload=payload,
        )

    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", _fake_persist)
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(
        module,
        "build_intake_execution_response",
        lambda *_, **kwargs: {"manager_result": kwargs["manager_result"]},
    )

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="bare basket",
        local_date="2026-04-29",
        allow_search=False,
        provider=_AskFollowupProvider(),
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal"),
        request_id="req-1",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    assert persisted
    assert persisted[0]["final_action"] == "ask_followup"
    assert result["manager_result"].final_action == "ask_followup"
    assert result["manager_result"].workflow_effect == "ask_followup"


@pytest.mark.asyncio
async def test_process_intake_execution_turn_does_not_create_draft_support_without_manager_ask_followup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    resolved_state = _empty_resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="bare basket",
        resolved_state=resolved_state,
    )
    persisted: list[object] = []

    async def _fake_run_intake_manager(**_: object) -> IntakeManagerResult:
        return IntakeManagerResult(
            intent="log_meal",
            manager_action="final",
            final_action="no_commit",
            workflow_effect="safe_failure",
            target_attachment={"mode": "none"},
            answer_contract={"reply_text": "Cannot proceed."},
            semantic_decision={
                "semantic_authority": "manager_llm",
                "current_turn_intent": "log_meal",
                "target_attachment": {"mode": "none"},
                "workflow_effect": "safe_failure",
                "final_action_candidate": "no_commit",
                "estimation_posture": "insufficient_details",
                "followup_posture": "none",
                "mutation_intent_candidate": "no_mutation",
                "uncertainty_posture": "high",
                "source": "manager_structured_no_commit",
            },
        )

    monkeypatch.setattr(module, "run_intake_manager", _fake_run_intake_manager)
    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(
        module,
        "persist_intake_execution_artifact",
        lambda *_, **kwargs: persisted.append(object()) if kwargs["nutrition_artifact"] is not None else None,
    )
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(
        module,
        "build_intake_execution_response",
        lambda *_, **kwargs: {
            "manager_result": kwargs["manager_result"],
            "nutrition_artifact": kwargs["nutrition_artifact"],
            "persistence_result": kwargs["persistence_result"],
            "phase_a_trace": kwargs["phase_a_trace"],
        },
    )

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="bare basket",
        local_date="2026-04-29",
        allow_search=False,
        provider=_FakeProvider(),
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal", tool_calls=(), llm_used=False),
        request_id="req-no-manager-ask-followup-draft",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    assert persisted == []
    assert result["nutrition_artifact"] is None
    assert result["manager_result"].final_action == "no_commit"
    assert result["phase_a_trace"]["phase_a_commit_boundary_preflight"]["bypassed"] is True


@pytest.mark.asyncio
async def test_process_intake_execution_turn_surfaces_shadow_when_back_reference_needs_manager(
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

    shadow = captured["phase_a_shadow_hypothesis"]
    assert shadow is not None
    assert shadow["role"] == "tentative_non_authoritative"
    assert shadow["candidate_target_object_id"] == "77"
    assert shadow["candidate_intent"] == "manager_review_required"
    assert shadow["mutation_authority"] is False
    trace = result["captured_phase_a_trace"]["shadow_hypothesis_runtime"]
    assert trace["created"] is True
    assert trace["skip_reason"] is None
    assert trace["candidate_target_object_id"] == "77"
    assert trace["mutation_authority"] is False


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
