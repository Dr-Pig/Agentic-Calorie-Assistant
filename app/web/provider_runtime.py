from __future__ import annotations

import os

from ..providers.builderspace_adapter import BuilderSpaceAdapter
from ..providers.gemini_adapter import GeminiAdapter
from ..search.tavily_adapter import TavilyAdapter


def _create_provider(
    *,
    provider_env: str,
    default_provider: str,
    role_label: str,
) -> BuilderSpaceAdapter | GeminiAdapter:
    provider_name = os.getenv(provider_env, default_provider).strip().lower()
    if provider_name == "gemini":
        return GeminiAdapter()
    if role_label == "planner":
        return BuilderSpaceAdapter(role_label=role_label)
    return BuilderSpaceAdapter(role_label=role_label)


planner_provider = _create_provider(
    provider_env="AI_PLANNER_PROVIDER",
    default_provider=os.getenv("AI_PROVIDER", "builderspace"),
    role_label="planner",
)
primary_provider = _create_provider(
    provider_env="AI_PRIMARY_PROVIDER",
    default_provider=os.getenv("AI_PROVIDER", "builderspace"),
    role_label="primary",
)
provider = primary_provider
search_provider = TavilyAdapter()

__all__ = [
    "planner_provider",
    "primary_provider",
    "provider",
    "search_provider",
]
