from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def artifact_io_path(path: Path) -> str:
    if os.name != "nt":
        return str(path)

    absolute = path.resolve(strict=False)
    raw = str(absolute)
    if raw.startswith("\\\\?\\"):
        return raw
    if raw.startswith("\\\\"):
        return "\\\\?\\UNC\\" + raw.lstrip("\\")
    return "\\\\?\\" + raw


def write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    os.makedirs(artifact_io_path(path.parent), exist_ok=True)
    with open(artifact_io_path(path), "w", encoding="utf-8") as output:
        output.write(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n"
        )


def artifact_path_exists(path: Path) -> bool:
    return os.path.exists(artifact_io_path(path))


def read_json_artifact(path: Path) -> dict[str, Any]:
    with open(artifact_io_path(path), encoding="utf-8-sig") as source:
        payload = json.loads(source.read())
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


__all__ = [
    "artifact_io_path",
    "artifact_path_exists",
    "read_json_artifact",
    "write_json_artifact",
]
