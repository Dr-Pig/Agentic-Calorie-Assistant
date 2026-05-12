from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.advanced_shadow_lab.product_lab_integrated_live_e2e_artifact import (
    case_bundle_blockers,
    finalize_integrated_live_e2e_artifact,
    integrated_live_e2e_artifact,
    provider_review_blockers,
    provider_review_summary,
    trace_summary,
)
from app.advanced_shadow_lab.product_lab_integrated_live_e2e_cases import (
    build_integrated_live_e2e_case_bundle,
)
from app.shared.infra.json_artifacts import write_json_artifact


STAGE = "advanced_product_lab_integrated_live_e2e"
SYSTEM_PROMPT = (
    "Return JSON only for integrated advanced product lab E2E diagnostics. "
    "Inspect compact component statuses for memory tools, recommendation, rescue, "
    "proactive controls, and the product lab chat turn. Return "
    "integrated_loop_closed, mainline_activation_enabled, "
    "canonical_mutation_allowed, durable_product_memory_written, "
    "scheduler_delivery_allowed, answer_summary, risk_notes, and claim_scope."
    " Lab memory context injection is allowed inside the isolated lab and is not "
    "a durable product memory write."
)


class FakeIntegratedLiveE2EProvider:
    def __init__(self, *, corrupt_review: bool = False) -> None:
        self.corrupt_review = corrupt_review

    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-integrated-live-e2e", "configured": True}

    async def complete_with_trace(
        self, **_: object
    ) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "integrated_loop_closed": not self.corrupt_review,
            "mainline_activation_enabled": self.corrupt_review,
            "canonical_mutation_allowed": self.corrupt_review,
            "durable_product_memory_written": False,
            "scheduler_delivery_allowed": False,
            "answer_summary": "Integrated lab loop closes without mainline activation.",
            "risk_notes": "fake integrated E2E review",
            "claim_scope": "diagnostic_only",
        }, {"stage": STAGE, "provider": "fake"}


def run_integrated_live_e2e(
    *,
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    case_bundle = build_integrated_live_e2e_case_bundle()
    provider_invoked = False
    provider_error: dict[str, Any] = {}
    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    try:
        provider_invoked = True
        provider_result, provider_trace = asyncio.run(_invoke_provider(provider, case_bundle))
    except Exception as exc:
        provider_error = {"type": type(exc).__name__, "message": str(exc)[:300]}
    blockers = (
        case_bundle_blockers(case_bundle)
        if provider_error
        else [*case_bundle_blockers(case_bundle), *provider_review_blockers(provider_result)]
    )
    status = "provider_error" if provider_error else "blocked" if blockers else "pass"
    artifact = integrated_live_e2e_artifact(
        status=status,
        provider_mode=provider_mode,
        provider_profile_id=provider_profile_id,
        live_invoked=live_invoked,
        provider_invoked=provider_invoked,
        case_bundle=case_bundle,
    )
    artifact.update(
        {
            "provider_readiness": _mapping(provider.readiness())
            if hasattr(provider, "readiness")
            else {},
            "provider_trace_summary": trace_summary(provider_trace),
            "provider_error": provider_error,
            "provider_review_summary": provider_review_summary(provider_result),
            "blockers": blockers,
        }
    )
    finalize_integrated_live_e2e_artifact(artifact)
    if output_path:
        write_json_artifact(output_path, artifact)
    return artifact


async def _invoke_provider(
    provider: Any, case_bundle: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload={
            "target_surface": "advanced_product_lab_integrated_live_e2e",
            "case_bundle": dict(case_bundle),
            "activation_boundary": _activation_boundary(case_bundle),
            "constraints": {
                "claim_scope_required": "diagnostic_only",
                "lab_user_facing_output_allowed": True,
                "mainline_activation_allowed": False,
                "canonical_mutation_allowed": False,
            },
        },
        stage=STAGE,
        max_tokens=1400,
    )
    return _mapping(result), _mapping(trace)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _activation_boundary(case_bundle: Mapping[str, Any]) -> dict[str, bool]:
    turn = _mapping(case_bundle.get("product_lab_turn_summary"))
    return {
        "lab_memory_context_injected": turn.get("memory_context_injected") is True,
        "lab_user_facing_behavior_changed": turn.get("lab_user_facing_behavior_changed")
        is True,
        "mainline_activation_enabled": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "scheduler_delivery_allowed": False,
    }


__all__ = ["FakeIntegratedLiveE2EProvider", "run_integrated_live_e2e"]
