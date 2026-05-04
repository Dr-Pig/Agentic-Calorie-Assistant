from __future__ import annotations

from app.shared.contracts.sidecar_activation import offline_sidecar_contract

from app.rescue.fixtures.shadow_scenarios import (
    RESCUE_SHADOW_SCENARIO_FIXTURES,
    rescue_shadow_scenario_fixture_pairs,
    rescue_shadow_scenario_ids,
)


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("rescue.fixtures")


__all__ = [
    "RESCUE_SHADOW_SCENARIO_FIXTURES",
    "SIDECAR_ACTIVATION_CONTRACT",
    "rescue_shadow_scenario_fixture_pairs",
    "rescue_shadow_scenario_ids",
]
