from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.shared.infra.json_artifacts import write_json_artifact


SAFE_SEGMENT_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
)


def unsafe_segment_blocker(name: str, value: str) -> str | None:
    if not value or any(char not in SAFE_SEGMENT_CHARS for char in value):
        return f"{name}.unsafe_path_segment"
    if value in {".", ".."}:
        return f"{name}.unsafe_path_segment"
    return None


def session_dir(*, artifact_root: Path | str, session_id: str) -> Path:
    return (
        Path(artifact_root)
        .resolve(strict=False)
        / "advanced_product_lab"
        / "sessions"
        / session_id
    )


def turn_artifact_path(
    *,
    artifact_root: Path | str,
    session_id: str,
    turn_id: str,
) -> Path:
    return session_dir(artifact_root=artifact_root, session_id=session_id) / "turns" / f"{turn_id}.json"


def session_artifact_path(*, artifact_root: Path | str, session_id: str) -> Path:
    return session_dir(artifact_root=artifact_root, session_id=session_id) / "session_artifact.json"


def write_turn_record(
    *,
    artifact_root: Path | str,
    session_id: str,
    turn_id: str,
    record: Mapping[str, Any],
) -> Path:
    path = turn_artifact_path(
        artifact_root=artifact_root,
        session_id=session_id,
        turn_id=turn_id,
    )
    write_json_artifact(path, dict(record))
    return path


def write_session_record(
    *,
    artifact_root: Path | str,
    session_id: str,
    artifact: Mapping[str, Any],
) -> Path:
    path = session_artifact_path(artifact_root=artifact_root, session_id=session_id)
    write_json_artifact(path, dict(artifact))
    return path


def write_final_session_record(
    *,
    artifact_root: Path | str,
    session_id: str,
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    path = session_artifact_path(artifact_root=artifact_root, session_id=session_id)
    final_artifact = {**dict(artifact), "session_artifact_path": str(path)}
    write_json_artifact(path, final_artifact)
    return final_artifact


__all__ = [
    "session_artifact_path",
    "session_dir",
    "turn_artifact_path",
    "unsafe_segment_blocker",
    "write_final_session_record",
    "write_session_record",
    "write_turn_record",
]
