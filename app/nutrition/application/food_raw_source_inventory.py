from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from app.nutrition.application.food_raw_source_file_inspection import (
    XLSX_PARSE_EXCEPTIONS,  # noqa: F401 - direct-import compatibility from this facade.
    inspect_csv,
    inspect_json,
    inspect_xlsx,
)
from app.nutrition.application.food_raw_source_file_locator import (
    find_source_file,
    path_hash,
    relative_to_root,
)
from app.nutrition.application.food_raw_source_registry import (
    NON_CLAIM_FLAGS,
    RAW_SOURCE_DEFINITIONS,
    RawSourceDefinition,
    build_raw_source_registry_artifact,
    pipeline_stage_boundary,
)


def build_food_raw_source_registry() -> dict[str, Any]:
    return build_raw_source_registry_artifact()


def build_food_raw_source_inventory(scan_roots: Iterable[Path | str]) -> dict[str, Any]:
    roots = [Path(root) for root in scan_roots]
    entries = [
        _inventory_entry(definition, roots)
        for definition in RAW_SOURCE_DEFINITIONS
    ]
    present_count = sum(1 for entry in entries if entry["local_path_present"] is True)
    return {
        "artifact_type": "accurate_intake_food_raw_source_inventory",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "claim_scope": "raw_source_inventory_only",
        "truth_owner": "none",
        "semantic_owner": "none",
        "runtime_truth": False,
        **NON_CLAIM_FLAGS,
        "pipeline_stage_boundary": pipeline_stage_boundary(),
        "scan_summary": {
            "scan_root_count": len(roots),
            "present_count": present_count,
            "absent_count": len(entries) - present_count,
        },
        "inventory_entries": entries,
    }


def _inventory_entry(definition: RawSourceDefinition, scan_roots: list[Path]) -> dict[str, Any]:
    match = find_source_file(definition.filename, scan_roots)
    base = definition.as_dict()
    base.update(
        {
            "local_path_present": False,
            "extension": Path(definition.filename).suffix.lower(),
            "file_size": None,
            "path_hash": None,
            "relative_to_scan_root": None,
            "row_count": None,
        }
    )
    if match is None:
        return base

    path, root = match
    base.update(
        {
            "local_path_present": True,
            "file_size": path.stat().st_size,
            "path_hash": path_hash(path),
            "relative_to_scan_root": relative_to_root(path, root),
        }
    )
    suffix = path.suffix.lower()
    if suffix == ".json":
        base.update(inspect_json(path))
    elif suffix == ".csv":
        base.update(inspect_csv(path))
    elif suffix == ".xlsx":
        base.update(inspect_xlsx(path))
    return base


__all__ = [
    "RAW_SOURCE_DEFINITIONS",
    "build_food_raw_source_inventory",
    "build_food_raw_source_registry",
]
