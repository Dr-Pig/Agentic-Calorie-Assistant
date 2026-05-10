from __future__ import annotations

import json
import re
from hashlib import sha1
from pathlib import Path
from typing import Any


def sanitize_artifact_label(label: str, *, fallback: str = "manual") -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", label.strip())
    sanitized = re.sub(r"-+", "-", sanitized)
    sanitized = sanitized.strip(".-_")
    while ".." in sanitized:
        sanitized = sanitized.replace("..", ".")
    return sanitized or fallback


def compact_dogfood_copy_name(*, db_path: Path, label: str, timestamp: str) -> str:
    stem = sanitize_artifact_label(db_path.stem, fallback="dogfood-db")[:24].strip(".-_") or "dogfood-db"
    label_part = sanitize_artifact_label(label, fallback="manual")[:32].strip(".-_") or "manual"
    digest = sha1(f"{db_path.stem}|{label}".encode("utf-8")).hexdigest()[:8]
    return f"{stem}.{label_part}.{digest}.{timestamp}{db_path.suffix}"


def write_json_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


__all__ = [
    "compact_dogfood_copy_name",
    "sanitize_artifact_label",
    "write_json_manifest",
]
