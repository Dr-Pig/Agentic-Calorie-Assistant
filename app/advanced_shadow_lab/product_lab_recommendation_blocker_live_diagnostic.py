from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.advanced_shadow_lab.product_lab_recommendation_blocker_artifact import (
    case_blockers,
    finalize_recommendation_blocker_artifact,
    provider_review_blockers,
    provider_review_summary,
    recommendation_blocker_artifact,
    trace_summary,
)
from app.advanced_shadow_lab.product_lab_recommendation_blocker_cases import (
    build_recommendation_blocker_case_reports,
)
from app.shared.infra.json_artifacts import write_json_artifact


STAGE = "advanced_product_lab_recommendation_blocker_live_diagnostic"
SYSTEM_PROMPT = (
    "Return JSON only for recommendation blocker diagnostics. Inspect case "
    "reports where deterministic candidate_retrieval_guard_scoring must apply "
    "negative preference blockers before offer_synthesis. Return "
    "blocker_respected, blocked_candidate_selected, positive_boost_observed, "
    "offer_synthesis_after_guard, answer_summary, risk_notes, and claim_scope. "
    "Correct behavior uses memory boosts only after hard blockers."
)


class FakeRecommendationBlockerProvider:
    def __init__(self, *, corrupt_review: bool = False) -> None:
        self.corrupt_review = corrupt_review

    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-recommendation-blocker", "configured": True}

    async def complete_with_trace(
        self, **_: object
    ) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "blocker_respected": not self.corrupt_review,
            "blocked_candidate_selected": self.corrupt_review,
            "positive_boost_observed": True,
            "offer_synthesis_after_guard": True,
            "answer_summary": "Negative preference blockers run before offer synthesis.",
            "risk_notes": "fake recommendation blocker review",
            "claim_scope": "diagnostic_only",
        }, {"stage": STAGE, "provider": "fake"}


def run_recommendation_blocker_live_diagnostic(
    *,
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    case_reports = build_recommendation_blocker_case_reports()
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
    artifact = recommendation_blocker_artifact(
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
    finalize_recommendation_blocker_artifact(artifact)
    if output_path:
        write_json_artifact(output_path, artifact)
    return artifact


async def _invoke_provider(
    provider: Any, case_reports: list[Mapping[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload={
            "target_surface": "advanced_product_lab_recommendation_blocker_live_diagnostic",
            "case_reports": [dict(report) for report in case_reports],
            "constraints": {
                "claim_scope_required": "diagnostic_only",
                "hard_blockers_owned_by": "deterministic_candidate_retrieval_guard_scoring",
                "mainline_activation_allowed": False,
            },
        },
        stage=STAGE,
        max_tokens=1200,
    )
    return _mapping(result), _mapping(trace)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "FakeRecommendationBlockerProvider",
    "run_recommendation_blocker_live_diagnostic",
]
