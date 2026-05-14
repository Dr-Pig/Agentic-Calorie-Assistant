from types import SimpleNamespace
from pathlib import Path

import pytest

from app.runtime.application import manager_service
from app.runtime.agent.manager_payload_utils import compact_tool_results_prompt_payload, stable_available_tools
from app.runtime.agent.manager_context_payload import (
    current_turn_context_prompt_payload,
    manager_context_pack_prompt_payload,
    manager_context_packet_v1_prompt_payload,
)


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
    assert "common commercial drink" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "self-selected mixed basket" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "listed items after a basket clarification" in SINGLE_MANAGER_SYSTEM_PROMPT
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
    assert "intent_type='correct_meal' for correction/refinement" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_single_manager_system_prompt_keeps_estimate_explanation_queries_read_only() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT

    assert "asks how an existing meal was estimated" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "intent_type='answer_query'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "mutation_intent_candidate='no_mutation'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "answer_contract.answer_basis" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "active meal basis snapshot supplied in the current context payload" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "Do not route estimate-basis inquiries to intake execution" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "Do not treat questions like how/why you estimated it or what you assumed as correction/refinement" in (
        SINGLE_MANAGER_SYSTEM_PROMPT
    )


def test_single_manager_system_prompt_keeps_user_replies_free_of_internal_estimate_labels() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT

    assert "do not expose internal labels such as LLM, llm_only" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "macro visibility is not explicit" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "say macro data is insufficient instead of listing protein/carbs/fat grams" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_single_manager_system_prompt_keeps_no_plan_budget_queries_read_only() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT

    assert "No-plan budget/status/setup-required questions are read-only answer surfaces" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "not intake execution" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "intent_type='answer_remaining_budget'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "final_action='onboarding_required'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "onboarding_required is the final_action, not the intent_type" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "workflow_effect='answer_only'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "mutation_intent_candidate='no_mutation'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "do not use workflow_effect='route_to_intake'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "do not describe missing target or remaining budget as 0" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_single_manager_system_prompt_preserves_write_intent_for_committable_optional_refinement() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT

    assert "For entry-scope committable food or drink handoffs" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "final_action_candidate='commit'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "mutation_intent_candidate='canonical_write'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "optional refinement follow-up does not make the mutation intent no_mutation" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "Do not pair final_action_candidate='commit' with mutation_intent_candidate='no_mutation'" in (
        SINGLE_MANAGER_SYSTEM_PROMPT
    )


def test_single_manager_system_prompt_is_static_prefix_across_scopes() -> None:
    from app.runtime.agent.manager_system_prompt import single_manager_system_prompt_for_scope

    entry_prompt = single_manager_system_prompt_for_scope("turn_entry_or_read_only")
    intake_prompt = single_manager_system_prompt_for_scope("intake_execution")

    assert entry_prompt == intake_prompt
    assert "Follow user_payload.manager_scope_policy" in entry_prompt
    assert "Scope policy has priority over evidence and target-resolution rules" in entry_prompt


def test_stable_available_tools_normalizes_order_and_deduplicates() -> None:
    assert stable_available_tools(
        ("budget.get_today_summary", "body.get_latest_observation", "budget.get_today_summary")
    ) == ("body.get_latest_observation", "budget.get_today_summary")


