from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..paths import RUNTIME_LOG_DIR, ensure_runtime_dirs


ensure_runtime_dirs()

STAGE_TRACE_DIR = RUNTIME_LOG_DIR / "stage_traces"


def append_stage_trace_event(request_id: str, event: dict[str, Any]) -> Path:
    STAGE_TRACE_DIR.mkdir(parents=True, exist_ok=True)
    path = STAGE_TRACE_DIR / f"{request_id}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return path


def read_stage_trace_events(request_id: str) -> list[dict[str, Any]]:
    path = STAGE_TRACE_DIR / f"{request_id}.jsonl"
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events

