from __future__ import annotations

from datetime import datetime
from typing import Any


def normalized_activity_level(activity_level: str | None) -> str:
    value = (activity_level or "").strip().lower()
    return value or "sedentary"


def resolve_local_date(local_date: str | None) -> str:
    if isinstance(local_date, str) and local_date.strip():
        return local_date.strip()
    return datetime.now().date().isoformat()


def payload_trace_contract(payload: Any) -> dict[str, Any]:
    trace_contract = getattr(payload, "trace_contract", None) or {}
    return dict(trace_contract)


def payload_unresolved_info(payload: Any) -> list[str]:
    trace_contract = payload_trace_contract(payload)
    raw = trace_contract.get("unresolved_info") or []
    return [str(item) for item in raw if str(item).strip()]
