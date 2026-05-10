from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.composition.accurate_intake_local_operator_data_hygiene_bundle import (
    build_local_operator_data_hygiene_bundle,
)
from app.composition.local_dogfood_data_hygiene import backup_local_dogfood_db, export_local_dogfood_db
from app.database import get_db
from app.runtime.interface.local_debug_auth import require_local_debug_access

router = APIRouter()
DOGFOOD_BACKUP_DIR = Path("workspace_data/local_dogfood_backups")
DOGFOOD_EXPORT_DIR = Path("workspace_data/local_dogfood_exports")
DOGFOOD_FEEDBACK_DIR = Path("workspace_data/local_dogfood_feedback")
DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH = Path("artifacts/accurate_intake_dogfood_review_queue.json")


def _local_sqlite_db_path(db: Any) -> Path:
    bind = db.get_bind() if hasattr(db, "get_bind") else getattr(db, "bind", None)
    database = getattr(getattr(bind, "url", None), "database", None)
    if not database or str(database) == ":memory:":
        raise HTTPException(status_code=400, detail="local_sqlite_db_path_unavailable")
    return Path(str(database))


def _label_from_payload(payload: dict[str, Any], *, fallback: str) -> str:
    label = str(payload.get("label") or "").strip()
    return label or fallback


@router.get("/accurate-intake/local-data-hygiene")
async def accurate_intake_local_data_hygiene(
    db: Any = Depends(get_db),
    _local_debug_access: None = Depends(require_local_debug_access),
) -> dict[str, Any]:
    return build_local_operator_data_hygiene_bundle(
        db_path=_local_sqlite_db_path(db),
        backup_dir=DOGFOOD_BACKUP_DIR,
        export_dir=DOGFOOD_EXPORT_DIR,
    )


@router.post("/accurate-intake/local-data-hygiene/backup")
async def accurate_intake_local_data_hygiene_backup(
    payload: dict[str, Any] | None = Body(default=None),
    db: Any = Depends(get_db),
    _local_debug_access: None = Depends(require_local_debug_access),
) -> dict[str, Any]:
    payload = payload or {}
    return backup_local_dogfood_db(
        db_path=_local_sqlite_db_path(db),
        backup_dir=DOGFOOD_BACKUP_DIR,
        label=_label_from_payload(payload, fallback="browser-backup"),
    )


@router.post("/accurate-intake/local-data-hygiene/export")
async def accurate_intake_local_data_hygiene_export(
    payload: dict[str, Any] | None = Body(default=None),
    db: Any = Depends(get_db),
    _local_debug_access: None = Depends(require_local_debug_access),
) -> dict[str, Any]:
    payload = payload or {}
    return export_local_dogfood_db(
        db_path=_local_sqlite_db_path(db),
        export_dir=DOGFOOD_EXPORT_DIR,
        label=_label_from_payload(payload, fallback="browser-export"),
        feedback_jsonl_path=DOGFOOD_FEEDBACK_DIR / "accurate_intake_dogfood_feedback.jsonl",
        review_queue_artifact_path=DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH,
    )
