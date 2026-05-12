from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.advanced_shadow_lab.product_lab_rescue_memory_context_artifact import (
    case_blockers,
    finalize_rescue_memory_context_artifact,
    provider_review_blockers,
    provider_review_summary,
    rescue_memory_context_artifact,
    trace_summary,
)
from app.advanced_shadow_lab.product_lab_rescue_memory_context_cases import (
    build_rescue_memory_context_case_reports,
)
from app.shared.infra.json_artifacts import write_json_artifact


STAGE = "advanced_product_lab_rescue_memory_context_live_diagnostic"
SYSTEM_PROMPT = (
    "Return JSON only for rescue memory context diagnostics. Inspect cases where "
    "rescue may use scoped memory context but cannot mutate meal, budget, body, "
    "ledger, or durable memory truth. Return memory_context_used, "
    "claim_boundary_respected, rescue_commit_requested, "
    "meal_or_budget_truth_mutated, answer_summary, risk_notes, and claim_scope."
)


class FakeRescueMemoryContextProvider:
    def __init__(self, *, corrupt_review: bool = False) -> None:
        self.corrupt_review = corrupt_review

    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-rescue-memory-context", "configured": True}

    async def complete_with_trace(
        self, **_: object
    ) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "memory_context_used": True,
            "claim_boundary_respected": not self.corrupt_review,
            "rescue_commit_requested": self.corrupt_review,
            "meal_or_budget_truth_mutated": self.corrupt_review,
            "answer_summary": "Rescue context stays read-only until explicit commit.",
            "risk_notes": "fake rescue memory context review",
            "claim_scope": "diagnostic_only",
        }, {"stage": STAGE, "provider": "fake"}


def run_rescue_memory_context_live_diagnostic(
    *,
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    case_reports = build_rescue_memory_context_case_reports()
    provider_invoked = False
    provider_error: dict[str, Any] = {}
    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    try:
        provider_invoked = True
        provider_result, provider_trace = asyncio.run(_invoke_provider(provider, case_reports))
    except Exception as exc:
        provider_error = {"type": type(exc).__name__, "message": str(exc)[:300]}
    blockers = (
        case_blockers(case_reports)
        if provider_error
        else [*case_blockers(case_reports), *provider_review_blockers(provider_result)]
    )
    status = "provider_error" if provider_error else "blocked" if blockers else "pass"
    artifact = rescue_memory_context_artifact(
        status=status,
        provider_mode=provider_mode,
        provider_profile_id=provider_profile_id,
        live_invoked=live_invoked,
        provider_invoked=provider_invoked,
        case_reports=case_reports,
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
    finalize_rescue_memory_context_artifact(artifact)
    if output_path:
        write_json_artifact(output_path, artifact)
    return artifact


async def _invoke_provider(
    provider: Any, case_reports: list[Mapping[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload={
            "target_surface": "advanced_product_lab_rescue_memory_context_live_diagnostic",
            "case_reports": [dict(report) for report in case_reports],
            "constraints": {
                "claim_scope_required": "diagnostic_only",
                "rescue_context_memory_use": "read_only",
                "canonical_mutation_allowed": False,
            },
        },
        stage=STAGE,
        max_tokens=1200,
    )
    return _mapping(result), _mapping(trace)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "FakeRescueMemoryContextProvider",
    "run_rescue_memory_context_live_diagnostic",
]
