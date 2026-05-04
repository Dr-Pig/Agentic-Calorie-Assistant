from __future__ import annotations

import json
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

DogfoodDataOperation = Literal["inspect", "backup", "reset", "export", "import-preview"]

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_GENERATED_ROOTS = (
    ROOT / ".pytest_tmp_local",
    ROOT / "artifacts",
    ROOT / "workspace_data" / "local_dogfood_exports",
    ROOT / "workspace_data" / "local_dogfood_backups",
    Path(tempfile.gettempdir()),
)

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


def _resolved_path(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def _path_is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _generated_path_blockers(path: Path, *, kind: str) -> list[str]:
    resolved = _resolved_path(path)
    allowed_roots = [_resolved_path(root) for root in ALLOWED_GENERATED_ROOTS]
    if any(_path_is_under(resolved, root) for root in allowed_roots):
        return []
    return [f"{kind}_outside_allowed_local_roots"]


def _sanitize_label(label: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", label.strip())
    sanitized = re.sub(r"-+", "-", sanitized)
    sanitized = sanitized.strip(".-_")
    while ".." in sanitized:
        sanitized = sanitized.replace("..", ".")
    return sanitized or "manual-backup"


def _is_disposable_path(db_path: Path) -> bool:
    parts = {part.lower() for part in db_path.parts}
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
    path_blockers = _generated_path_blockers(backup_dir, kind="backup_dir")
    if path_blockers:
        manifest = build_local_dogfood_data_manifest(db_path=db_path, operation="backup")
        return {**manifest, "status": "blocked", "allowed": False, "blockers": path_blockers}

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_label = _sanitize_label(label)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{db_path.stem}.{safe_label}.{timestamp}{db_path.suffix}"
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


def export_local_dogfood_db(
    *,
    db_path: Path,
    export_dir: Path,
    label: str = "manual-export",
) -> dict:
    if not db_path.exists():
        manifest = build_local_dogfood_data_manifest(db_path=db_path, operation="export")
        return {**manifest, "status": "blocked", "blockers": ["db_path_missing"]}
    path_blockers = _generated_path_blockers(export_dir, kind="export_dir")
    if path_blockers:
        manifest = build_local_dogfood_data_manifest(db_path=db_path, operation="export")
        return {**manifest, "status": "blocked", "allowed": False, "blockers": path_blockers}

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_label = _sanitize_label(label)
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"{db_path.stem}.{safe_label}.{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, export_path)
    manifest = {
        **build_local_dogfood_data_manifest(db_path=db_path, operation="export"),
        "status": "pass",
        "export_format": "sqlite_copy_with_manifest",
        "export_contains_sqlite_copy": True,
        "export_path": str(export_path),
        "export_manifest_contains_personal_log_paths": True,
    }
    manifest_path = export_dir / f"{export_path.stem}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": str(manifest_path)}


def import_preview_local_dogfood_export(
    *,
    export_manifest_path: Path,
    target_db_path: Path,
) -> dict:
    blockers: list[str] = []
    source_manifest: dict = {}
    if not export_manifest_path.exists():
        blockers.append("export_manifest_missing")
    else:
        try:
            source_manifest = json.loads(export_manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            blockers.append("export_manifest_invalid_json")
    if source_manifest:
        if source_manifest.get("operation") != "export":
            blockers.append("export_manifest_not_export_operation")
        if source_manifest.get("local_only") is not True:
            blockers.append("export_manifest_not_local_only")
        if source_manifest.get("do_not_commit") is not True:
            blockers.append("export_manifest_missing_do_not_commit")
        export_path_value = source_manifest.get("export_path")
        if not export_path_value:
            blockers.append("export_sqlite_copy_missing")
        else:
            export_path = Path(str(export_path_value))
            if not export_path.exists():
                blockers.append("export_sqlite_copy_missing")
    classification = classify_local_dogfood_db(target_db_path)
    personal_logs = bool(
        source_manifest.get("contains_personal_diet_logs") or classification["contains_personal_diet_logs"]
    )
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_local_dogfood_import_preview",
        "generated_at_utc": _generated_at(),
        "operation": "import-preview",
        "status": "pass" if not blockers else "blocked",
        "allowed": not blockers,
        "blockers": blockers,
        "import_allowed": False,
        "writes_performed": False,
        "source_manifest_path": str(export_manifest_path),
        "source_export_path": source_manifest.get("export_path"),
        "target_db_path": str(target_db_path),
        "target_db_class": classification["db_class"],
        "local_only": True,
        "contains_personal_diet_logs": personal_logs,
        "do_not_commit": True,
    }


__all__ = [
    "backup_local_dogfood_db",
    "build_local_dogfood_data_manifest",
    "classify_local_dogfood_db",
    "export_local_dogfood_db",
    "import_preview_local_dogfood_export",
]
