from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .fooddb_websearch_no_runtime_wall_policy import (
    blocker_list_is_non_empty,
    count_key_forbidden,
    status_is_blocked,
    truthy_key_forbidden,
    value_is_claim_signal,
)


def forbidden_paths(
    value: Any,
    *,
    path: str = "$",
    artifact_type: str = "",
    parent: dict[str, Any] | None = None,
) -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if status_is_blocked(key, child, child_path):
                violations.append(child_path)
            if blocker_list_is_non_empty(key, child):
                violations.append(child_path)
            if value_is_claim_signal(child) and truthy_key_forbidden(
                key,
                child_path,
                artifact_type=artifact_type,
                parent=value,
            ):
                violations.append(child_path)
            if count_key_forbidden(key, child, child_path):
                violations.append(child_path)
            violations.extend(
                forbidden_paths(
                    child,
                    path=child_path,
                    artifact_type=artifact_type,
                    parent=value,
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            violations.extend(
                forbidden_paths(
                    child,
                    path=f"{path}[{index}]",
                    artifact_type=artifact_type,
                    parent=parent,
                )
            )
    return violations


def stable_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


__all__ = ["forbidden_paths", "stable_unique"]
