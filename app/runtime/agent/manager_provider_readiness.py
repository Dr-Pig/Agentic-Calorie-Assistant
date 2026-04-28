from __future__ import annotations

from typing import Any


def provider_ready(provider: Any) -> bool:
    readiness = provider.readiness() if hasattr(provider, "readiness") else {}
    return bool(readiness.get("configured")) and hasattr(provider, "complete_with_trace")


__all__ = ["provider_ready"]
