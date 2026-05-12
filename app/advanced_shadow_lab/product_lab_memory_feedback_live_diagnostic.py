from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.advanced_shadow_lab.product_lab_memory_feedback_artifact import (
    case_blockers,
    finalize_memory_feedback_artifact,
    memory_feedback_artifact,
    provider_review_blockers,
    provider_review_summary,
    trace_summary,
)
from app.advanced_shadow_lab.product_lab_memory_feedback_cases import (
    build_memory_feedback_case_reports,
)
from app.shared.infra.json_artifacts import write_json_artifact


STAGE = "advanced_product_lab_memory_feedback_live_diagnostic"
SYSTEM_PROMPT = (
    "Return JSON only for a memory FeedbackEvent projection diagnostic. Inspect "
    "confirm, reject, and correct case reports. Return confirmed_memory_promoted, "
    "durable_memory_written, canonical_mutation_allowed, "
    "validator_required_for_confirm, answer_summary, risk_notes, and claim_scope. "
    "Correct behavior keeps FeedbackEvent as audit/input and does not mutate "
    "memory truth without separate validator approval."
)


class FakeMemoryFeedbackProvider:
    def __init__(self, *, corrupt_review: bool = False) -> None:
        self.corrupt_review = corrupt_review

    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-memory-feedback", "configured": True}

    async def complete_with_trace(
        self, **_: object
    ) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "confirmed_memory_promoted": self.corrupt_review,
            "durable_memory_written": self.corrupt_review,
            "canonical_mutation_allowed": False,
            "validator_required_for_confirm": True,
            "answer_summary": "FeedbackEvent projected to validator inputs only.",
            "risk_notes": "fake feedback projection review",
            "claim_scope": "diagnostic_only",
        }, {"stage": STAGE, "provider": "fake"}


def run_memory_feedback_live_diagnostic(
    *,
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    case_reports = build_memory_feedback_case_reports()
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
    artifact = memory_feedback_artifact(
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
    finalize_memory_feedback_artifact(artifact)
    if output_path:
        write_json_artifact(output_path, artifact)
    return artifact


async def _invoke_provider(
    provider: Any, case_reports: list[Mapping[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload=_provider_payload(case_reports),
        stage=STAGE,
        max_tokens=1200,
    )
    return _mapping(result), _mapping(trace)


def _provider_payload(case_reports: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "target_surface": "advanced_product_lab_memory_feedback_live_diagnostic",
        "case_reports": [dict(report) for report in case_reports],
        "output_contract": {
            "confirmed_memory_promoted_must_be_false": True,
            "durable_memory_written_must_be_false": True,
            "canonical_mutation_allowed_must_be_false": True,
            "validator_required_for_confirm_must_be_true": True,
        },
        "constraints": {
            "claim_scope_required": "diagnostic_only",
            "durable_memory_write_allowed": False,
            "canonical_mutation_allowed": False,
        },
    }


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "FakeMemoryFeedbackProvider",
    "run_memory_feedback_live_diagnostic",
]
