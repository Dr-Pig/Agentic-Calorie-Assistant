from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ....paths import REQUEST_TRACE_DIR


def stage_trace_path(request_id: str) -> Path:
    stage_dir = REQUEST_TRACE_DIR / "stage_events"
    return stage_dir / f"{request_id}.jsonl"


def append_stage_trace_event(request_id: str, payload: dict[str, Any]) -> Path:
    stage_dir = REQUEST_TRACE_DIR / "stage_events"
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_trace_path(request_id)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str))
        handle.write("\n")
    return path
