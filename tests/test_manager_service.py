from types import SimpleNamespace
from pathlib import Path

import pytest

from app.runtime.application import manager_service
from app.runtime.agent.manager_payload_utils import stable_available_tools


def test_manager_service_exposes_single_entrypoint_and_bounded_rounds() -> None:
    assert hasattr(manager_service, "run_intake_manager")
    assert manager_service.MAX_MANAGER_ROUNDS == 3


def test_manager_service_has_no_step_specific_entrypoints() -> None:
    source = manager_service.__file__
    with open(source, "r", encoding="utf-8") as handle:
        content = handle.read()

    assert "decide_" + "intake_turn_turn" not in content
    assert "decide_" + "intake_execution_step1" not in content
    assert "decide_" + "intake_execution_step2" not in content


def test_single_manager_entrypoint_has_no_bundle_specific_modes() -> None:
    source = manager_service.__file__
    with open(source, "r", encoding="utf-8") as handle:
        content = handle.read()

    assert "intake_execution" + "_round_1" not in content
    assert "intake_execution" + "_final" not in content


def test_single_manager_system_prompt_requires_semantic_contract_not_reasoning_dump() -> None:
    source = Path(manager_service.__file__).resolve().parents[1] / "agent" / "manager_system_prompt.py"
    with open(source, "r", encoding="utf-8") as handle:
        content = handle.read()

    assert "intent, target_attachment" in content
    assert "semantic_decision" in content
    assert "exactness, confidence, evidence_posture, repair_ack" in content
    assert "thoughts" not in content


def test_single_manager_system_prompt_consumes_product_policy_hints_without_owning_them() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT

    assert "manager_product_policy_hints" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "pearl_milk_tea_missing_sugar_size" not in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "self_selected_basket_without_listed_items" not in SINGLE_MANAGER_SYSTEM_PROMPT


def test_single_manager_system_prompt_restricts_tool_calls_to_available_surface() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT

    assert "Only call tool names listed in user_payload.available_tools" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "do not call it or invent a compatible alias" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "manager_scope_policy" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "Scope policy has priority over evidence and target-resolution rules" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "manager_loop_scope='turn_entry_or_read_only'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "workflow_effect='route_to_intake'" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_stable_available_tools_normalizes_order_and_deduplicates() -> None:
    assert stable_available_tools(
        ("budget.get_today_summary", "body.get_latest_observation", "budget.get_today_summary")
    ) == ("body.get_latest_observation", "budget.get_today_summary")


class FakeLoopProvider:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def readiness(self) -> dict[str, object]:
        return {
            "configured": True,
            "provider": "fake_provider",
            "manager_model": "fake-model",
            "stage_models": {"intake_manager_round": "fake-model"},
        }

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        if not self.responses:
            return {"manager_action": "call_tools", "tool_calls": [{"name": "budget.get_today_summary"}]}, {"source": "fake"}
        return self.responses.pop(0), {"source": "fake", "call_index": len(self.calls)}


