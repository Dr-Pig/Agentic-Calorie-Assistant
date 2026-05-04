from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def build_fooddb_modifier_catalog(
    *,
    small_anchor_payload: dict[str, Any],
) -> dict[str, Any]:
    runtime_anchors = _runtime_common_serving_anchors(small_anchor_payload)
    modifier_aware_anchors = [
        anchor for anchor in runtime_anchors if anchor.get("major_modifiers")
    ]
    modifier_groups = _modifier_groups(modifier_aware_anchors)

    return {
        "artifact_type": "accurate_intake_fooddb_modifier_catalog",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "fooddb_modifier_catalog_report_only",
        "runtime_truth_changed": False,
        "product_loop_integration_claimed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "summary": {
            "runtime_common_serving_anchor_count": len(runtime_anchors),
            "modifier_aware_anchor_count": len(modifier_aware_anchors),
            "modifier_name_count": len(modifier_groups),
        },
        "modifier_groups": modifier_groups,
        "manager_modifier_catalog": _manager_modifier_catalog(modifier_aware_anchors),
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_product_loop_integration",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_live_provider_call",
        ],
    }


def _runtime_common_serving_anchors(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        anchor
        for anchor in payload.get("anchors") or []
        if isinstance(anchor, dict)
        and anchor.get("record_kind") == "generic_anchor"
        and anchor.get("runtime_role") == "common_serving_anchor"
        and anchor.get("runtime_truth_allowed") is True
    ]


def _modifier_groups(anchors: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for anchor in anchors:
        anchor_id = str(anchor.get("anchor_id") or "")
        for modifier in anchor.get("major_modifiers") or []:
            if not isinstance(modifier, dict):
                continue
            modifier_name = str(modifier.get("name") or "").strip()
            if not modifier_name:
                continue
            group = groups.setdefault(
                modifier_name,
                {
                    "modifier_name": modifier_name,
                    "anchor_count": 0,
                    "anchor_ids": [],
                    "values": [],
                },
            )
            if anchor_id and anchor_id not in group["anchor_ids"]:
                group["anchor_ids"].append(anchor_id)
            for value in modifier.get("values") or []:
                if value not in group["values"]:
                    group["values"].append(value)

    for group in groups.values():
        group["anchor_ids"].sort()
        group["values"].sort()
        group["anchor_count"] = len(group["anchor_ids"])
    return dict(sorted(groups.items()))


def _manager_modifier_catalog(anchors: list[dict[str, Any]]) -> dict[str, Any]:
    compact = []
    for anchor in sorted(anchors, key=lambda item: str(item.get("anchor_id") or "")):
        compact.append(
            {
                "anchor_id": anchor.get("anchor_id"),
                "canonical_name": anchor.get("canonical_name"),
                "modifiers": list(anchor.get("major_modifiers") or []),
                "followup_hints": list(anchor.get("followup_hints") or []),
            }
        )
    return {
        "claim_scope": "compact_runtime_modifier_catalog_not_raw_source",
        "raw_source_rows_included": False,
        "candidate_only_records_included": False,
        "anchors": compact,
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_fooddb_modifier_catalog"]
