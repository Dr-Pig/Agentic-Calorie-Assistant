from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.advanced_shadow_lab.product_lab_proactive_send_skip import (
    run_product_lab_proactive_send_skip_fixture,
)
from app.advanced_shadow_lab.product_lab_proactive_send_skip_live_policy import (
    ARTIFACT_TYPE,
    STAGE,
    SYSTEM_PROMPT,
    mapping,
    model_output_summary,
    provider_payload,
    trace_summary,
)
from app.shared.infra.json_artifacts import write_json_artifact


def run_product_lab_proactive_send_skip_live_diagnostic(
    *,
    pre_delivery_review: Mapping[str, Any],
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    provider_error: dict[str, Any] = {}
    provider_invoked = True
    try:
        provider_result, provider_trace = asyncio.run(
            _invoke_provider(provider, pre_delivery_review)
        )
    except Exception as exc:
        provider_error = {"type": type(exc).__name__, "message": str(exc)[:300]}
    validation = (
        _not_run_validation()
        if provider_error
        else _validate_provider_output(pre_delivery_review, provider_result)
    )
    blockers = [f"validation.{item}" for item in validation.get("blockers") or []]
    status = "provider_error" if provider_error else "blocked" if blockers else "pass"
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": status,
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "live_invoked": live_invoked,
        "provider_invoked": provider_invoked,
        "live_provider_used": bool(live_invoked and provider_invoked and not provider_error),
        "live_grokfast_diagnostic_pass": bool(live_invoked and status == "pass"),
        "provider_readiness": mapping(provider.readiness()) if hasattr(provider, "readiness") else {},
        "provider_trace_summary": trace_summary(provider_trace),
        "provider_error": provider_error,
        "model_output_summary": model_output_summary(provider_result),
        "validation_artifact": validation,
        "blockers": blockers,
        "mainline_activation_enabled": False,
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "raw_keyword_semantic_oracle_allowed": False,
        **dict(FALSE_FLAGS),
    }
    artifact["live_provider_used"] = bool(
        live_invoked and provider_invoked and not provider_error
    )
    artifact["live_grokfast_diagnostic_pass"] = bool(live_invoked and status == "pass")
    if output_path is not None:
        write_json_artifact(output_path, artifact)
    return artifact


def blocked_not_invoked_proactive_send_skip_live_artifact(
    *,
    reason: str,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked",
        "provider_mode": "not_invoked",
        "provider_profile_id": provider_profile_id,
        "live_invoked": False,
        "provider_invoked": False,
        "live_provider_used": False,
        "live_grokfast_diagnostic_pass": False,
        "provider_error": {},
        "validation_artifact": _not_run_validation(),
        "blockers": [reason],
        "mainline_activation_enabled": False,
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        **dict(FALSE_FLAGS),
    }
    if output_path is not None:
        write_json_artifact(output_path, artifact)
    return artifact


async def _invoke_provider(
    provider: Any,
    pre_delivery_review: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload=provider_payload(pre_delivery_review),
        stage=STAGE,
        max_tokens=900,
    )
    return mapping(result), mapping(trace)


def _validate_provider_output(
    pre_delivery_review: Mapping[str, Any],
    output: Mapping[str, Any],
) -> dict[str, Any]:
    validation = run_product_lab_proactive_send_skip_fixture(
        pre_delivery_review=pre_delivery_review,
        provider_decisions=[
            item
            for item in output.get("provider_decisions") or output.get("decisions") or []
            if isinstance(item, Mapping)
        ],
    )
    if output.get("claim_scope") != "diagnostic_only":
        validation["blockers"] = [
            "model_output.claim_scope_not_diagnostic_only",
            *list(validation.get("blockers") or []),
        ]
        validation["status"] = "blocked"
    return validation


def _not_run_validation() -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_proactive_contextual_send_skip_fixture",
        "status": "not_run",
        "blockers": [],
    }


__all__ = [
    "ARTIFACT_TYPE",
    "blocked_not_invoked_proactive_send_skip_live_artifact",
    "run_product_lab_proactive_send_skip_live_diagnostic",
]