@pytest.mark.asyncio
async def test_run_intake_manager_executes_tools_and_feeds_results_into_next_round() -> None:
    provider = FakeLoopProvider(
        [
            {"manager_action": "call_tools", "tool_calls": [{"name": "budget.get_today_summary"}]},
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "commit",
                "workflow_effect": "commit",
                "target_attachment": {"mode": "new_meal"},
                "exactness": "anchored",
                "confidence": "medium",
                "evidence_posture": "generic_with_uncertainty",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "generic_with_uncertainty",
            },
        ]
    )
    async def tool_executor(*, tool_calls: list[dict[str, object]], **_: object) -> list[dict[str, object]]:
        tool_calls_copy = [dict(item) for item in tool_calls]
        tool_calls.append({"name": "sentinel"})  # mutate caller copy if implementation leaks it
        return [{"tool_name": item["name"], "evidence": {"remaining_kcal": 1200}, "failure_family": None} for item in tool_calls_copy]

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="今天還剩多少熱量",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("budget.get_today_summary",),
        tool_executor=tool_executor,
    )

    assert result.final_action == "commit"
    assert result.request_failure_family is None
    assert result.intent == "log_meal"
    assert result.exactness == "anchored"
    assert result.confidence == "medium"
    assert result.evidence_posture == "generic_with_uncertainty"
    assert len(result.manager_rounds) == 2
    assert provider.calls[1]["user_payload"]["tool_results"][0]["tool_name"] == "budget.get_today_summary"
    pass1_prompt_layer = result.trace["manager_rounds"][0]["prompt_layer_contract"]
    final_prompt_layer = result.trace["manager_rounds"][1]["prompt_layer_contract"]
    assert result.trace["react_trace"] == {
        "trace_schema_version": "manager_react_trace.v1",
        "manager_pass_count": 2,
        "manager_pass_1": {
            "round_index": 0,
            "stage": "intake_manager_round",
            "manager_action": "call_tools",
            "final_action": None,
            "workflow_effect": None,
            "tool_calls": [{"name": "budget.get_today_summary"}],
            "decision_payload": {"manager_action": "call_tools", "tool_calls": [{"name": "budget.get_today_summary"}]},
            "provider_trace": {"source": "fake", "call_index": 1},
            "prompt_registry": result.trace["prompt_registry"],
            "prompt_layer_contract": pass1_prompt_layer,
        },
        "manager_passes": [
            {
                "round_index": 0,
                "stage": "intake_manager_round",
                "manager_action": "call_tools",
                "final_action": None,
                "workflow_effect": None,
                "tool_names": ["budget.get_today_summary"],
            },
            {
                "round_index": 1,
                "stage": "intake_manager_round",
                "manager_action": "final",
                "final_action": "commit",
                "workflow_effect": "commit",
                "tool_names": [],
            },
        ],
        "requested_tools": ["budget.get_today_summary"],
        "executed_tools": ["budget.get_today_summary"],
        "manager_pass_final": {
            "round_index": 1,
            "stage": "intake_manager_round",
            "manager_action": "final",
            "final_action": "commit",
            "workflow_effect": "commit",
            "tool_calls": [],
            "decision_payload": {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "commit",
                "workflow_effect": "commit",
                "target_attachment": {"mode": "new_meal"},
                "exactness": "anchored",
                "confidence": "medium",
                "evidence_posture": "generic_with_uncertainty",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "generic_with_uncertainty",
            },
            "provider_trace": {"source": "fake", "call_index": 2},
            "prompt_registry": result.trace["prompt_registry"],
            "prompt_layer_contract": final_prompt_layer,
        },
        "guard_result": {},
        "request_failure_family": None,
    }


@pytest.mark.asyncio
async def test_run_intake_manager_forwards_product_policy_hints_as_payload_context() -> None:
    provider = FakeLoopProvider(
        [
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "no_commit",
                "workflow_effect": "safe_failure",
                "target_attachment": {"mode": "none"},
                "exactness": "unknown",
                "confidence": "low",
                "evidence_posture": "insufficient",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
            },
        ]
    )
    policy_hints = {
        "policy_source": "approved_nutrition_case_law",
        "rules": [{"policy_id": "self_selected_basket_without_listed_items"}],
    }

    await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="luwei",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("estimate_nutrition",),
        constraints={"manager_product_policy_hints": policy_hints},
    )

    assert provider.calls[0]["user_payload"]["manager_product_policy_hints"] == policy_hints


@pytest.mark.asyncio
async def test_run_intake_manager_forwards_manager_loop_scope_for_latency_attribution() -> None:
    provider = FakeLoopProvider(
        [
            {
                "manager_action": "final",
                "intent": "answer_remaining_budget",
                "final_action": "answer_only",
                "workflow_effect": "answer_only",
                "target_attachment": {"mode": "none"},
                "exactness": "unknown",
                "confidence": "medium",
                "evidence_posture": "read_only_state",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
            },
        ]
    )

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="How much have I eaten?",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("budget.get_today_summary",),
        manager_loop_scope="turn_entry_or_read_only",
    )

    assert provider.calls[0]["user_payload"]["manager_loop_scope"] == "turn_entry_or_read_only"
    assert result.trace["manager_rounds"][0]["manager_loop_scope"] == "turn_entry_or_read_only"
    assert result.trace["manager_rounds"][0]["phase_a_input"]["manager_loop_scope"] == "turn_entry_or_read_only"


