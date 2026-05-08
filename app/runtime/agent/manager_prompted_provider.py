from __future__ import annotations

from typing import Any

from app.runtime.agent.manager_prompt_layer_contract import build_manager_prompt_layer_contract
from app.runtime.agent.manager_system_prompt import single_manager_system_prompt_for_scope


async def complete_manager_round_with_prompt_trace(
    *,
    provider: Any,
    manager_loop_scope: str,
    user_payload: dict[str, Any],
    stage: str,
    max_tokens: int,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    system_prompt = single_manager_system_prompt_for_scope(manager_loop_scope)
    prompt_layer_contract = build_manager_prompt_layer_contract(
        manager_loop_scope=manager_loop_scope,
        system_prompt=system_prompt,
        user_payload=user_payload,
    )
    payload, trace = await provider.complete_with_trace(
        system_prompt=system_prompt,
        user_payload=user_payload,
        stage=stage,
        max_tokens=max_tokens,
    )
    return payload, trace, prompt_layer_contract


__all__ = ["complete_manager_round_with_prompt_trace"]
