from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_live_output_guard import (
    product_lab_live_output_guard,
)
from app.advanced_shadow_lab.product_lab_memory_record_live_artifact import (
    ARTIFACT_TYPE,
    base_live_artifact,
    blocked_not_invoked_artifact,
    input_blockers,
    model_input_policy,
    model_output_summary,
    trace_summary,
)
from app.advanced_shadow_lab.product_lab_memory_record_live_payload import (
    memory_record_live_provider_payload,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract
from app.shared.infra.json_artifacts import write_json_artifact


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_memory_record_live_diagnostic"
)
STAGE = "advanced_product_lab_memory_record_live_diagnostic"
SYSTEM_PROMPT = (
    "Return JSON for a MemoryRecord integrated product-lab diagnostic only. "
    "Do not claim outside-lab delivery, user-facing activation, save, commit, "
    "schedule, or production application. Required fields: diagnostic_notes, "
    "risk_notes, claim_scope, action_request, delivery_request, mutation_request, "
    "reason_codes."
)


def run_memory_record_live_diagnostic(
    *,
    integrated_e2e_artifact: Mapping[str, Any],
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    provider_profile_id: str = "",
    source_integrated_e2e_path: str | Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    blockers = input_blockers(integrated_e2e_artifact)
    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    provider_error: dict[str, Any] = {}
    provider_invoked = False
    if not blockers:
        provider_invoked = True
        try:
            provider_result, provider_trace = asyncio.run(
                _invoke_provider(provider, integrated_e2e_artifact)
            )
        except Exception as exc:
            provider_error = {"type": type(exc).__name__, "message": str(exc)[:300]}
    output_guard = (
        {"status": "not_run", "blockers": []}
        if blockers or provider_error
        else product_lab_live_output_guard(provider_result)
    )
    all_blockers = [*blockers, *output_guard["blockers"]]
    status = (
        "provider_error" if provider_error else "blocked" if all_blockers else "pass"
    )
    artifact = base_live_artifact(
        status=status,
        provider_mode=provider_mode,
        provider_profile_id=provider_profile_id,
        live_invoked=live_invoked,
        source_integrated_e2e_path=source_integrated_e2e_path,
        integrated_e2e_artifact=integrated_e2e_artifact,
    )
    artifact.update(
        {
            "live_provider_used": bool(live_invoked and provider_invoked),
            "provider_invoked": provider_invoked,
            "provider_readiness": _mapping(provider.readiness())
            if hasattr(provider, "readiness")
            else {},
            "provider_trace_summary": trace_summary(provider_trace),
            "provider_error": provider_error,
            "model_output_summary": model_output_summary(provider_result),
            "output_guard": output_guard,
            "blockers": all_blockers,
        }
    )
    if output_path:
        write_json_artifact(output_path, artifact)
    return artifact


async def _invoke_provider(
    provider: Any,
    integrated_e2e_artifact: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload=memory_record_live_provider_payload(
            integrated_e2e_artifact,
            constraints=model_input_policy(),
        ),
        stage=STAGE,
        max_tokens=700,
    )
    return _mapping(payload), _mapping(trace)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "ARTIFACT_TYPE",
    "SIDECAR_ACTIVATION_CONTRACT",
    "blocked_not_invoked_artifact",
    "run_memory_record_live_diagnostic",
]