@pytest.mark.asyncio
async def test_run_intake_manager_injects_entry_scope_route_policy() -> None:
    provider = FakeLoopProvider(
        [
            {
                "manager_action": "final",
                "intent": "answer_remaining_budget",
                "final_action": "answer_only",
                "workflow_effect": "answer_only",
                "target_attachment": {"mode": "none"},
                "exactness": "unknown",
                "confidence": "medium",
                "evidence_posture": "read_only_state",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
            },
        ]
    )

    await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="把湯拿掉",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("budget.get_today_summary",),
        manager_loop_scope="turn_entry_or_read_only",
    )

    policy = provider.calls[0]["user_payload"]["manager_scope_policy"]
    assert provider.calls[0]["user_payload"]["constraints"]["manager_loop_scope"] == "turn_entry_or_read_only"
    assert provider.calls[0]["user_payload"]["constraints"]["available_tools"] == ["budget.get_today_summary"]
    assert policy == {
        "policy_id": "manager_scope_policy.turn_entry_or_read_only.v1",
        "manager_loop_scope": "turn_entry_or_read_only",
        "available_tools": ["budget.get_today_summary"],
        "unavailable_intake_tools": [
            "compare_against_budget",
            "estimate_nutrition",
            "resolve_correction_target",
        ],
        "if_intake_execution_needed": {
            "manager_action": "final",
            "tool_calls": [],
            "intent_type": "log_meal",
            "final_action": "no_commit",
            "workflow_effect": "route_to_intake",
        },
        "deterministic_boundary": "runtime_validates_tool_scope_only_no_raw_text_semantic_routing",
    }


@pytest.mark.asyncio
async def test_run_intake_manager_uses_entry_scope_prompt_without_intake_resolution_rules() -> None:
    provider = FakeLoopProvider(
        [
            {
                "manager_action": "final",
                "intent": "log_meal",
                "intent_type": "log_meal",
                "final_action": "no_commit",
                "workflow_effect": "route_to_intake",
                "target_attachment": {"mode": "none"},
                "exactness": "unknown",
                "confidence": "medium",
                "evidence_posture": "requires_intake_execution",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
            },
        ]
    )

    await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="刪掉剛剛那個",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("budget.get_today_summary",),
        manager_loop_scope="turn_entry_or_read_only",
    )

    prompt = provider.calls[0]["system_prompt"]
    assert "Entry scope is classification, handoff, and read-only tool planning only." in prompt
    assert "Explicit remove_item correction is different" not in prompt
    assert "use target evidence from resolve_correction_target" not in prompt


@pytest.mark.asyncio
async def test_run_intake_manager_uses_intake_scope_prompt_with_resolution_rules() -> None:
    provider = FakeLoopProvider(
        [
            {
                "manager_action": "call_tools",
                "tool_calls": [{"name": "resolve_correction_target"}],
            },
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "correction_applied",
                "workflow_effect": "correction_applied",
                "target_attachment": {"mode": "existing_meal"},
                "exactness": "anchored",
                "confidence": "medium",
                "evidence_posture": "target_evidence_present",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
            },
        ]
    )

    async def tool_executor(*, tool_calls: list[dict[str, object]], **_: object) -> list[dict[str, object]]:
        return [{"tool_name": item["name"], "evidence": {"target": "latest_meal"}} for item in tool_calls]

    await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="刪掉剛剛那個",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("resolve_correction_target",),
        manager_loop_scope="intake_execution",
        tool_executor=tool_executor,
    )

    prompt = provider.calls[0]["system_prompt"]
    assert "Explicit remove_item correction is different" in prompt
    assert "use target evidence from resolve_correction_target" in prompt


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("available_tools", "expected_scope"),
    [
        (("budget.get_today_summary",), "turn_entry_or_read_only"),
        (("body.record_observation",), "body_observation"),
        (("estimate_nutrition", "compare_against_budget"), "intake_execution"),
    ],
)
async def test_run_intake_manager_infers_latency_scope_from_tool_surface(
    available_tools: tuple[str, ...],
    expected_scope: str,
) -> None:
    provider = FakeLoopProvider(
        [
            {
                "manager_action": "final",
                "intent": "answer_remaining_budget",
                "final_action": "answer_only",
                "workflow_effect": "answer_only",
                "target_attachment": {"mode": "none"},
                "exactness": "unknown",
                "confidence": "medium",
                "evidence_posture": "read_only_state",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
            },
        ]
    )

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="How much have I eaten?",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=available_tools,
    )

    assert provider.calls[0]["user_payload"]["manager_loop_scope"] == expected_scope
    assert result.trace["manager_rounds"][0]["manager_loop_scope"] == expected_scope


