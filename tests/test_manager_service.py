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
    assert "exactness, confidence, evidence_posture, repair_ack" in content
    assert "thoughts" not in content


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
