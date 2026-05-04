from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from app.composition.local_dogfood_data_hygiene import (
    build_local_dogfood_data_manifest,
    import_preview_local_dogfood_export,
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _copy_operation_preview(*, db_path: Path, operation: str, output_dir: Path) -> dict[str, Any]:
    base_manifest = build_local_dogfood_data_manifest(
        db_path=db_path,
        operation=f"{operation}-preview",
    )
    blockers: list[str] = []
    if not db_path.exists():
        blockers.append("db_path_missing")
    return {
        "operation": f"{operation}-preview",
        "status": "ready" if not blockers else "blocked",
        "allowed": not blockers,
        "blockers": blockers,
        "db_path": str(db_path),
        "output_dir": str(output_dir),
        "would_write_copy": not blockers,
        "writes_performed": False,
        "local_only": True,
        "contains_personal_diet_logs": base_manifest["contains_personal_diet_logs"],
        "do_not_commit": True,
    }


def _import_preview_summary(
    *,
    import_manifest_path: Path | None,
    target_db_path: Path,
) -> dict[str, Any]:
    if import_manifest_path is None:
        return {
            "operation": "import-preview",
            "status": "not_checked",
            "allowed": False,
            "blockers": ["import_manifest_not_provided"],
            "source_manifest_path": None,
            "target_db_path": str(target_db_path),
            "import_allowed": False,
            "writes_performed": False,
            "local_only": True,
            "contains_personal_diet_logs": build_local_dogfood_data_manifest(
                db_path=target_db_path,
                operation="import-preview",
            )["contains_personal_diet_logs"],
            "do_not_commit": True,
        }
    return import_preview_local_dogfood_export(
        export_manifest_path=import_manifest_path,
        target_db_path=target_db_path,
    )


def _blockers_from_import_preview(import_preview: dict[str, Any]) -> list[str]:
    if import_preview.get("status") in {"pass", "not_checked"}:
        return []
    return [f"import_preview.{blocker}" for blocker in import_preview.get("blockers", [])]


def build_local_operator_data_hygiene_bundle(
    *,
    db_path: Path,
    backup_dir: Path | None = None,
    export_dir: Path | None = None,
    import_manifest_path: Path | None = None,
) -> dict[str, Any]:
    backup_dir = backup_dir or Path("workspace_data/local_dogfood_backups")
    export_dir = export_dir or Path("workspace_data/local_dogfood_exports")
    inspect_manifest = build_local_dogfood_data_manifest(db_path=db_path, operation="inspect")
    reset_guard = build_local_dogfood_data_manifest(db_path=db_path, operation="reset")
    backup_preview = _copy_operation_preview(
        db_path=db_path,
        operation="backup",
        output_dir=backup_dir,
    )
    export_preview = _copy_operation_preview(
        db_path=db_path,
        operation="export",
        output_dir=export_dir,
    )
    import_preview = _import_preview_summary(
        import_manifest_path=import_manifest_path,
        target_db_path=db_path,
    )
    blockers = [
        *([] if inspect_manifest.get("db_path") else ["inspect.db_path_missing"]),
        *_blockers_from_import_preview(import_preview),
    ]
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_local_operator_data_hygiene_bundle",
            "claim_scope": "local_operator_data_hygiene_review_checkpoint",
            "status": "local_operator_data_hygiene_ready" if not blockers else "blocked",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "blockers": blockers,
            "db_path": str(db_path),
            "db_class": inspect_manifest["db_class"],
            "real_dogfood_data": inspect_manifest["real_dogfood_data"],
            "disposable": inspect_manifest["disposable"],
            "backup_required_before_reset": inspect_manifest["backup_required_before_reset"],
            "reset_without_backup_allowed": reset_guard["reset_without_backup_allowed"],
            "local_only": True,
            "contains_personal_diet_logs": inspect_manifest["contains_personal_diet_logs"],
            "do_not_commit": True,
            "writes_performed": False,
            "import_allowed": False,
            "operation_previews": {
                "inspect": inspect_manifest,
                "reset_guard": reset_guard,
                "backup": backup_preview,
                "export": export_preview,
                "import_preview": import_preview,
            },
            "review_checkpoints": [
                "real_dogfood_reset_requires_backup",
                "backup_export_are_local_only_sqlite_copy_operations",
                "import_preview_never_writes_target_db",
                "personal_diet_logs_do_not_commit",
            ],
            "fooddb_truth_updated": False,
            "production_db_used": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "ready_for_fdb_integration": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        }
    )


__all__ = ["build_local_operator_data_hygiene_bundle"]
