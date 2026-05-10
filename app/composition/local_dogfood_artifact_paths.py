from __future__ import annotations

import re
import os
import shutil
from hashlib import sha1
from pathlib import Path
from typing import Any

from app.shared.infra.json_artifacts import artifact_io_path, write_json_artifact


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
    write_json_artifact(path, payload)


def copy_local_artifact_file(source: Path, target: Path) -> None:
    os.makedirs(artifact_io_path(target.parent), exist_ok=True)
    with open(artifact_io_path(source), "rb") as source_file, open(
        artifact_io_path(target),
        "wb",
    ) as target_file:
        shutil.copyfileobj(source_file, target_file)


__all__ = [
    "compact_dogfood_copy_name",
    "copy_local_artifact_file",
    "sanitize_artifact_label",
    "write_json_manifest",
]
