from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .schemas import AuditEvent


LOG_DIR = Path(__file__).resolve().parent.parent / ".logs"
LOG_FILE = LOG_DIR / "text_meal_events.jsonl"


def append_audit_event(event: AuditEvent) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(event.model_dump_json(ensure_ascii=False) + "\n")


def read_recent_events(limit: int = 20) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    records: list[dict] = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(records))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
