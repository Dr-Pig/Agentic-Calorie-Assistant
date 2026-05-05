from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def find_source_file(filename: str, scan_roots: list[Path]) -> Path | None:
    for root in scan_roots:
        if not root.exists():
            continue
        if root.is_file() and root.name == filename:
            return root
        if root.is_dir():
            direct = root / filename
            if direct.exists():
                return direct
            for candidate in root.rglob(filename):
                if candidate.is_file():
                    return candidate
    return None


def json_records(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        records = payload.get("records")
        if isinstance(records, list):
            return records
        products = payload.get("products")
        if isinstance(products, list):
            return products
    return []


def schema_keys(records: list[Any]) -> list[str]:
    return sorted(
        {
            str(key)
            for record in records
            if isinstance(record, dict)
            for key in record.keys()
        }
    )


def csv_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(record) for record in csv.DictReader(handle)]


__all__ = [
    "csv_records",
    "find_source_file",
    "json_records",
    "schema_keys",
]
