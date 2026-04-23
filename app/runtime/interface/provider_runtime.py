from __future__ import annotations

import os

from ...providers.builderspace_adapter import BuilderSpaceAdapter
from ...providers.deepseek_adapter import DeepSeekAdapter
from ...providers.gemini_adapter import GeminiAdapter
from ...nutrition.infrastructure.web_search.tavily_adapter import TavilyAdapter


def _create_provider(
    *,
    provider_env: str,
    default_provider: str,
    role_label: str,
) -> BuilderSpaceAdapter | DeepSeekAdapter | GeminiAdapter:
    provider_name = os.getenv(provider_env, default_provider).strip().lower()
    if provider_name == "deepseek":
        return DeepSeekAdapter()
    if provider_name == "gemini":
        return GeminiAdapter()
    return BuilderSpaceAdapter(role_label=role_label)


manager_provider = _create_provider(
    provider_env="AI_MANAGER_PROVIDER",
    default_provider=os.getenv("AI_PROVIDER", "deepseek"),
    role_label="manager",
)
provider = manager_provider
search_provider = TavilyAdapter()

__all__ = [
    "manager_provider",
    "provider",
    "search_provider",
]