def test_compact_tool_results_preserves_latest_weight_read_model_evidence() -> None:
    compact = compact_tool_results_prompt_payload(
        [
            {
                "tool_name": "body.get_latest_observation",
                "evidence": {
                    "latest_weight_status": "available",
                    "latest_weight_observation": {
                        "observation_id": 2,
                        "value": 70.4,
                        "unit": "kg",
                        "local_date": "2026-05-10",
                        "observed_at": "2026-05-10T06:02:50",
                        "debug_blob": "x" * 1000,
                    },
                },
                "provenance": {
                    "canonical_tool_name": "body.get_latest_observation",
                    "truth_owner": "body_domain",
                    "tool_kind": "read_only",
                    "mutation_authority": False,
                },
                "confidence": "available",
                "failure_family": None,
            }
        ]
    )

    evidence = compact[0]["evidence"]
    assert evidence["latest_weight_status"] == "available"
    assert evidence["latest_weight_observation"] == {
        "observation_id": 2,
        "value": 70.4,
        "unit": "kg",
        "local_date": "2026-05-10",
    }
    assert "debug_blob" not in str(compact)
    assert "observed_at" not in str(compact)


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
    react_trace = result.trace["react_trace"]
    assert react_trace["manager_round_count"] == 2
    assert react_trace["manager_round_latency_ms"] == [
        pytest.approx(react_trace["manager_pass_1"]["latency_ms"]),
        pytest.approx(react_trace["manager_pass_final"]["latency_ms"]),
    ]
    assert react_trace["manager_pass_1"]["latency_ms"] >= 0
    assert react_trace["manager_pass_final"]["latency_ms"] >= 0
    assert react_trace["tool_batch_latency_ms"] >= 0
    assert react_trace["guard_latency_ms"] == 0
    assert react_trace["orchestration_latency_ms"] >= 0
    assert react_trace["tool_call_count"] == 1
    assert react_trace["repair_round_used"] is False
    assert react_trace["total_latency_ms"] >= (
        sum(react_trace["manager_round_latency_ms"])
        + react_trace["tool_batch_latency_ms"]
        + react_trace["guard_latency_ms"]
    )
    assert react_trace["call_topology"] == [
        {
            "operation": "manager_provider_round",
            "stage": "intake_manager_round",
            "round_index": 0,
            "duration_ms": pytest.approx(react_trace["manager_pass_1"]["latency_ms"]),
        },
        {
            "operation": "tool_batch",
            "stage": "manager_tool_execution",
            "round_index": 0,
            "duration_ms": pytest.approx(react_trace["tool_batch_latency_ms"]),
            "tool_names": ["budget.get_today_summary"],
            "tool_count": 1,
        },
        {
            "operation": "manager_provider_round",
            "stage": "intake_manager_round",
            "round_index": 1,
            "duration_ms": pytest.approx(react_trace["manager_pass_final"]["latency_ms"]),
        },
    ]
    dynamic_observability_fields = {
        "manager_round_count",
        "manager_round_latency_ms",
        "tool_batch_latency_ms",
        "guard_latency_ms",
        "total_latency_ms",
        "orchestration_latency_ms",
        "tool_call_count",
        "repair_round_used",
        "call_topology",
    }
    static_trace = {key: value for key, value in react_trace.items() if key not in dynamic_observability_fields}
    assert static_trace == {
        "trace_schema_version": "manager_react_trace.v1",
        "manager_pass_count": 2,
        "manager_pass_1": {
            "round_index": 0,
            "stage": "intake_manager_round",
            "latency_ms": react_trace["manager_pass_1"]["latency_ms"],
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
                "latency_ms": react_trace["manager_pass_1"]["latency_ms"],
                "manager_action": "call_tools",
                "final_action": None,
                "workflow_effect": None,
                "tool_names": ["budget.get_today_summary"],
            },
            {
                "round_index": 1,
                "stage": "intake_manager_round",
                "latency_ms": react_trace["manager_pass_final"]["latency_ms"],
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
            "latency_ms": react_trace["manager_pass_final"]["latency_ms"],
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

    hint_payload = provider.calls[0]["user_payload"]["manager_product_policy_hints"]
    assert hint_payload["prompt_payload_kind"] == "manager_product_policy_hints_compact_summary"
    assert hint_payload["policy_source"] == "approved_nutrition_case_law"
    assert hint_payload["policy_ids"] == ["self_selected_basket_without_listed_items"]
    assert hint_payload["full_policy_text_omitted_from_prompt"] is True
    assert "manager_behavior" not in str(hint_payload)
    assert "manager_product_policy_hints" not in provider.calls[0]["user_payload"]["constraints"]


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
            "intent_type_options": {
                "new_meal": "log_meal",
                "correction_or_refinement": "correct_meal",
            },
            "final_action": "no_commit",
            "workflow_effect": "route_to_intake",
        },
        "context_packet_read_only_flags": "context_evidence_only_not_current_turn_mutation_intent",
        "deterministic_boundary": "runtime_validates_tool_scope_only_no_raw_text_semantic_routing",
    }


@pytest.mark.asyncio
async def test_run_intake_manager_uses_static_prompt_and_dynamic_entry_scope_policy() -> None:
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
    policy = provider.calls[0]["user_payload"]["manager_scope_policy"]
    assert "Entry scope is classification, handoff, and read-only tool planning only." in prompt
    assert "Explicit remove_item correction is different" in prompt
    assert "use target evidence from resolve_correction_target" in prompt
    assert "context packet read_only" in prompt
    assert "after an estimate-basis inquiry" in prompt
    assert "do not ask for replacement confirmation" in prompt
    assert policy["manager_loop_scope"] == "turn_entry_or_read_only"
    assert policy["if_intake_execution_needed"]["workflow_effect"] == "route_to_intake"
    assert policy["if_intake_execution_needed"]["intent_type_options"]["correction_or_refinement"] == "correct_meal"
    assert policy["context_packet_read_only_flags"] == "context_evidence_only_not_current_turn_mutation_intent"


