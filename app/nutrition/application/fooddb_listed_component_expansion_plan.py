from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


LISTED_COMPONENT_TARGETS: tuple[dict[str, Any], ...] = (
    {"label": "豆干", "families": ("luwei", "malatang")},
    {"label": "海帶", "families": ("luwei", "malatang")},
    {"label": "貢丸", "families": ("luwei", "malatang", "oden")},
    {"label": "青菜", "families": ("luwei", "malatang", "buffet")},
    {"label": "豆皮", "families": ("luwei", "malatang")},
    {"label": "百頁豆腐", "families": ("luwei", "malatang")},
    {"label": "王子麵", "families": ("luwei", "malatang")},
    {"label": "雞排", "families": ("fried_snack",)},
    {"label": "甜不辣", "families": ("fried_snack", "luwei")},
    {"label": "米血", "families": ("fried_snack", "luwei")},
    {"label": "四季豆", "families": ("fried_snack", "luwei")},
    {"label": "黑輪", "families": ("oden", "luwei")},
    {"label": "高麗菜", "families": ("luwei", "malatang", "buffet")},
    {"label": "鴨血", "families": ("malatang", "spicy_hotpot")},
    {"label": "粉絲", "families": ("malatang", "spicy_hotpot")},
    {"label": "香菇", "families": ("luwei", "malatang")},
    {"label": "魚板", "families": ("oden",)},
    {"label": "蟹肉棒", "families": ("oden", "hotpot")},
    {"label": "油豆腐", "families": ("oden", "luwei")},
    {"label": "白蘿蔔", "families": ("oden",)},
    {"label": "金針菇", "families": ("malatang", "hotpot")},
    {"label": "凍豆腐", "families": ("malatang", "hotpot")},
    {"label": "玉米筍", "families": ("malatang", "buffet")},
    {"label": "花椰菜", "families": ("malatang", "buffet")},
    {"label": "魚豆腐", "families": ("oden", "hotpot")},
)


def build_listed_component_expansion_plan(
    *,
    small_anchor_payload: dict[str, Any],
    tfda_source_payload: dict[str, Any],
) -> dict[str, Any]:
    runtime_index = _runtime_listed_anchor_index(small_anchor_payload)
    source_index = _source_evidence_index(tfda_source_payload)
    targets = [
        _target_entry(target=target, runtime_index=runtime_index, source_index=source_index)
        for target in LISTED_COMPONENT_TARGETS
    ]
    source_backed = [
        entry
        for entry in targets
        if entry["status"] == "source_evidence_match_available_not_runtime"
    ]
    missing = [entry for entry in targets if entry["status"] == "source_evidence_missing"]
    return {
        "artifact_type": "accurate_intake_fooddb_listed_component_expansion_plan",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "claim_scope": "listed_component_expansion_plan_only",
        "runtime_truth_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "match_policy": {
            "source_evidence_matching": "normalized_exact_alias_only",
            "substring_matching_allowed": False,
            "false_positive_guard_examples": ["白蘿蔔 != 胡蘿蔔素", "白蘿蔔 != 蘿蔔糕"],
        },
        "summary": {
            "target_component_count": len(targets),
            "runtime_visible_count": sum(
                1 for entry in targets if entry["status"] == "runtime_visible_existing_anchor"
            ),
            "source_backed_not_runtime_count": len(source_backed),
            "source_missing_count": len(missing),
        },
        "next_batch_recommendation": {
            "max_new_runtime_anchors_before_activation": 12,
            "candidate_labels": [entry["component_label"] for entry in source_backed],
            "blocked_labels": [entry["component_label"] for entry in missing],
        },
        "targets": targets,
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_live_provider_call",
            "no_manager_context_change",
            "no_packetizer_format_change",
        ],
    }


def _target_entry(
    *,
    target: dict[str, Any],
    runtime_index: dict[str, dict[str, Any]],
    source_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    label = str(target["label"])
    normalized = _normalize_label(label)
    runtime_anchor = runtime_index.get(normalized)
    source_match = source_index.get(normalized)

    if runtime_anchor is not None:
        status = "runtime_visible_existing_anchor"
        recommended = "none_runtime_visible"
    elif source_match is not None:
        status = "source_evidence_match_available_not_runtime"
        recommended = "add_small_anchor_then_selected_promotion"
    else:
        status = "source_evidence_missing"
        recommended = "require_new_source_or_alias_strategy"

    return {
        "component_label": label,
        "families": list(target["families"]),
        "status": status,
        "runtime_anchor_id": runtime_anchor.get("anchor_id") if runtime_anchor else None,
        "source_evidence_match": (
            {
                "source_evidence_id": source_match["source_evidence_id"],
                "canonical_name": source_match["canonical_name"],
                "alias_matched": source_match["alias_matched"],
            }
            if source_match
            else None
        ),
        "recommended_next_action": recommended,
    }


def _runtime_listed_anchor_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for anchor in payload.get("anchors") or []:
        if not isinstance(anchor, dict):
            continue
        if anchor.get("record_kind") != "generic_anchor":
            continue
        if anchor.get("dish_type") != "listed_item":
            continue
        if anchor.get("runtime_role") != "common_serving_anchor":
            continue
        if anchor.get("runtime_truth_allowed") is not True:
            continue
        candidate_names = [
            str(anchor.get("canonical_name") or "").strip(),
            *[
                str(alias).strip()
                for alias in anchor.get("aliases") or []
                if str(alias).strip()
            ],
        ]
        candidate_names = [name for name in candidate_names if name]
        if not candidate_names:
            continue
        for name in candidate_names:
            normalized = _normalize_label(name)
            if not normalized or normalized in index:
                continue
            index[normalized] = anchor
    return index


def _source_evidence_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for record in payload.get("records") or []:
        if not isinstance(record, dict):
            continue
        evidence_id = str(record.get("source_evidence_id") or "").strip()
        canonical_name = str(record.get("canonical_name") or "").strip()
        aliases = [
            str(alias).strip()
            for alias in record.get("aliases") or []
            if str(alias).strip()
        ]
        if not evidence_id or not canonical_name:
            continue
        for alias in (canonical_name, *aliases):
            normalized = _normalize_label(alias)
            if not normalized or normalized in index:
                continue
            index[normalized] = {
                "source_evidence_id": evidence_id,
                "canonical_name": canonical_name,
                "alias_matched": alias,
            }
    return index


def _normalize_label(value: str) -> str:
    return "".join(str(value).strip().lower().split())


__all__ = [
    "LISTED_COMPONENT_TARGETS",
    "build_listed_component_expansion_plan",
]
