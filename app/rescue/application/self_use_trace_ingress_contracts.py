from __future__ import annotations

from dataclasses import dataclass

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.self_use_trace_ingress"
)
REQUIRED_SCOPE_KEYS = ("user_id", "workspace_id", "project_id", "surface", "run_id")


@dataclass(frozen=True)
class RescueIngressScopeError(ValueError):
    missing_keys: tuple[str, ...]

    def __str__(self) -> str:
        return f"missing_scope_keys:{','.join(self.missing_keys)}"


__all__ = [
    "REQUIRED_SCOPE_KEYS",
    "RescueIngressScopeError",
    "SIDECAR_ACTIVATION_CONTRACT",
]