@pytest.mark.asyncio
async def test_run_intake_manager_uses_same_static_prompt_with_intake_scope_policy() -> None:
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
    policy = provider.calls[0]["user_payload"]["manager_scope_policy"]
    assert "Explicit remove_item correction is different" in prompt
    assert "use target evidence from resolve_correction_target" in prompt
    assert policy["manager_loop_scope"] == "intake_execution"


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
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT_VERSION

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
        "system_prompt_version": SINGLE_MANAGER_SYSTEM_PROMPT_VERSION,
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
    assert layer["prompt_cache_identity"] == {
        "identity_version": "manager_prompt_cache_identity.v1",
        "stable_prefix_sha256": layer["system_contract"]["stable_prefix_sha256"],
        "dynamic_suffix_sha256": layer["prompt_cache_identity"]["dynamic_suffix_sha256"],
        "stable_prefix_component_order": ["system_prompt"],
        "stable_prefix_section_order": layer["system_contract"]["section_order"],
        "dynamic_suffix_component_order": ["runtime_user_payload"],
        "provider_overlay_hash_source": "provider_trace.prompt_cache_request",
        "cache_truth_source": "provider_reported_usage_only",
        "provider_usage_is_cache_truth": True,
    }
    assert layer["dynamic_payload_keys"] == sorted(provider.calls[0]["user_payload"])
    assert layer["system_contract"]["owner"] == "ManagerRuntime"
    assert layer["system_contract"]["prompt_id"] == "single_manager_system_prompt"
    assert layer["system_contract"]["section_manifest_version"] == "single_manager_system_prompt_sections.v1"
    assert layer["system_contract"]["section_order"] == [
        "base_manager_role_and_react_loop",
        "product_policy_guidance",
        "runtime_contract_policy",
        "scope_boundary_policy",
        "user_facing_reply_policy",
    ]
    assert set(layer["system_contract"]["section_sha256"]) == set(layer["system_contract"]["section_order"])
    assert [
        section["section_id"]
        for section in layer["system_contract"]["sections"]
    ] == layer["system_contract"]["section_order"]
    assert all(section["provider_overlay_allowed"] is False for section in layer["system_contract"]["sections"])
    assert all(section["layer"] == "static_prefix" for section in layer["system_contract"]["sections"])
    assert layer["provider_overlay_contract"] == {
        "owner": "ProviderAdapter",
        "trace_only": True,
        "may_set_model": True,
        "may_set_transport": True,
        "may_change_system_contract": False,
        "may_change_system_prompt_sections": False,
        "may_inject_product_semantics": False,
    }
    assert layer["runtime_payload_layer_plan"]["uncategorized_dynamic_keys"] == []
    sections = {
        section["section_id"]: section
        for section in layer["runtime_payload_layer_plan"]["sections"]
    }
    assert "phase_a_current_turn_context" in sections["context_engineering"]["keys"]
    assert "manager_context_packet_v1" in sections["context_engineering"]["keys"]
    assert "tool_results" in sections["tool_evidence"]["keys"]
    assert "constraints" in sections["contract_constraints"]["keys"]
    footprint = layer["prompt_footprint"]
    assert footprint["measurement"] == "json_utf8_bytes_trace_only"
    assert footprint["provider_usage_is_token_truth"] is True
    assert footprint["system_prompt_utf8_bytes"] > 0
    assert footprint["dynamic_payload_total_utf8_bytes"] > 0
    assert footprint["largest_dynamic_section_id"] in sections
    context_footprint = {
        section["section_id"]: section
        for section in footprint["dynamic_sections"]
    }["context_engineering"]
    assert context_footprint["utf8_bytes"] >= 0
    assert context_footprint["key_count"] == len(sections["context_engineering"]["keys"])
    key_footprints = {
        item["key"]: item
        for item in context_footprint["key_footprints"]
    }
    assert set(key_footprints) == set(sections["context_engineering"]["keys"])
    assert key_footprints["manager_context_packet_v1"]["utf8_bytes"] >= 0
    assert context_footprint["largest_key"] in key_footprints
    assert footprint["largest_dynamic_key"]["section_id"] in sections
    assert footprint["largest_dynamic_key"]["key"]
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


def test_manager_context_packet_prompt_omits_duplicate_interaction_raw_text() -> None:
    packet = {
        "metadata": {
            "local_date": "2026-05-02",
            "context_policy_version": "accurate_intake_mvp_context_policy_v1",
            "claim_scope": "current_session_current_day_manager_input_evidence",
        },
        "current_turn": {
            "raw_user_input": "remove this",
            "channel": "web_shell",
            "manager_mode": "fixture",
            "interaction_event": {
                "source": "web",
                "surface_mode": "today_diary",
                "event_type": "quick_action",
                "raw_text": "remove this",
                "target_object_type": "meal_item",
                "target_object_id": "item-42",
                "read_only": True,
                "mutation_authority": False,
            },
        },
        "context_loading_artifact": {
            "loaded_message_count": 0,
            "omitted_count": 0,
            "char_truncated": False,
            "token_budget_status": "within_budget",
        },
        "recent_chat_window": {"messages": []},
        "hard_pins": {},
        "active_day_state": {},
        "target_candidates": {},
        "constraints": [],
    }

    payload = manager_context_packet_v1_prompt_payload(packet)

    interaction_event = payload["current_turn"]["interaction_event"]
    assert "raw_text" not in interaction_event
    assert "raw_text_omitted_from_prompt" not in interaction_event
    assert "raw_text_source" not in interaction_event
    assert interaction_event["target_object_type"] == "meal_item"
    assert interaction_event["target_object_id"] == "item-42"