@pytest.mark.asyncio
async def test_run_intake_manager_keeps_prompt_registry_in_trace_only() -> None:
    provider = FakeLoopProvider(
        [
            {
                "manager_action": "final",
                "intent": "general_chat",
                "intent_type": "general_chat",
                "final_action": "answer_only",
                "workflow_effect": "answer_only",
                "target_attachment": {"mode": "none"},
                "exactness": "unknown",
                "confidence": "low",
                "evidence_posture": "none",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
            }
        ]
    )

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="today",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("budget.get_today_summary", "body.get_latest_observation"),
        constraints={
            "manager_contract_schema_version": "v1",
            "manager_contract_provider_profile_id": "builderspace-grok-4-fast-founder-live-contract",
            "manager_contract_provider_profile_transport_mode": "structured_outputs",
        },
    )

    assert "manager_prompt_registry" not in provider.calls[0]["user_payload"]
    registry = result.trace["prompt_registry"]
    assert registry == {
        "registry_version": "manager_prompt_registry.v1",
        "manager_loop_stage": "intake_manager_round",
        "system_prompt_id": "single_manager_system_prompt",
        "system_prompt_version": "v6",
        "model_prompt_contract_id": "single_manager_user_payload_contract",
        "model_prompt_contract_version": "v1",
        "tool_surface_version": "current_shell_public_tools.v1",
        "output_schema_name": "manager_loop_schema",
        "output_schema_version": "v1",
        "provider": "fake_provider",
        "manager_model": "fake-model",
        "model_profile_overlay_id": "builderspace-grok-4-fast-founder-live-contract",
        "model_profile_overlay_transport_mode": "structured_outputs",
    }
    assert result.manager_rounds[0]["prompt_registry"] == registry


@pytest.mark.asyncio
async def test_run_intake_manager_records_prompt_layer_contract_trace_only() -> None:
    provider = FakeLoopProvider(
        [
            {
                "manager_action": "final",
                "intent": "general_chat",
                "intent_type": "general_chat",
                "final_action": "answer_only",
                "workflow_effect": "answer_only",
                "target_attachment": {"mode": "none"},
                "exactness": "unknown",
                "confidence": "low",
                "evidence_posture": "none",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
            }
        ]
    )

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="today",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("budget.get_today_summary", "body.get_latest_observation"),
        manager_loop_scope="turn_entry_or_read_only",
    )

    assert "prompt_layer_contract" not in provider.calls[0]["user_payload"]
    layer = result.manager_rounds[0]["prompt_layer_contract"]
    assert layer["contract_version"] == "manager_prompt_layer_contract.v1"
    assert layer["manager_loop_scope"] == "turn_entry_or_read_only"
    assert layer["system_prompt_layer"] == "static_prefix"
    assert layer["runtime_payload_layer"] == "dynamic_suffix"
    assert layer["provider_profile_layer"] == "transport_overlay_trace_only"
    assert layer["prompt_cache_profile"]["static_prefix_first"] is True
    assert layer["prompt_cache_profile"]["dynamic_context_last"] is True
    assert layer["prompt_cache_profile"]["cache_metric_field"] == "usage.*.cached_tokens"
    assert layer["dynamic_payload_keys"] == sorted(provider.calls[0]["user_payload"])
    assert result.trace["react_trace"]["manager_pass_1"]["prompt_layer_contract"] == layer


