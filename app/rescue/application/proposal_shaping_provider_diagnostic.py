from __future__ import annotations

import asyncio
from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.shared.contracts.sidecar_activation import offline_sidecar_contract

from .proposal_shaping_contracts import FALSE_OUTPUT_FLAGS, STAGE, mapping
from .proposal_shaping_validation import (
    blocked_validation,
    payload_blockers,
    validate_rescue_proposal_shaping_output,
)


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.proposal_shaping_provider_diagnostic"
)


def run_rescue_proposal_shaping_fake_provider(
    *,
    proposal_shaping_payload: Mapping[str, Any],
    candidate_output: Mapping[str, Any],
) -> dict[str, Any]:
    validation = validate_rescue_proposal_shaping_output(
        proposal_shaping_payload=proposal_shaping_payload,
        candidate_output=candidate_output,
    )
    return _diagnostic_artifact(
        artifact_type="rescue_proposal_shaping_fake_provider_artifact",
        provider_mode="fake",
        live_llm_invoked=False,
        provider_called=False,
        live_provider_used=False,
        provider_readiness={},
        provider_trace={},
        validation=validation,
    )


def run_rescue_proposal_shaping_provider_diagnostic(
    *,
    proposal_shaping_payload: Mapping[str, Any],
    provider: Any,
    provider_mode: str,
    live_llm_invoked: bool,
) -> dict[str, Any]:
    input_blockers = payload_blockers(proposal_shaping_payload)
    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    provider_called = False
    if not input_blockers:
        provider_called = True
        provider_result, provider_trace = asyncio.run(
            _invoke_provider(provider, proposal_shaping_payload)
        )
    validation = (
        blocked_validation(proposal_shaping_payload, input_blockers)
        if input_blockers
        else validate_rescue_proposal_shaping_output(
            proposal_shaping_payload=proposal_shaping_payload,
            candidate_output=provider_result,
        )
    )
    return _diagnostic_artifact(
        artifact_type="rescue_proposal_shaping_provider_diagnostic",
        provider_mode=provider_mode,
        live_llm_invoked=live_llm_invoked,
        provider_called=provider_called,
        live_provider_used=bool(live_llm_invoked and provider_called),
        provider_readiness=_provider_readiness(provider),
        provider_trace=provider_trace,
        validation=validation,
    )


class FakeRescueProposalShapingProvider:
    def __init__(self, candidate_output: Mapping[str, Any]) -> None:
        self._candidate_output = dict(candidate_output)

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "fake-builderspace",
            "configured": True,
            "provider_profile_id": ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
            "model_id": "grok-4-fast",
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return self._candidate_output, {"stage": str(kwargs.get("stage") or ""), "provider": "fake-builderspace"}


async def _invoke_provider(
    provider: Any,
    proposal_shaping_payload: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    request = mapping(proposal_shaping_payload.get("provider_request"))
    payload, trace = await provider.complete_with_trace(
        system_prompt=str(request.get("system_prompt") or ""),
        user_payload=mapping(request.get("user_payload")),
        stage=STAGE,
        max_tokens=650,
    )
    return mapping(payload), mapping(trace)


def _diagnostic_artifact(
    *,
    artifact_type: str,
    provider_mode: str,
    live_llm_invoked: bool,
    provider_called: bool,
    live_provider_used: bool,
    provider_readiness: Mapping[str, Any],
    provider_trace: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    status = str(validation.get("status") or "blocked")
    return {
        "artifact_type": artifact_type,
        "status": status,
        "owner": "app/rescue",
        "consumer": "rescue_response_presentation",
        "provider_mode": provider_mode,
        "provider_called": provider_called,
        "live_llm_invoked": live_llm_invoked,
        "live_provider_used": live_provider_used,
        "provider_readiness": dict(provider_readiness),
        "provider_trace_summary": _trace_summary(provider_trace),
        "validation": dict(validation),
        "blockers": list(validation.get("blockers") or []),
        "lab_user_facing_surface_allowed": validation.get("status") == "pass",
        "non_claims": [
            "not_mainline_activation",
            "not_canonical_mutation_authority",
            "not_scheduler_delivery",
            "not_production_model_selection",
        ],
        **dict(FALSE_OUTPUT_FLAGS),
    }


def _provider_readiness(provider: Any) -> dict[str, Any]:
    readiness = provider.readiness() if hasattr(provider, "readiness") else {}
    return mapping(readiness)


def _trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {"stage": str(trace.get("stage") or ""), "provider": str(trace.get("provider") or "")}


__all__ = [
    "FakeRescueProposalShapingProvider",
    "SIDECAR_ACTIVATION_CONTRACT",
    "run_rescue_proposal_shaping_fake_provider",
    "run_rescue_proposal_shaping_provider_diagnostic",
]
