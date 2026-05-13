from __future__ import annotations

import asyncio
from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.shared.contracts.sidecar_activation import offline_sidecar_contract

from .response_presentation_card import build_rescue_response_card
from .response_presentation_contracts import FALSE_OUTPUT_FLAGS, STAGE, mapping
from .response_presentation_validation import (
    blocked_validation,
    payload_blockers,
    validate_rescue_response_presentation_output,
)


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.response_presentation_provider_diagnostic"
)


def run_rescue_response_presentation_provider_diagnostic(
    *,
    response_presentation_payload: Mapping[str, Any],
    provider: Any,
    provider_mode: str,
    live_llm_invoked: bool,
) -> dict[str, Any]:
    input_blockers = payload_blockers(response_presentation_payload)
    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    provider_called = False
    if not input_blockers:
        provider_called = True
        provider_result, provider_trace = asyncio.run(
            _invoke_provider(provider, response_presentation_payload)
        )
    validation = (
        blocked_validation(response_presentation_payload, input_blockers)
        if input_blockers
        else validate_rescue_response_presentation_output(
            response_presentation_payload=response_presentation_payload,
            candidate_output=provider_result,
        )
    )
    card_packet = build_rescue_response_card(
        response_presentation_payload=response_presentation_payload,
        response_presentation_validation=validation,
    )
    return _diagnostic_artifact(
        provider_mode=provider_mode,
        live_llm_invoked=live_llm_invoked,
        provider_called=provider_called,
        live_provider_used=bool(live_llm_invoked and provider_called),
        provider_readiness=_provider_readiness(provider),
        provider_trace=provider_trace,
        validation=validation,
        card_packet=card_packet,
    )


class FakeRescueResponsePresentationProvider:
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
    response_presentation_payload: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    request = mapping(response_presentation_payload.get("provider_request"))
    payload, trace = await provider.complete_with_trace(
        system_prompt=str(request.get("system_prompt") or ""),
        user_payload=mapping(request.get("user_payload")),
        stage=STAGE,
        max_tokens=700,
    )
    return mapping(payload), mapping(trace)


def _diagnostic_artifact(
    *,
    provider_mode: str,
    live_llm_invoked: bool,
    provider_called: bool,
    live_provider_used: bool,
    provider_readiness: Mapping[str, Any],
    provider_trace: Mapping[str, Any],
    validation: Mapping[str, Any],
    card_packet: Mapping[str, Any],
) -> dict[str, Any]:
    status = "pass" if validation.get("status") == "pass" and card_packet.get("status") == "pass" else "fail"
    return {
        "artifact_type": "rescue_response_presentation_provider_diagnostic",
        "status": status,
        "owner": "app/rescue",
        "consumer": "future_accept_or_dismiss_rescue_plan_contract",
        "provider_mode": provider_mode,
        "provider_called": provider_called,
        "live_llm_invoked": live_llm_invoked,
        "live_provider_used": live_provider_used,
        "provider_readiness": dict(provider_readiness),
        "provider_trace_summary": _trace_summary(provider_trace),
        "validation": dict(validation),
        "response_card_packet": dict(card_packet),
        "blockers": [*list(validation.get("blockers") or []), *list(card_packet.get("blockers") or [])],
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
    "FakeRescueResponsePresentationProvider",
    "SIDECAR_ACTIVATION_CONTRACT",
    "run_rescue_response_presentation_provider_diagnostic",
]