@pytest.mark.asyncio
async def test_run_intake_manager_stably_normalizes_available_tools_in_user_payload() -> None:
    provider = FakeLoopProvider(
        [
            {
                "manager_action": "final",
                "intent": "general_chat",
                "intent_type": "general_chat",
                "final_action": "answer_only",
                "workflow_effect": "answer_only",
                "target_attachment": {"mode": "none"},
                "exactness": "unknown",
                "confidence": "low",
                "evidence_posture": "none",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
            }
        ]
    )

    await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="today",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("budget.get_today_summary", "body.get_latest_observation", "budget.get_today_summary"),
    )

    assert provider.calls[0]["user_payload"]["available_tools"] == [
        "body.get_latest_observation",
        "budget.get_today_summary",
    ]


@pytest.mark.asyncio
async def test_run_intake_manager_clears_guard_repair_constraints_after_tool_call() -> None:
    provider = FakeLoopProvider(
        [
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "commit",
                "workflow_effect": "commit",
                "target_attachment": {"mode": "new_meal"},
                "exactness": "estimated",
                "confidence": "medium",
                "evidence_posture": "requires_nutrition_estimate",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "pending",
            },
            {
                "manager_action": "call_tools",
                "tool_calls": [{"name": "estimate_nutrition", "arguments": {}}],
            },
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "commit",
                "workflow_effect": "commit",
                "target_attachment": {"mode": "new_meal"},
                "exactness": "estimated",
                "confidence": "medium",
                "evidence_posture": "tool_estimated",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "tool_estimated",
            },
        ]
    )

    async def tool_executor(**_: object) -> list[dict[str, object]]:
        return [{"tool_name": "estimate_nutrition", "evidence": {"nutrition_payload": {"estimated_kcal": 80}}, "failure_family": None}]

    async def guard_checker(**kwargs: object) -> dict[str, object]:
        tool_results = kwargs.get("tool_results")
        if not isinstance(tool_results, list) or not tool_results:
            return {
                "ok": False,
                "repair_request": True,
                "failure_family": "commit_without_evidence",
                "phase_a_transition_guard_preflight": {"blocked": True},
            }
        return {"ok": True, "phase_a_transition_guard_preflight": {"blocked": False}}

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="tea egg",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("estimate_nutrition",),
        tool_executor=tool_executor,
        guard_checker=guard_checker,
        constraints={"request_id": "req-test"},
    )

    assert result.final_action == "commit"
    assert result.repair_round_used is True
    assert provider.calls[1]["user_payload"]["constraints"]["guard_feedback_failure_family"] == "commit_without_evidence"
    assert "guard_feedback_failure_family" not in provider.calls[2]["user_payload"]["constraints"]


@pytest.mark.asyncio
async def test_run_intake_manager_max_rounds_is_hard_failure() -> None:
    provider = FakeLoopProvider([])

    async def tool_executor(**_: object) -> list[dict[str, object]]:
        return [{"tool_name": "budget.get_today_summary", "evidence": {}, "failure_family": None}]

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="loop",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("budget.get_today_summary",),
        tool_executor=tool_executor,
    )

    assert result.final_action == "no_commit"
    assert result.intent == "manager_unavailable"
    assert result.intent_type == "manager_unavailable"
    assert result.workflow_effect == "safe_failure"
    assert result.request_failure_family == "max_rounds_exceeded"
    assert len(result.manager_rounds) == manager_service.MAX_MANAGER_ROUNDS
    assert result.trace["react_trace"]["request_failure_family"] == "max_rounds_exceeded"
    assert result.trace["react_trace"]["manager_pass_count"] == manager_service.MAX_MANAGER_ROUNDS
    assert len(result.trace["react_trace"]["manager_passes"]) == manager_service.MAX_MANAGER_ROUNDS
    assert result.trace["react_trace"]["manager_pass_1"]["round_index"] == result.trace["react_trace"]["manager_passes"][0]["round_index"]
    assert (
        result.trace["react_trace"]["manager_pass_final"]["round_index"]
        == result.trace["react_trace"]["manager_passes"][-1]["round_index"]
    )


