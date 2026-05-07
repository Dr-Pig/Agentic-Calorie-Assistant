from __future__ import annotations

from typing import Any

from app.runtime.agent.founder_live_manager_contract import FOUNDER_LIVE_MANAGER_SCHEMA_VERSION
from app.runtime.agent.manager_system_prompt import (
    SINGLE_MANAGER_SYSTEM_PROMPT_ID,
    SINGLE_MANAGER_SYSTEM_PROMPT_VERSION,
)
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE


MANAGER_PROMPT_REGISTRY_VERSION = "manager_prompt_registry.v1"
MANAGER_TOOL_SURFACE_VERSION = "current_shell_public_tools.v1"
MANAGER_OUTPUT_SCHEMA_NAME = "manager_loop_schema"
MANAGER_MODEL_PROMPT_CONTRACT_ID = "single_manager_user_payload_contract"
MANAGER_MODEL_PROMPT_CONTRACT_VERSION = "v1"


def build_manager_prompt_registry(
    *,
    provider: Any,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    readiness = provider.readiness() if hasattr(provider, "readiness") else {}
    readiness = readiness if isinstance(readiness, dict) else {}
    stage_models = readiness.get("stage_models")
    stage_models = stage_models if isinstance(stage_models, dict) else {}
    manager_model = stage_models.get(MANAGER_LOOP_STAGE) or readiness.get("manager_model")
    manager_contract_schema_version = (
        str((constraints or {}).get("manager_contract_schema_version") or FOUNDER_LIVE_MANAGER_SCHEMA_VERSION)
        or FOUNDER_LIVE_MANAGER_SCHEMA_VERSION
    )
    model_profile_overlay_id = (
        str((constraints or {}).get("manager_contract_provider_profile_id") or "").strip()
        or None
    )
    model_profile_overlay_transport_mode = (
        str((constraints or {}).get("manager_contract_provider_profile_transport_mode") or "").strip() or None
    )
    return {
        "registry_version": MANAGER_PROMPT_REGISTRY_VERSION,
        "manager_loop_stage": MANAGER_LOOP_STAGE,
        "system_prompt_id": SINGLE_MANAGER_SYSTEM_PROMPT_ID,
        "system_prompt_version": SINGLE_MANAGER_SYSTEM_PROMPT_VERSION,
        "model_prompt_contract_id": MANAGER_MODEL_PROMPT_CONTRACT_ID,
        "model_prompt_contract_version": MANAGER_MODEL_PROMPT_CONTRACT_VERSION,
        "tool_surface_version": MANAGER_TOOL_SURFACE_VERSION,
        "output_schema_name": MANAGER_OUTPUT_SCHEMA_NAME,
        "output_schema_version": manager_contract_schema_version,
        "provider": str(readiness.get("provider") or "").strip() or None,
        "manager_model": str(manager_model).strip() if manager_model is not None else None,
        "model_profile_overlay_id": model_profile_overlay_id,
        "model_profile_overlay_transport_mode": model_profile_overlay_transport_mode,
    }


__all__ = [
    "MANAGER_OUTPUT_SCHEMA_NAME",
    "MANAGER_MODEL_PROMPT_CONTRACT_ID",
    "MANAGER_MODEL_PROMPT_CONTRACT_VERSION",
    "MANAGER_PROMPT_REGISTRY_VERSION",
    "MANAGER_TOOL_SURFACE_VERSION",
    "build_manager_prompt_registry",
]
