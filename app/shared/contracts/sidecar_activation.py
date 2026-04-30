from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SidecarActivationContract(BaseModel):
    module_name: str
    activation_stage: Literal["offline_sidecar"] = "offline_sidecar"
    offline_only: Literal[True] = True
    activation_blocked: Literal[True] = True
    not_runtime_authority: Literal[True] = True
    user_facing_activation: Literal[False] = False
    mutation_authority: Literal[False] = False
    product_intelligence_readiness_participant: Literal[False] = False


def offline_sidecar_contract(module_name: str) -> SidecarActivationContract:
    return SidecarActivationContract(module_name=module_name)


__all__ = ["SidecarActivationContract", "offline_sidecar_contract"]
