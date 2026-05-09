from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from app.memory.application.runtime_lab_trace_ingress_contracts import (
    REQUIRED_SCOPE_KEYS,
)


def require_scope(scope_keys: Mapping[str, Any]) -> dict[str, str]:
    resolved = {key: str(scope_keys.get(key) or "") for key in REQUIRED_SCOPE_KEYS}
    missing = tuple(key for key in REQUIRED_SCOPE_KEYS if not resolved.get(key))
    if missing:
        raise ValueError(f"missing_scope_keys:{','.join(missing)}")
    return resolved


def candidate_path(root: Path, scope_keys: Mapping[str, Any], candidate_id: str) -> Path:
    return scope_dir(root, scope_keys) / f"{_safe_id(candidate_id)}.json"


def scope_dir(root: Path, scope_keys: Mapping[str, Any]) -> Path:
    scope = require_scope(scope_keys)
    raw = "|".join(scope[key] for key in REQUIRED_SCOPE_KEYS)
    digest = sha256(raw.encode("utf-8")).hexdigest()[:24]
    return root / "scopes" / digest


def scope_manifest(scope_keys: Mapping[str, Any]) -> dict[str, str]:
    return require_scope(scope_keys)


def _safe_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in value)


__all__ = [
    "candidate_path",
    "require_scope",
    "scope_dir",
    "scope_manifest",
]
