from types import SimpleNamespace
from pathlib import Path

import pytest

from app.runtime.application import manager_service


def test_manager_service_exposes_single_entrypoint_and_bounded_rounds() -> None:
    assert hasattr(manager_service, "run_intake_manager")
    assert manager_service.MAX_MANAGER_ROUNDS == 3


def test_manager_service_has_no_step_specific_entrypoints() -> None:
    source = manager_service.__file__
    with open(source, "r", encoding="utf-8") as handle:
        content = handle.read()

    assert "decide_" + "bundle1_turn" not in content
    assert "decide_" + "bundle2_step1" not in content
    assert "decide_" + "bundle2_step2" not in content


def test_single_manager_entrypoint_has_no_bundle_specific_modes() -> None:
    source = manager_service.__file__
    with open(source, "r", encoding="utf-8") as handle:
        content = handle.read()

    assert "bundle2" + "_round_1" not in content
    assert "bundle2" + "_final" not in content


def test_single_manager_system_prompt_requires_semantic_contract_not_reasoning_dump() -> None:
    source = Path(manager_service.__file__).resolve().parents[1] / "agent" / "manager.py"
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


class FakeLoopProvider:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def readiness(self) -> dict[str, object]:
        return {"configured": True}

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        if not self.responses:
            return {"manager_action": "call_tools", "tool_calls": [{"name": "read_day_budget"}]}, {"source": "fake"}
        return self.responses.pop(0), {"source": "fake", "call_index": len(self.calls)}


@pytest.mark.asyncio
async def test_run_intake_manager_executes_tools_and_feeds_results_into_next_round() -> None:
    provider = FakeLoopProvider(
        [
            {"manager_action": "call_tools", "tool_calls": [{"name": "read_day_budget"}]},
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
    tool_calls: list[list[dict[str, object]]] = []

    async def tool_executor(*, tool_calls: list[dict[str, object]], **_: object) -> list[dict[str, object]]:
        tool_calls_copy = [dict(item) for item in tool_calls]
        tool_calls.append({"name": "sentinel"})  # mutate caller copy if implementation leaks it
        return [{"tool_name": item["name"], "evidence": {"remaining_kcal": 1200}, "failure_family": None} for item in tool_calls_copy]

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="今天還剩多少熱量",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("read_day_budget",),
        tool_executor=tool_executor,
    )

    assert result.final_action == "commit"
    assert result.request_failure_family is None
    assert result.intent == "log_meal"
    assert result.exactness == "anchored"
    assert result.confidence == "medium"
    assert result.evidence_posture == "generic_with_uncertainty"
    assert len(result.manager_rounds) == 2
    assert provider.calls[1]["user_payload"]["tool_results"][0]["tool_name"] == "read_day_budget"


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
        "policy_source": "approved_b2_case_law",
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
        return [{"tool_name": "read_day_budget", "evidence": {}, "failure_family": None}]

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="loop",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("read_day_budget",),
        tool_executor=tool_executor,
    )

    assert result.final_action == "no_commit"
    assert result.request_failure_family == "max_rounds_exceeded"
    assert len(result.manager_rounds) == manager_service.MAX_MANAGER_ROUNDS


@pytest.mark.asyncio
async def test_run_intake_manager_malformed_final_target_attachment_returns_safe_failure_not_raw_crash() -> None:
    provider = FakeLoopProvider(
        [
            {"manager_action": "call_tools", "tool_calls": [{"name": "read_day_budget"}]},
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
        return [{"tool_name": "read_day_budget", "evidence": {"remaining_kcal": 1200}, "failure_family": None}]

    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="我吃了一杯珍珠奶茶",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("read_day_budget",),
        tool_executor=tool_executor,
    )

    assert result.final_action == "no_commit"
    assert result.workflow_effect == "safe_failure"
    assert result.request_failure_family == "final_payload_shape_error"
    assert result.trace["request_failure_family"] == "final_payload_shape_error"
    assert result.trace["payload_shape_error"]["field_name"] == "target_attachment"
    assert result.trace["payload_shape_error"]["observed_type"] == "array"
