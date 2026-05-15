from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any

import httpx


def record_attempt_failure(
    attempt_trace: dict[str, Any],
    *,
    exc: Exception,
    response: httpx.Response | Any | None,
) -> None:
    attempt_trace["status"] = "error"
    attempt_trace["ended_at_utc"] = _utc_now_iso()
    _finish_attempt_timer(attempt_trace)
    attempt_trace["error_type"] = type(exc).__name__
    attempt_trace["error"] = str(exc)
    if isinstance(exc, httpx.HTTPStatusError):
        attempt_trace["http_status"] = exc.response.status_code
        attempt_trace["response_body_excerpt"] = (exc.response.text or "")[:1200]
        attempt_trace["response_body_truncated"] = len(exc.response.text or "") > 1200
    elif response is not None:
        attempt_trace["http_status"] = getattr(response, "status_code", None)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _finish_attempt_timer(attempt_trace: dict[str, Any]) -> None:
    started = attempt_trace.pop("_started_monotonic_s", None)
    if isinstance(started, (int, float)):
        attempt_trace["duration_ms"] = max(0, int(round((time.perf_counter() - started) * 1000)))
