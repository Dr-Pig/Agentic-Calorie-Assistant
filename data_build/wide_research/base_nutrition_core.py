from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

from data_build.wide_research.common import (
    DATE_RE,
    ID_RE,
    Issue,
    child_output_paths,
    create_run_layout,
    issue_dicts,
    read_json,
    write_json,
)


BASE_NUTRITION_SHARDS: tuple[dict[str, str], ...] = (
    {"id": "grains_and_rice", "title": "Grains and rice"},
    {"id": "noodles_and_pasta", "title": "Noodles and pasta"},
    {"id": "proteins_eggs_and_meats", "title": "Proteins, eggs, and meats"},
    {"id": "vegetables_roots_and_basic_produce", "title": "Vegetables and produce"},
    {"id": "sauces_spreads_and_oils", "title": "Sauces, spreads, and oils"},
    {"id": "beverages_and_liquid_basics", "title": "Beverages and liquid basics"},
)

ALLOWED_UNIT_TYPES = {"g", "ml", "serving", "piece", "bowl", "cup", "tbsp", "tsp"}
ALLOWED_SOURCE_TYPES = {
    "government_nutrition",
    "official_brand_product_page",
    "official_chain_product_page",
    "official_retailer_product_page",
    "verified_reference",
}
ALLOWED_CONFIDENCE = {"medium", "high"}


def build_manifest(run_id: str, *, schema_version: str) -> dict[str, Any]:
    return {"run_id": run_id, "schema_version": schema_version, "shards": list(BASE_NUTRITION_SHARDS)}


def render_child_prompt(
    shard: Mapping[str, Any],
    run_id: str,
    *,
    schema_version: str,
    verified_reference_fallback: bool = False,
) -> str:
    prompt = (
        f"# Base nutrition {schema_version} / {shard['id']}\n\n"
        f"Run id: {run_id}\n\n"
        "Use canonical row selection. White rice and purple rice should not both be excluded "
        "when one canonical base row can represent the food family.\n"
    )
    if verified_reference_fallback and shard.get("id") == "sauces_spreads_and_oils":
        prompt += (
            "When official nutrition is sparse, use verified_reference fallback only after "
            "checking official_brand_product_page evidence. Include examples such as "
            "Dongquan chili sauce when appropriate.\n"
        )
    return prompt


def scaffold_run(
    root: Path,
    *,
    run_id: str,
    schema_version: str,
    schema_signature: str = "",
    verified_reference_fallback: bool = False,
) -> Path:
    prompts = {
        shard["id"]: render_child_prompt(
            shard,
            run_id,
            schema_version=schema_version,
            verified_reference_fallback=verified_reference_fallback,
        )
        for shard in BASE_NUTRITION_SHARDS
    }
    return create_run_layout(
        Path(root),
        run_id=run_id,
        manifest=build_manifest(run_id, schema_version=schema_version),
        prompts=prompts,
        schema_signature=schema_signature,
    )


def validate_run(run_dir: Path, *, schema_version: str) -> dict[str, Any]:
    run_path = Path(run_dir)
    expected_shards = {shard["id"] for shard in BASE_NUTRITION_SHARDS}
    present_shards: set[str] = set()
    issues: list[Issue] = []
    for path in child_output_paths(run_path):
        payload = read_json(path)
        shard_id = str(payload.get("shard_id") or path.stem)
        present_shards.add(shard_id)
        for record in payload.get("records") or []:
            if isinstance(record, Mapping):
                issues.extend(_validate_record(record, shard_id=shard_id))
    for shard_id in sorted(expected_shards - present_shards):
        issues.append(Issue("missing_output", "Missing child output.", shard_id=shard_id))
    return {
        "schema_version": schema_version,
        "status": "pass" if not issues else "blocked",
        "issues": issue_dicts(issues),
    }


def aggregate_run(run_dir: Path, *, schema_version: str) -> dict[str, Any]:
    records_by_id: dict[str, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    for path in child_output_paths(Path(run_dir)):
        payload = read_json(path)
        for record in payload.get("records") or []:
            if not isinstance(record, Mapping):
                continue
            record_id = str(record.get("id") or "")
            if record_id in records_by_id:
                duplicates.append({"id": record_id, "source_path": str(path)})
                continue
            records_by_id[record_id] = dict(record)
    return {
        "schema_version": schema_version,
        "candidates": {
            "records": list(records_by_id.values()),
            "duplicates": duplicates,
        },
    }


def main(argv: list[str] | None = None, *, schema_version: str, verified_reference_fallback: bool = False) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["scaffold", "validate", "aggregate"])
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--run-id", default=f"base-nutrition-{schema_version}")
    parser.add_argument("--schema-signature", default="")
    args = parser.parse_args(argv)
    if args.command == "scaffold":
        scaffold_run(
            Path(args.path),
            run_id=args.run_id,
            schema_version=schema_version,
            schema_signature=args.schema_signature,
            verified_reference_fallback=verified_reference_fallback,
        )
        return 0
    if args.command == "validate":
        report = validate_run(Path(args.path), schema_version=schema_version)
        write_json(Path(args.path) / "validation_report.json", report)
        return 0 if report["status"] == "pass" else 1
    aggregate = aggregate_run(Path(args.path), schema_version=schema_version)
    write_json(Path(args.path) / "aggregated_candidates.json", aggregate)
    return 0


def _validate_record(record: Mapping[str, Any], *, shard_id: str) -> list[Issue]:
    record_id = str(record.get("id") or "")
    issues: list[Issue] = []
    if not ID_RE.match(record_id):
        issues.append(Issue("bad_id", "Record id must be lowercase kebab-case.", shard_id, record_id))
    serving = record.get("serving_basis") if isinstance(record.get("serving_basis"), Mapping) else {}
    if serving.get("unit_type") not in ALLOWED_UNIT_TYPES or _number(serving.get("amount")) <= 0:
        issues.append(Issue("bad_unit_type", "Serving unit or amount is invalid.", shard_id, record_id))
    nutrition = record.get("nutrition") if isinstance(record.get("nutrition"), Mapping) else {}
    if any(_number(nutrition.get(key)) < 0 for key in ("protein_g", "carb_g", "fat_g", "kcal")):
        issues.append(Issue("bad_nutrition", "Nutrition values must be non-negative.", shard_id, record_id))
    if record.get("source_type") not in ALLOWED_SOURCE_TYPES:
        issues.append(Issue("bad_source_type", "Source type is not approved.", shard_id, record_id))
    if record.get("confidence") not in ALLOWED_CONFIDENCE:
        issues.append(Issue("bad_confidence", "Confidence must be medium or high.", shard_id, record_id))
    if not DATE_RE.match(str(record.get("last_verified_at") or "")):
        issues.append(Issue("bad_last_verified_at", "Date must be YYYY-MM-DD.", shard_id, record_id))
    return issues


def _number(value: Any) -> float:
    return float(value) if isinstance(value, int | float) else 0.0
