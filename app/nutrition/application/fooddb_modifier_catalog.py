from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.nutrition.application.fooddb_modifier_priority import (
    CATALOG_SUPPORTED_REPORT_ONLY_POSTURE,
    NON_P0_STAGED_POSTURE,
    P0_MODIFIERS,
    build_staged_policy_modifier_labels,
)


def build_fooddb_modifier_catalog(
    *,
    small_anchor_payload: dict[str, Any],
) -> dict[str, Any]:
    runtime_anchors = _runtime_common_serving_anchors(small_anchor_payload)
    modifier_aware_anchors = [
        anchor for anchor in runtime_anchors if anchor.get("major_modifiers")
    ]
    modifier_groups = _modifier_groups(modifier_aware_anchors)
    priority_groups = _modifier_priority_groups(modifier_groups)
    p0_support_matrix = _p0_support_matrix(modifier_aware_anchors)
    p0_anchor_coverage = _p0_anchor_coverage(modifier_aware_anchors)

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
            "p0_modifier_count": len(priority_groups["P0"]),
            "p0_supported_anchor_count": len(p0_anchor_coverage),
        },
        "modifier_groups": modifier_groups,
        "modifier_priority_groups": priority_groups,
        "p0_support_matrix": p0_support_matrix,
        "p0_anchor_coverage": p0_anchor_coverage,
        "non_p0_posture": _non_p0_posture(priority_groups),
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


def _modifier_priority_groups(modifier_groups: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    known_modifiers = sorted(modifier_groups)
    p0 = [modifier for modifier in P0_MODIFIERS if modifier in modifier_groups]
    observed_non_p0 = [modifier for modifier in known_modifiers if modifier not in P0_MODIFIERS]
    return {
        "P0": p0,
        "observed_runtime_non_p0_modifier_names": observed_non_p0,
        "policy_staged_modifier_labels": build_staged_policy_modifier_labels(),
        "unsupported_or_not_yet_covered": [],
    }


def _p0_support_matrix(anchors: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    matrix: dict[str, dict[str, Any]] = {}
    for modifier_name in P0_MODIFIERS:
        matching_anchors = []
        values: set[str] = set()
        followup_hints: set[str] = set()
        for anchor in anchors:
            modifier_names = {
                str(modifier.get("name") or "").strip()
                for modifier in anchor.get("major_modifiers") or []
                if isinstance(modifier, dict)
            }
            if modifier_name not in modifier_names:
                continue
            matching_anchors.append(anchor)
            followup_hints.update(str(hint) for hint in anchor.get("followup_hints") or [] if hint)
            for modifier in anchor.get("major_modifiers") or []:
                if not isinstance(modifier, dict):
                    continue
                if str(modifier.get("name") or "").strip() != modifier_name:
                    continue
                values.update(str(value) for value in modifier.get("values") or [] if value)

        matrix[modifier_name] = {
            "modifier_name": modifier_name,
            "priority": "P0",
            "supported": bool(matching_anchors),
            "anchor_count": len(matching_anchors),
            "anchor_ids": sorted(
                str(anchor.get("anchor_id") or "")
                for anchor in matching_anchors
                if str(anchor.get("anchor_id") or "")
            ),
            "supported_values": sorted(values),
            "followup_hints": sorted(followup_hints),
            "activation_posture": CATALOG_SUPPORTED_REPORT_ONLY_POSTURE,
        }
    return matrix


def _p0_anchor_coverage(anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    coverage = []
    for anchor in sorted(anchors, key=lambda item: str(item.get("anchor_id") or "")):
        p0_modifiers = sorted(
            {
                str(modifier.get("name") or "").strip()
                for modifier in anchor.get("major_modifiers") or []
                if isinstance(modifier, dict) and str(modifier.get("name") or "").strip() in P0_MODIFIERS
            }
        )
        if not p0_modifiers:
            continue
        coverage.append(
            {
                "anchor_id": anchor.get("anchor_id"),
                "canonical_name": anchor.get("canonical_name"),
                "p0_modifiers": p0_modifiers,
                "followup_hints": sorted(str(hint) for hint in anchor.get("followup_hints") or [] if hint),
            }
        )
    return coverage


def _non_p0_posture(priority_groups: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "treated_as_p0": [],
        "observed_runtime_modifier_names": list(
            priority_groups["observed_runtime_non_p0_modifier_names"]
        ),
        "policy_staged_modifier_labels": list(priority_groups["policy_staged_modifier_labels"]),
        "posture": NON_P0_STAGED_POSTURE,
        "runtime_truth_promoted": False,
    }


def _manager_modifier_catalog(anchors: list[dict[str, Any]]) -> dict[str, Any]:
    compact = []
    for anchor in sorted(anchors, key=lambda item: str(item.get("anchor_id") or "")):
        compact.append(
            {
                "anchor_id": anchor.get("anchor_id"),
                "canonical_name": anchor.get("canonical_name"),
                "modifiers": _compact_modifiers(anchor.get("major_modifiers") or []),
                "followup_hints": list(anchor.get("followup_hints") or []),
            }
        )
    return {
        "claim_scope": "compact_runtime_modifier_catalog_not_raw_source",
        "raw_source_rows_included": False,
        "candidate_only_records_included": False,
        "anchors": compact,
    }


def _compact_modifiers(modifiers: list[Any]) -> list[dict[str, Any]]:
    compact = []
    for modifier in modifiers:
        if not isinstance(modifier, dict):
            continue
        name = str(modifier.get("name") or "").strip()
        if not name:
            continue
        compact.append(
            {
                "name": name,
                "values": [
                    str(value)
                    for value in modifier.get("values") or []
                    if str(value).strip()
                ],
            }
        )
    return compact


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_fooddb_modifier_catalog"]
