from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

DogfoodDataOperation = Literal["inspect", "backup", "reset", "export"]

_DISPOSABLE_PATH_PARTS = {
    ".pytest_tmp_local",
    "pytest_tmp_local",
    "artifacts",
}
_DISPOSABLE_NAME_TOKENS = {
    "fixture",
    "smoke",
    "test",
    "browser",
    "bridge",
}
_REAL_DOGFOOD_PATH_PARTS = {
    "real_dogfood",
    "local_dogfood",
}


def _generated_at() -> str:
    return datetime.now(UTC).isoformat()


def _is_disposable_path(db_path: Path) -> bool:
    parts = set(db_path.parts)
    if parts & _REAL_DOGFOOD_PATH_PARTS:
        return False
    name = db_path.name.lower()
    if parts & _DISPOSABLE_PATH_PARTS:
        return True
    return any(token in name for token in _DISPOSABLE_NAME_TOKENS)


def classify_local_dogfood_db(db_path: Path) -> dict:
    db_class = "fixture_smoke_db" if _is_disposable_path(db_path) else "real_dogfood_db"
    real_dogfood = db_class == "real_dogfood_db"
    return {
        "db_path": str(db_path),
        "db_class": db_class,
        "real_dogfood_data": real_dogfood,
        "disposable": not real_dogfood,
        "backup_required_before_reset": real_dogfood,
        "local_only": True,
        "contains_personal_diet_logs": real_dogfood,
        "do_not_commit": True,
    }


def build_local_dogfood_data_manifest(
    *,
    db_path: Path,
    operation: DogfoodDataOperation | str,
    backup_path: Path | None = None,
) -> dict:
    classification = classify_local_dogfood_db(db_path)
    operation_value = str(operation)
    blockers: list[str] = []
    if (
        operation_value == "reset"
        and classification["backup_required_before_reset"] is True
        and backup_path is None
    ):
        blockers.append("backup_required_before_reset")
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_local_dogfood_data_hygiene",
        "generated_at_utc": _generated_at(),
        "operation": operation_value,
        "allowed": not blockers,
        "blockers": blockers,
        "reset_without_backup_allowed": classification["backup_required_before_reset"] is False,
        "backup_path": str(backup_path) if backup_path is not None else None,
        **classification,
    }


def backup_local_dogfood_db(
    *,
    db_path: Path,
    backup_dir: Path,
    label: str = "manual-backup",
) -> dict:
    if not db_path.exists():
        manifest = build_local_dogfood_data_manifest(db_path=db_path, operation="backup")
        return {**manifest, "status": "blocked", "blockers": ["db_path_missing"]}

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{db_path.stem}.{label}.{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    manifest = {
        **build_local_dogfood_data_manifest(
            db_path=db_path,
            operation="backup",
            backup_path=backup_path,
        ),
        "status": "pass",
        "backup_path": str(backup_path),
    }
    manifest_path = backup_dir / f"{backup_path.stem}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": str(manifest_path)}


__all__ = [
    "backup_local_dogfood_db",
    "build_local_dogfood_data_manifest",
    "classify_local_dogfood_db",
]
