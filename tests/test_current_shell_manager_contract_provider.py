from __future__ import annotations

import importlib
from typing import Any

import pytest

from app.runtime.contracts.trace import MANAGER_LOOP_STAGE


class _CapturingProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "builderspace",
            "configured": True,
            "manager_model": "grok-4-fast",
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        self.calls.append(kwargs)
        return (
            {
                "manager_action": "final",
                "intent": "log_meal",
                "intent_type": "log_meal",
                "tool_calls": [],
                "workflow_effect": "answer_only",
                "target_attachment": {},
                "final_action": "answer_only",
                "exactness": "unknown",
                "confidence": "low",
                "evidence_posture": "none",
                "semantic_decision": {},
                "answer_contract": {},
            },
            {"stage": kwargs.get("stage")},
        )


@pytest.mark.asyncio
async def test_current_shell_manager_provider_injects_structured_contract_constraints_for_manager_round() -> None:
    from app.runtime.interface.current_shell_manager_provider import (
        CurrentShellManagerContractProvider,
        current_shell_manager_provider_profile,
    )

    inner = _CapturingProvider()
    provider = CurrentShellManagerContractProvider(
        inner,
        profile=current_shell_manager_provider_profile(),
    )

    payload, trace = await provider.complete_with_trace(
        system_prompt="Return JSON.",
        user_payload={
            "constraints": {"request_id": "req-1"},
            "tool_results": [
                {
                    "tool_name": "estimate_nutrition",
                    "evidence": {"nutrition_payload": {"estimated_kcal": 180}},
                }
            ],
        },
        stage=MANAGER_LOOP_STAGE,
        max_tokens=900,
    )

    constraints = inner.calls[0]["user_payload"]["constraints"]
    assert payload["manager_action"] == "final"
    assert constraints["request_id"] == "req-1"
    assert constraints["manager_contract_schema_name"] == "founder_live_manager_contract"
    assert constraints["manager_contract_schema_version"] == "v1"
    assert constraints["manager_contract_transport_policy"] == "synthetic_tool_transport"
    assert constraints["manager_contract_provider_profile_id"] == (
        "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic"
    )
    assert constraints["manager_contract_evidence_state"]["nutrition_evidence_present"] is True
    assert trace["provider_profile_id"] == "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic"
    assert trace["provider_profile_model"] == "grok-4-fast"
    assert trace["production_selected"] is False


@pytest.mark.asyncio
async def test_current_shell_manager_provider_does_not_inject_contract_constraints_for_non_manager_stage() -> None:
    from app.runtime.interface.current_shell_manager_provider import (
        CurrentShellManagerContractProvider,
        current_shell_manager_provider_profile,
    )

    inner = _CapturingProvider()
    provider = CurrentShellManagerContractProvider(
        inner,
        profile=current_shell_manager_provider_profile(),
    )

    await provider.complete_with_trace(
        system_prompt="Return JSON.",
        user_payload={"constraints": {"request_id": "req-2"}},
        stage="not_manager",
        max_tokens=900,
    )

    constraints = inner.calls[0]["user_payload"]["constraints"]
    assert constraints == {"request_id": "req-2"}


def test_provider_runtime_builderspace_manager_uses_current_shell_contract_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_MANAGER_PROVIDER", "builderspace")
    monkeypatch.delenv("BUILDERSPACE_MANAGER_MODEL", raising=False)

    module = importlib.import_module("app.runtime.interface.provider_runtime")
    from app.runtime.interface.current_shell_manager_provider import CurrentShellManagerContractProvider

    provider = module._create_provider(  # noqa: SLF001 - runtime factory contract.
        provider_env="AI_MANAGER_PROVIDER",
        default_provider="deepseek",
        role_label="manager",
    )

    assert isinstance(provider, CurrentShellManagerContractProvider)
    readiness = provider.readiness()
    assert readiness["provider"] == "builderspace"
    assert readiness["manager_model"] == "grok-4-fast"
    assert readiness["provider_profile_id"] == "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic"
    assert readiness["provider_profile_model"] == "grok-4-fast"
    assert readiness["production_selected"] is False
