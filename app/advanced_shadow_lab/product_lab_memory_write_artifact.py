from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


def memory_write_artifact(
    *,
    blockers: list[str],
    written_record_ids: list[str],
    all_record_ids: list[str],
    surface_paths: Mapping[str, Path],
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_memory_write_artifact",
        "status": "blocked" if blockers else "pass",
        "written_record_ids": list(written_record_ids),
        "all_record_ids": list(all_record_ids),
        "surface_paths": {key: str(path) for key, path in dict(surface_paths).items()},
        "lab_memory_store_written": not blockers and bool(written_record_ids),
        "isolated_lab_durable_memory_written": not blockers and bool(written_record_ids),
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "blockers": blockers,
    }


__all__ = ["memory_write_artifact"]
