from __future__ import annotations

import os
from typing import Any

from app.runtime.agent.founder_live_manager_contract import (
    founder_live_manager_contract_constraints,
)
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE

CURRENT_SHELL_MANAGER_PROVIDER_PROFILE_ENV = "ACCURATE_INTAKE_MANAGER_PROVIDER_PROFILE_ID"
DEFAULT_CURRENT_SHELL_MANAGER_PROVIDER_PROFILE_ID = (
    "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic"
)

_CURRENT_SHELL_MANAGER_PROFILES: dict[str, dict[str, Any]] = {
    DEFAULT_CURRENT_SHELL_MANAGER_PROVIDER_PROFILE_ID: {
        "provider_profile_id": DEFAULT_CURRENT_SHELL_MANAGER_PROVIDER_PROFILE_ID,
        "provider": "builderspace",
        "model": "grok-4-fast",
        "provider_profile_role": "current_shell_manager_runtime",
        "production_selected": False,
        "not_production_selection": True,
        "readiness_owner": False,
    },
}


def current_shell_manager_provider_profile(profile_id: str | None = None) -> dict[str, Any]:
    selected_profile_id = str(
        profile_id
        or os.getenv(CURRENT_SHELL_MANAGER_PROVIDER_PROFILE_ENV)
        or DEFAULT_CURRENT_SHELL_MANAGER_PROVIDER_PROFILE_ID
    ).strip()
    if selected_profile_id not in _CURRENT_SHELL_MANAGER_PROFILES:
        supported = ", ".join(sorted(_CURRENT_SHELL_MANAGER_PROFILES))
        raise ValueError(
            f"Unsupported Current Shell manager provider profile: {selected_profile_id}. "
            f"Supported: {supported}"
        )
    return dict(_CURRENT_SHELL_MANAGER_PROFILES[selected_profile_id])


def with_current_shell_manager_contract_constraints(
    kwargs: dict[str, Any],
    *,
    profile: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(kwargs)
    if str(updated.get("stage") or "") != MANAGER_LOOP_STAGE:
        return updated

    user_payload = dict(_dict(updated.get("user_payload")))
    constraints = dict(_dict(user_payload.get("constraints")))
    constraints["current_shell_manager_runtime_contract"] = {
        "runner_inferred_semantics": False,
        "raw_text_routing_forbidden": True,
        "provider_profile_semantic_owner": False,
        "live_provider_used_as_truth": False,
    }
    tool_results = [dict(item) for item in _list(user_payload.get("tool_results")) if isinstance(item, dict)]
    constraints.update(
        founder_live_manager_contract_constraints(
            str(profile["provider_profile_id"]),
            tool_results=tool_results,
        )
    )
    user_payload["constraints"] = constraints
    updated["user_payload"] = user_payload
    return updated


class CurrentShellManagerContractProvider:
    """App-runtime wrapper that binds the live Manager route to the shared contract seam."""

    def __init__(self, provider: Any, *, profile: dict[str, Any]) -> None:
        self._provider = provider
        self.profile = dict(profile)

    def begin_step(self, step_script: dict[str, Any]) -> None:
        if hasattr(self._provider, "begin_step"):
            self._provider.begin_step(step_script)

    def readiness(self) -> dict[str, Any]:
        readiness = self._provider.readiness() if hasattr(self._provider, "readiness") else {}
        return {
            **(readiness if isinstance(readiness, dict) else {}),
            "provider_profile_id": self.profile["provider_profile_id"],
            "provider_profile_model": self.profile["model"],
            "provider_profile_role": self.profile["provider_profile_role"],
            "production_selected": False,
            "not_production_selection": True,
            "readiness_owner": False,
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        updated_kwargs = with_current_shell_manager_contract_constraints(kwargs, profile=self.profile)
        payload, trace = await self._provider.complete_with_trace(**updated_kwargs)
        enriched_trace = {
            **(_dict(trace)),
            "provider_profile_id": self.profile["provider_profile_id"],
            "provider_profile_model": self.profile["model"],
            "provider_profile_role": self.profile["provider_profile_role"],
            "production_selected": False,
            "not_production_selection": True,
            "current_shell_manager_contract_wrapper": True,
        }
        return payload, enriched_trace


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


__all__ = [
    "CURRENT_SHELL_MANAGER_PROVIDER_PROFILE_ENV",
    "DEFAULT_CURRENT_SHELL_MANAGER_PROVIDER_PROFILE_ID",
    "CurrentShellManagerContractProvider",
    "current_shell_manager_provider_profile",
    "with_current_shell_manager_contract_constraints",
]
