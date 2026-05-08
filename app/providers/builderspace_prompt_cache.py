from __future__ import annotations

import hashlib
import json
import re
from typing import Any


PROMPT_CACHE_KEY_VERSION = "builderspace_prompt_cache_key.v2"


def apply_prompt_cache_key(
    request_payload: dict[str, Any],
    *,
    model: str,
    stage: str,
) -> dict[str, Any]:
    updated = dict(request_payload)
    updated["prompt_cache_key"] = build_prompt_cache_key(
        model=model,
        stage=stage,
        request_payload=request_payload,
    )
    return updated


def build_prompt_cache_key(
    *,
    model: str,
    stage: str,
    request_payload: dict[str, Any],
) -> str:
    digest = _sha256_json(
        {
            "version": PROMPT_CACHE_KEY_VERSION,
            "model": str(model),
            "stage": str(stage),
            "stable_prompt_prefix_sha256": _stable_prompt_prefix_sha256(request_payload),
        }
    )[:24]
    return f"bs:{_safe_key_part(stage)}:{_safe_key_part(model)}:{digest}"


def _stable_prompt_prefix_sha256(request_payload: dict[str, Any]) -> str:
    messages = request_payload.get("messages") if isinstance(request_payload.get("messages"), list) else []
    system_messages = [
        dict(message)
        for message in messages
        if isinstance(message, dict) and str(message.get("role") or "") in {"system", "developer"}
    ]
    return _sha256_json(
        {
            "tools": request_payload.get("tools"),
            "response_format": request_payload.get("response_format"),
            "system_messages": system_messages,
        }
    )


def _safe_key_part(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value).strip())
    return normalized[:48].strip("-") or "unknown"


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, default=str, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


__all__ = [
    "PROMPT_CACHE_KEY_VERSION",
    "apply_prompt_cache_key",
    "build_prompt_cache_key",
]
