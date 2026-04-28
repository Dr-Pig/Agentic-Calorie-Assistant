from __future__ import annotations

import json
from typing import Any

from ..text_integrity import corruption_summary, find_text_corruption


def format_user_message(stage: str, user_payload: dict[str, Any]) -> str:
    return json.dumps({"stage": stage, "payload": jsonable(user_payload)}, ensure_ascii=False)


def check_encoding_safety(content: str) -> None:
    findings = find_text_corruption(content)
    if findings:
        summary = corruption_summary(findings)
        raise RuntimeError(f"Encoding Gate Failure (Layer 1): text corruption detected before serialization: {summary}")


def jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value
