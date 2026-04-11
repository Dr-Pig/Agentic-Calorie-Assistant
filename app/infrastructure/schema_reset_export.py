from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ..paths import RUNTIME_ARTIFACT_DIR, ensure_runtime_dirs


ensure_runtime_dirs()

SCHEMA_RESET_EXPORT_DIR = RUNTIME_ARTIFACT_DIR / "schema_reset_exports"
LEGACY_TABLES = ("users", "meal_logs", "message_buffer")
CANONICAL_TABLES = (
    "meal_threads",
    "meal_versions",
    "meal_items",
    "day_budget_ledger",
    "ledger_entries",
    "body_observations",
    "body_plans",
    "proposal_containers",
    "proposal_options",
    "proactive_triggers",
    "legacy_meal_log_map",
)


def _fetch_rows(session: Session, table_name: str, limit: int) -> list[dict[str, Any]]:
    rows = session.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}")).mappings().all()
    return [dict(row) for row in rows]


def export_schema_reset_snapshot(
    session: Session,
    *,
    output_root: Path | None = None,
    sample_limit: int = 50,
    label: str | None = None,
) -> Path:
    engine: Engine = session.get_bind()
    output_root = output_root or SCHEMA_RESET_EXPORT_DIR
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{timestamp}_{label}" if label else timestamp
    export_dir = output_root / folder_name
    export_dir.mkdir(parents=True, exist_ok=True)

    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "dialect": engine.dialect.name,
        "tables": tables,
        "legacy_tables": [t for t in LEGACY_TABLES if t in tables],
        "canonical_tables": [t for t in CANONICAL_TABLES if t in tables],
        "sample_limit": sample_limit,
    }
    (export_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    schema_dump = {}
    for table_name in tables:
        schema_dump[table_name] = [
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": bool(col["nullable"]),
                "default": str(col["default"]) if col["default"] is not None else None,
            }
            for col in inspector.get_columns(table_name)
        ]
    (export_dir / "schema.json").write_text(json.dumps(schema_dump, ensure_ascii=False, indent=2), encoding="utf-8")

    samples = {}
    for table_name in metadata["legacy_tables"] + metadata["canonical_tables"]:
        samples[table_name] = _fetch_rows(session, table_name, sample_limit)
    (export_dir / "sample_rows.json").write_text(json.dumps(samples, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    if engine.dialect.name == "sqlite":
        sqlite_master = session.execute(
            text("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE type IN ('table', 'index') ORDER BY type, name")
        ).mappings().all()
        (export_dir / "sqlite_master.json").write_text(
            json.dumps([dict(row) for row in sqlite_master], ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    return export_dir

