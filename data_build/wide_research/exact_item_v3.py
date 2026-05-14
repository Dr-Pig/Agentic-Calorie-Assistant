from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from data_build.wide_research.common import Issue, child_output_paths, create_run_layout, read_json, write_json


SCHEMA_VERSION = "exact_item_v3"
EXACT_ITEM_SHARDS: tuple[dict[str, str], ...] = (
    {"id": "mcdonalds_tw", "title": "McDonald's Taiwan"},
    {"id": "seven_eleven_tw", "title": "7-ELEVEN Taiwan"},
    {"id": "familymart_tw", "title": "FamilyMart Taiwan"},
    {"id": "packaged_beverages_tw", "title": "Packaged beverages Taiwan"},
    {"id": "drink_chains_tw", "title": "Drink chains Taiwan"},
    {"id": "other_fast_food_tw", "title": "Other fast food Taiwan"},
)
ALLOWED_SOURCE_TYPES = {
    "official_menu_nutrition_page",
    "official_retailer_product_page",
    "official_chain_product_page",
    "official_brand_product_page",
}


def build_manifest(run_id: str) -> dict[str, Any]:
    return {"run_id": run_id, "schema_version": SCHEMA_VERSION, "shards": list(EXACT_ITEM_SHARDS)}


def make_run_id(now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%Y%m%dT%H%M%S")
    return f"exact-item-v3-{stamp}"


def scaffold_run(root: Path, *, run_id: str, schema_signature: str = "") -> Path:
    prompts = {shard["id"]: _prompt(shard, run_id) for shard in EXACT_ITEM_SHARDS}
    return create_run_layout(
        Path(root),
        run_id=run_id,
        manifest=build_manifest(run_id),
        prompts=prompts,
        schema_signature=schema_signature,
    )


def validate_child_payload(payload: Mapping[str, Any], shard: Mapping[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    shard_id = str(shard.get("id") or payload.get("shard_id") or "")
    for record in normalize_child_payload(payload).get("records") or []:
        if not isinstance(record, Mapping):
            continue
        if record.get("source_type") not in ALLOWED_SOURCE_TYPES:
            issues.append(Issue("bad_source_type", "Source type is not official enough.", shard_id, str(record.get("id") or "")))
    return issues


def normalize_child_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    records: list[dict[str, Any]] = []
    excluded = [dict(item) for item in payload.get("excluded_candidates") or [] if isinstance(item, Mapping)]
    for item in payload.get("records") or []:
        if not isinstance(item, Mapping):
            continue
        record = dict(item)
        nutrition = dict(record.get("nutrition") or {})
        for key in (
            "common_components",
            "official_serving_text",
            "source_type",
            "source_name",
            "source_url",
            "confidence",
            "last_verified_at",
            "notes",
        ):
            if key in nutrition and key not in record:
                record[key] = nutrition.pop(key)
        record["nutrition"] = nutrition
        if nutrition.get("kcal") is None:
            excluded.append(
                {
                    "id": record.get("id"),
                    "reason": "missing_kcal",
                    "source_url": record.get("source_url"),
                }
            )
            continue
        records.append(record)
    normalized["records"] = records
    normalized["excluded_candidates"] = excluded
    return normalized


def aggregate_run(run_dir: Path) -> dict[str, Any]:
    records_by_id: dict[str, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    for path in child_output_paths(Path(run_dir)):
        payload = normalize_child_payload(read_json(path))
        for record in payload.get("records") or []:
            if not isinstance(record, Mapping):
                continue
            record_id = str(record.get("id") or "")
            if record_id in records_by_id:
                duplicates.append({"id": record_id, "source_path": str(path)})
                continue
            records_by_id[record_id] = dict(record)
    return {
        "schema_version": SCHEMA_VERSION,
        "candidates": {"records": list(records_by_id.values()), "duplicates": duplicates},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["scaffold", "validate", "aggregate"])
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--run-id", default=make_run_id())
    parser.add_argument("--schema-signature", default="")
    args = parser.parse_args(argv)
    if args.command == "scaffold":
        scaffold_run(Path(args.path), run_id=args.run_id, schema_signature=args.schema_signature)
        return 0
    if args.command == "validate":
        issues = []
        for path in child_output_paths(Path(args.path)):
            payload = read_json(path)
            issues.extend(issue.to_dict() for issue in validate_child_payload(payload, {"id": payload.get("shard_id")}))
        write_json(Path(args.path) / "validation_report.json", {"issues": issues, "status": "pass" if not issues else "blocked"})
        return 0 if not issues else 1
    write_json(Path(args.path) / "aggregated_candidates.json", aggregate_run(Path(args.path)))
    return 0


def _prompt(shard: Mapping[str, str], run_id: str) -> str:
    return (
        f"# Exact item v3 / {shard['title']}\n\n"
        f"Run id: {run_id}\n\n"
        "Use official item identity. Do not merge sibling variants into one record.\n"
    )