def test_primary_context_packet_omits_legacy_lineage_prompt_payloads() -> None:
    class UnexpectedLegacyPayload:
        def model_dump(self, **_: object) -> dict[str, object]:
            raise AssertionError("primary packet prompt should not serialize legacy current-turn context")

        def __getattr__(self, name: str) -> object:
            raise AssertionError(f"primary packet prompt should not read legacy pack field {name}")

    legacy_payload = UnexpectedLegacyPayload()

    assert current_turn_context_prompt_payload(legacy_payload, primary_packet_present=True) is None
    assert manager_context_pack_prompt_payload(legacy_payload, primary_packet_present=True) is None


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
    react_trace = result.trace["react_trace"]
    assert react_trace["repair_round_used"] is True
    assert react_trace["guard_latency_ms"] >= 0
    assert [event["operation"] for event in react_trace["call_topology"]] == [
        "manager_provider_round",
        "guard_check",
        "manager_provider_round",
        "tool_batch",
        "manager_provider_round",
        "guard_check",
    ]
    guard_events = [event for event in react_trace["call_topology"] if event["operation"] == "guard_check"]
    assert guard_events[0]["guard_ok"] is False
    assert guard_events[0]["failure_family"] == "commit_without_evidence"
    assert guard_events[1]["guard_ok"] is True


@pytest.mark.asyncio
async def test_run_intake_manager_sends_compact_tool_results_to_provider_only() -> None:
    provider = FakeLoopProvider(
        [
            {"manager_action": "call_tools", "tool_calls": [{"name": "estimate_nutrition", "arguments": {}}]},
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
    full_tool_result = {
        "tool_name": "estimate_nutrition",
        "evidence": {
            "nutrition_payload": {
                "meal_title": "milk tea",
                "estimated_kcal": 520,
                "reply_text": "logged",
                "trace_contract": {
                    "canonical_write_decision": {"can_write_canonical": True},
                    "db_hit_type": "generic",
                    "web_runtime_trace": {"debug_blob": "x" * 10_000},
                    "raw_candidates": ["not prompt input"] * 50,
                },
            }
        },
        "provenance": {
            "canonical_tool_name": "estimate_nutrition",
            "truth_owner": "nutrition_evidence_packet",
            "tool_kind": "read_only",
            "mutation_authority": False,
            "correction_target": {"canonical_name": "milk tea", "debug_blob": "x" * 10_000},
            "budget_summary": {"predicted_remaining_kcal_after": 900, "debug_blob": "x" * 10_000},
            "macro_summary": {"show_macro": False, "macro_guard_reason": "hidden_missing_source"},
            "evidence_summary": {"eligibility": "generic", "candidate_count": 1},
        },
        "confidence": "available",
        "failure_family": None,
    }

    async def tool_executor(**_: object) -> list[dict[str, object]]:
        return [full_tool_result]

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="milk tea",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("estimate_nutrition",),
        tool_executor=tool_executor,
        constraints={"request_id": "req-compact-tool-result"},
    )

    prompt_tool_result = provider.calls[1]["user_payload"]["tool_results"][0]
    prompt_nutrition = prompt_tool_result["evidence"]["nutrition_payload"]
    prompt_provenance = prompt_tool_result["provenance"]
    assert prompt_tool_result["prompt_payload_kind"] == "manager_tool_result_prompt_compact"
    assert prompt_nutrition["estimated_kcal"] == 520
    assert prompt_provenance["canonical_tool_name"] == "estimate_nutrition"
    assert prompt_provenance["truth_owner"] == "nutrition_evidence_packet"
    assert prompt_provenance["tool_kind"] == "read_only"
    assert prompt_provenance["mutation_authority"] is False
    assert prompt_nutrition["trace_contract"] == {
        "db_hit_type": "generic",
        "canonical_write_decision": {"can_write_canonical": True},
    }
    assert "web_runtime_trace" not in str(prompt_tool_result)
    assert "raw_candidates" not in str(prompt_tool_result)
    assert "debug_blob" not in str(prompt_tool_result)
    assert result.tool_results[0]["evidence"]["nutrition_payload"]["trace_contract"]["web_runtime_trace"]["debug_blob"]


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
