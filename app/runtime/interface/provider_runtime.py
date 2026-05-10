from __future__ import annotations

import os

from ...providers.builderspace_adapter import BuilderSpaceAdapter
from ...providers.deepseek_adapter import DeepSeekAdapter
from ...providers.tavily_search_port import TavilySearchPort
from .current_shell_manager_provider import (
    CurrentShellManagerContractProvider,
    current_shell_manager_provider_profile,
)


def _create_provider(
    *,
    provider_env: str,
    default_provider: str,
    role_label: str,
) -> BuilderSpaceAdapter | DeepSeekAdapter | CurrentShellManagerContractProvider:
    provider_name = os.getenv(provider_env, default_provider).strip().lower()
    if provider_name == "deepseek":
        return DeepSeekAdapter()
    if provider_name == "gemini":
        raise RuntimeError("Gemini provider is not supported in V2 single-manager runtime yet.")
    profile = current_shell_manager_provider_profile()
    adapter = BuilderSpaceAdapter(
        manager_model_override=str(profile["model"]),
        role_label=role_label,
    )
    return CurrentShellManagerContractProvider(adapter, profile=profile)


manager_provider = _create_provider(
    provider_env="AI_MANAGER_PROVIDER",
    default_provider=os.getenv("AI_PROVIDER", "deepseek"),
    role_label="manager",
)
provider = manager_provider
search_provider = TavilySearchPort()
extract_provider = search_provider.extract_port()


async def close_provider_clients() -> None:
    await search_provider.aclose()

__all__ = [
    "manager_provider",
    "provider",
    "search_provider",
    "extract_provider",
    "close_provider_clients",
]
