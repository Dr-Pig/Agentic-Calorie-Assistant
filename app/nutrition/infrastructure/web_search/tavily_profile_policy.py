from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TavilyRuntimeSearchProfile:
    search_depth: str = "basic"
    include_raw_content: bool = False


@dataclass(frozen=True)
class TavilySelectedExtractProfile:
    extract_depth: str = "advanced"
    chunks_per_source: int = 3


def runtime_search_profile() -> TavilyRuntimeSearchProfile:
    return TavilyRuntimeSearchProfile()


def selected_extract_profile() -> TavilySelectedExtractProfile:
    return TavilySelectedExtractProfile()


__all__ = [
    "TavilyRuntimeSearchProfile",
    "TavilySelectedExtractProfile",
    "runtime_search_profile",
    "selected_extract_profile",
]
