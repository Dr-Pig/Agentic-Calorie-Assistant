from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
)
from app.advanced_shadow_lab.product_lab_manager_turn_grokfast_artifact import (
    build_manager_turn_grokfast_artifact,
)
from app.advanced_shadow_lab.product_lab_manager_turn_grokfast_policy import (
    manager_turn_output_guard,
    manager_turn_runtime_blockers,
)
from app.advanced_shadow_lab.product_lab_manager_turn_live_payload import (
    manager_turn_live_provider_payload,
)
from app.shared.infra.json_artifacts import write_json_artifact


ARTIFACT_TYPE = "advanced_product_lab_manager_turn_grokfast_diagnostic"
STAGE = "advanced_product_lab_manager_turn_diagnostic"
SYSTEM_PROMPT = (
    "Return JSON only for an advanced product-lab Manager turn diagnostic. "
    "Use the provided runtime summary; do not infer from raw chat text. Required "
    "fields: claim_scope, selected_capabilities, tool_call_order, "
    "manager_turn_summary, action_request, delivery_request, mutation_request, "
    "risk_notes. This is diagnostic-only evidence."
)


def run_manager_turn_grokfast_diagnostic(
    *,
    runtime_artifact: Mapping[str, Any],
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    input_blockers = manager_turn_runtime_blockers(runtime_artifact)
    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    provider_error: dict[str, Any] = {}
    provider_invoked = False
    if not input_blockers:
        provider_invoked = True
        try:
            provider_result, provider_trace = asyncio.run(
                _invoke_provider(provider, runtime_artifact)
            )
        except Exception as exc:
            provider_error = {"type": type(exc).__name__, "message": str(exc)[:300]}
    output_guard = (
        {"status": "not_run", "blockers": []}
        if input_blockers or provider_error
        else manager_turn_output_guard(provider_result)
    )
    blockers = [*input_blockers, *output_guard["blockers"]]
    status = "provider_error" if provider_error else "blocked" if blockers else "pass"
    artifact = build_manager_turn_grokfast_artifact(
        artifact_type=ARTIFACT_TYPE,
        status=status,
        runtime_artifact=runtime_artifact,
        provider_mode=provider_mode,
        provider_profile_id=provider_profile_id,
        live_invoked=live_invoked,
        provider_invoked=provider_invoked,
        provider=provider,
        provider_trace=provider_trace,
        provider_error=provider_error,
        provider_result=provider_result,
        output_guard=output_guard,
        blockers=blockers,
    )
    if output_path is not None:
        write_json_artifact(output_path, artifact)
    return artifact


def blocked_not_invoked_manager_turn_grokfast_artifact(
    *,
    reason: str,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    artifact = build_manager_turn_grokfast_artifact(
        artifact_type=ARTIFACT_TYPE,
        status="blocked",
        runtime_artifact={},
        provider_mode="not_invoked",
        provider_profile_id=provider_profile_id,
        live_invoked=False,
        provider_invoked=False,
        provider=None,
        provider_trace={"stage": "not_invoked", "provider": "not_invoked"},
        provider_error={},
        provider_result={},
        output_guard={"status": "not_invoked", "blockers": []},
        blockers=[reason],
    )
    if output_path is not None:
        write_json_artifact(output_path, artifact)
    return artifact


async def _invoke_provider(
    provider: Any,
    runtime_artifact: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload=manager_turn_live_provider_payload(
            runtime_artifact,
            constraints={
                "claim_scope_required": "diagnostic_only",
                "lab_runtime_surface_allowed": True,
                "outside_lab_delivery_allowed": False,
                "mutation_or_commit_allowed": False,
            },
        ),
        stage=STAGE,
        max_tokens=700,
    )
    return _mapping(result), _mapping(trace)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "ARTIFACT_TYPE",
    "blocked_not_invoked_manager_turn_grokfast_artifact",
    "run_manager_turn_grokfast_diagnostic",
]
