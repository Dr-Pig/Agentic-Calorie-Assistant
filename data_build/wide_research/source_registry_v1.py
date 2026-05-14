from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

from data_build.wide_research.common import Issue, child_output_paths, create_run_layout, issue_dicts, read_json, write_json


SCHEMA_VERSION = "source_registry_v1"
SOURCE_FAMILY_SHARDS: tuple[dict[str, str], ...] = (
    {"id": "tw_gov_nutrition", "title": "Taiwan government nutrition"},
    {"id": "tw_packaged_beverage_official", "title": "Taiwan packaged beverage official"},
    {"id": "tw_convenience_store_official", "title": "Taiwan convenience store official"},
    {"id": "tw_fast_food_chain_official", "title": "Taiwan fast food chain official"},
    {"id": "tw_chain_restaurant_nutrition", "title": "Taiwan chain restaurant nutrition"},
    {"id": "tw_drink_chain_official", "title": "Taiwan drink chain official"},
    {"id": "tw_retailer_official_product_pages", "title": "Taiwan retailer product pages"},
    {"id": "tw_pattern_reference_candidates", "title": "Pattern reference candidates"},
)


def build_manifest(run_id: str) -> dict[str, Any]:
    return {"run_id": run_id, "schema_version": SCHEMA_VERSION, "shards": list(SOURCE_FAMILY_SHARDS)}


def scaffold_run(root: Path, *, run_id: str, schema_signature: str = "") -> Path:
    prompts = {shard["id"]: _prompt(shard, run_id) for shard in SOURCE_FAMILY_SHARDS}
    return create_run_layout(
        Path(root),
        run_id=run_id,
        manifest=build_manifest(run_id),
        prompts=prompts,
        schema_signature=schema_signature,
    )


def validate_run(run_dir: Path) -> dict[str, Any]:
    expected_shards = {shard["id"] for shard in SOURCE_FAMILY_SHARDS}
    present_shards: set[str] = set()
    issues: list[Issue] = []
    for path in child_output_paths(Path(run_dir)):
        payload = read_json(path)
        shard_id = str(payload.get("shard_id") or path.stem)
        present_shards.add(shard_id)
        for source in payload.get("sources") or []:
            if isinstance(source, Mapping):
                issues.extend(_validate_source(source, shard_id=shard_id))
    for shard_id in sorted(expected_shards - present_shards):
        issues.append(Issue("missing_output", "Missing source output.", shard_id=shard_id))
    return {"schema_version": SCHEMA_VERSION, "status": "pass" if not issues else "blocked", "issues": issue_dicts(issues)}


def aggregate_run(run_dir: Path) -> dict[str, Any]:
    sources_by_id: dict[str, dict[str, Any]] = {}
    url_index: dict[str, str] = {}
    conflicts: list[dict[str, Any]] = []
    for path in child_output_paths(Path(run_dir)):
        payload = read_json(path)
        for source in payload.get("sources") or []:
            if not isinstance(source, Mapping):
                continue
            source_id = str(source.get("id") or "")
            url = str(source.get("url") or "")
            if source_id in sources_by_id:
                continue
            if url and url in url_index:
                conflicts.append(
                    {
                        "url": url,
                        "existing_id": url_index[url],
                        "candidate_id": source_id,
                        "source_path": str(path),
                    }
                )
                continue
            sources_by_id[source_id] = dict(source)
            if url:
                url_index[url] = source_id
    return {
        "schema_version": SCHEMA_VERSION,
        "candidates": {"sources": list(sources_by_id.values()), "conflicts": conflicts},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["scaffold", "validate", "aggregate"])
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--run-id", default="source-registry-v1")
    parser.add_argument("--schema-signature", default="")
    args = parser.parse_args(argv)
    if args.command == "scaffold":
        scaffold_run(Path(args.path), run_id=args.run_id, schema_signature=args.schema_signature)
        return 0
    if args.command == "validate":
        report = validate_run(Path(args.path))
        write_json(Path(args.path) / "validation_report.json", report)
        return 0 if report["status"] == "pass" else 1
    write_json(Path(args.path) / "aggregated_sources.json", aggregate_run(Path(args.path)))
    return 0


def _validate_source(source: Mapping[str, Any], *, shard_id: str) -> list[Issue]:
    source_id = str(source.get("id") or "")
    issues: list[Issue] = []
    if source.get("tier") == "P2" and "base_nutrition" in (source.get("applies_to") or []):
        issues.append(Issue("p2_scope_violation", "P2 sources may not seed base nutrition.", shard_id, source_id))
    if shard_id == "tw_pattern_reference_candidates" and source.get("source_type") == "nutrition_aggregator":
        issues.append(Issue("shard_source_type_violation", "Aggregator source is not valid for this shard.", shard_id, source_id))
    return issues


def _prompt(shard: Mapping[str, str], run_id: str) -> str:
    return f"# Source registry v1 / {shard['title']}\n\nRun id: {run_id}\n"
