from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from data_build.wide_research import base_nutrition_core as core


SCHEMA_VERSION = "base_nutrition_v2"
BASE_NUTRITION_SHARDS = core.BASE_NUTRITION_SHARDS


def render_child_prompt(shard: Mapping[str, Any], run_id: str) -> str:
    return core.render_child_prompt(shard, run_id, schema_version=SCHEMA_VERSION)


def scaffold_run(root: Path, *, run_id: str, schema_signature: str = "") -> Path:
    return core.scaffold_run(root, run_id=run_id, schema_version=SCHEMA_VERSION, schema_signature=schema_signature)


def validate_run(run_dir: Path) -> dict[str, Any]:
    return core.validate_run(run_dir, schema_version=SCHEMA_VERSION)


def aggregate_run(run_dir: Path) -> dict[str, Any]:
    return core.aggregate_run(run_dir, schema_version=SCHEMA_VERSION)


def main(argv: list[str] | None = None) -> int:
    return core.main(argv, schema_version=SCHEMA_VERSION)
