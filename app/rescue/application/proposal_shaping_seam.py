from __future__ import annotations

from app.shared.contracts.sidecar_activation import offline_sidecar_contract

from .proposal_shaping_contracts import (
    STAGE,
    build_rescue_proposal_shaping_payload,
)
from .proposal_shaping_provider_diagnostic import (
    FakeRescueProposalShapingProvider,
    run_rescue_proposal_shaping_fake_provider,
    run_rescue_proposal_shaping_provider_diagnostic,
)
from .proposal_shaping_validation import validate_rescue_proposal_shaping_output


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.proposal_shaping_seam"
)


__all__ = [
    "FakeRescueProposalShapingProvider",
    "SIDECAR_ACTIVATION_CONTRACT",
    "STAGE",
    "build_rescue_proposal_shaping_payload",
    "run_rescue_proposal_shaping_fake_provider",
    "run_rescue_proposal_shaping_provider_diagnostic",
    "validate_rescue_proposal_shaping_output",
]