@pytest.mark.asyncio
async def test_run_intake_manager_routes_entry_scope_intake_tool_to_execution_without_executor_loop() -> None:
    provider = FakeLoopProvider(
        [
            {
                "manager_action": "call_tools",
                "intent": "correct_meal",
                "intent_type": "log_meal",
                "workflow_effect": "correction",
                "target_attachment": {"operation": "remove_item"},
                "final_action": "correction_applied",
                "tool_calls": [{"name": "resolve_correction_target", "arguments": {}}],
                "semantic_decision": {
                    "semantic_authority": "manager_llm",
                    "current_turn_intent": "correct_meal",
                    "target_attachment": {"operation": "remove_item"},
                    "workflow_effect": "correction",
                    "final_action_candidate": "correction_applied",
                    "estimation_posture": "target_evidence_needed",
                    "followup_posture": "none",
                    "mutation_intent_candidate": "correction_write",
                    "uncertainty_posture": "pending_tool",
                    "source": "manager_structured_output",
                },
            }
        ]
    )
    executor_called = False

    async def tool_executor(**_: object) -> list[dict[str, object]]:
        nonlocal executor_called
        executor_called = True
        return [{"tool_name": "resolve_correction_target", "evidence": {}, "failure_family": None}]

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="remove that",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("budget.get_day_meal_log",),
        tool_executor=tool_executor,
    )

    assert executor_called is False
    assert len(result.manager_rounds) == 1
    assert result.intent_type == "log_meal"
    assert result.final_action == "no_commit"
    assert result.workflow_effect == "route_to_intake"
    assert result.semantic_decision["workflow_effect"] == "correction"
    assert result.request_failure_family is None
    assert result.tool_results == (
        {
            "handoff_family": "entry_scope_requested_intake_tool",
            "requested_tools": ["resolve_correction_target"],
            "available_tools": ["budget.get_day_meal_log"],
            "target_scope": "intake_execution",
            "mutation_result": {"state_mutation": "none"},
            "confidence": "bounded_handoff",
        },
    )


@pytest.mark.asyncio
async def test_run_intake_manager_blocks_unknown_unavailable_tool_before_executor_loop() -> None:
    provider = FakeLoopProvider(
        [
            {
                "manager_action": "call_tools",
                "tool_calls": [{"name": "unapproved.lookup", "arguments": {}}],
            }
        ]
    )
    executor_called = False

    async def tool_executor(**_: object) -> list[dict[str, object]]:
        nonlocal executor_called
        executor_called = True
        return [{"tool_name": "unapproved.lookup", "evidence": {}, "failure_family": None}]

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="look this up",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("budget.get_day_meal_log",),
        tool_executor=tool_executor,
    )

    assert executor_called is False
    assert len(result.manager_rounds) == 1
    assert result.intent_type == "manager_unavailable"
    assert result.final_action == "no_commit"
    assert result.workflow_effect == "safe_failure"
    assert result.request_failure_family == "tool_not_available"
    assert result.tool_results == (
        {
            "failure_family": "tool_not_available",
            "requested_tools": ["unapproved.lookup"],
            "available_tools": ["budget.get_day_meal_log"],
            "mutation_result": {"state_mutation": "none"},
            "confidence": "none",
        },
    )


@pytest.mark.asyncio
async def test_run_intake_manager_malformed_final_target_attachment_returns_safe_failure_not_raw_crash() -> None:
    provider = FakeLoopProvider(
        [
            {"manager_action": "call_tools", "tool_calls": [{"name": "budget.get_today_summary"}]},
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "commit",
                "workflow_effect": "commit",
                "target_attachment": ["bad-shape"],
                "exactness": "anchored",
                "confidence": "medium",
                "evidence_posture": "generic_with_uncertainty",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "generic_with_uncertainty",
            },
        ]
    )

    async def tool_executor(**_: object) -> list[dict[str, object]]:
        return [{"tool_name": "budget.get_today_summary", "evidence": {"remaining_kcal": 1200}, "failure_family": None}]

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="我吃了一杯珍珠奶茶",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("budget.get_today_summary",),
        tool_executor=tool_executor,
    )

    assert result.final_action == "no_commit"
    assert result.intent == "manager_unavailable"
    assert result.intent_type == "manager_unavailable"
    assert result.workflow_effect == "safe_failure"
    assert result.request_failure_family == "final_payload_shape_error"
    assert result.trace["request_failure_family"] == "final_payload_shape_error"
    assert result.trace["payload_shape_error"]["field_name"] == "target_attachment"
    assert result.trace["payload_shape_error"]["observed_type"] == "array"
