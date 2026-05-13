from __future__ import annotations

from app.shared.contracts.sidecar_activation import offline_sidecar_contract

from .response_presentation_card import build_rescue_response_card
from .response_presentation_contracts import (
    PRIMARY_ACTIONS,
    STAGE,
    build_rescue_response_presentation_payload,
)
from .response_presentation_provider_diagnostic import (
    FakeRescueResponsePresentationProvider,
    run_rescue_response_presentation_provider_diagnostic,
)
from .response_presentation_validation import (
    validate_rescue_response_presentation_output,
)


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.response_presentation_seam"
)


__all__ = [
    "FakeRescueResponsePresentationProvider",
    "PRIMARY_ACTIONS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "STAGE",
    "build_rescue_response_card",
    "build_rescue_response_presentation_payload",
    "run_rescue_response_presentation_provider_diagnostic",
    "validate_rescue_response_presentation_output",
]
