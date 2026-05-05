from __future__ import annotations

from copy import deepcopy
from typing import Any

RUNTIME_METADATA_KEYS = (
    "runtime_role",
    "runtime_estimate_allowed",
    "runtime_truth_allowed",
    "serving_basis",
    "portion_basis",
    "kcal_point",
    "kcal_range",
    "source_refs",
    "source_provenance",
    "source_posture_flags",
    "approval_metadata",
    "range_policy",
    "runtime_usage_boundary",
    "kcal_basis",
)


def apply_runtime_anchor_batch_to_small_anchor_store(
    small_anchor_payload: dict[str, Any],
    runtime_batch: dict[str, Any],
) -> dict[str, Any]:
    metadata_by_id = {
        anchor["anchor_id"]: anchor
        for anchor in runtime_batch.get("anchors") or []
        if isinstance(anchor, dict) and anchor.get("anchor_id")
    }
    updated = deepcopy(small_anchor_payload)
    for item in updated.get("anchors") or []:
        anchor_id = item.get("anchor_id")
        metadata = metadata_by_id.get(anchor_id)
        if not metadata:
            continue
        for key in RUNTIME_METADATA_KEYS:
            item[key] = metadata[key]
        item["baseline_likely_kcal"] = metadata["kcal_point"]
        item["baseline_kcal_range"] = metadata["kcal_range"]
    return updated


__all__ = ["RUNTIME_METADATA_KEYS", "apply_runtime_anchor_batch_to_small_anchor_store"]
