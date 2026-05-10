from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Any

from app.nutrition.application.food_evidence_tfda_source_macro import (
    SOURCE_EVIDENCE_MACRO_FIELDS,
    source_evidence_macro_fields,
)


POLICY_VERSION = "food_evidence_tfda_batch_promotion_v1"
SELECTED_PORTION_DEFAULTS = {
    "custom_drink_boba_milk_tea": {
        "canonical_name": "珍珠奶茶",
        "match_keywords": ("珍珠奶茶",),
        "serving_basis": "common_serving",
        "portion_basis": {
            "portion_quantity": 1,
            "portion_unit": "large_cup",
            "portion_grams": 500,
            "label": "一杯大杯珍珠奶茶",
            "derived_from": ["tfda_per_100g_source_evidence", "mvp_portion_default_policy"],
        },
        "uncertainty_category": "high_variance_customizable_drink_or_meal",
        "range_multiplier": 0.30,
        "runtime_kcal_point": 450,
        "runtime_kcal_range": [350, 550],
    },
    "listed_item_tofu_dried": {
        "canonical_name": "豆干",
        "match_keywords": ("小方豆干", "五香豆干"),
        "serving_basis": "common_serving",
        "portion_basis": {
            "portion_quantity": 1,
            "portion_unit": "piece",
            "portion_grams": 50,
            "label": "一塊滷味豆干",
            "derived_from": ["tfda_per_100g_source_evidence", "mvp_portion_default_policy"],
        },
        "uncertainty_category": "moderate_prepared_item",
        "range_multiplier": 0.20,
        "runtime_kcal_point": 95,
        "runtime_kcal_range": [70, 120],
    },
}


def build_tfda_batch_promotion_artifact(
    *,
    candidate_artifact: dict[str, Any],
    auto_eligible_artifact: dict[str, Any],
) -> dict[str, Any]:
    auto_ids = {
        str(candidate.get("candidate_id") or "")
        for candidate in auto_eligible_artifact.get("auto_eligible_candidates") or []
        if isinstance(candidate, dict)
        and candidate.get("source_class") == "taiwan_tfda_open_data"
        and candidate.get("evidence_role") == "generic_anchor_candidate"
    }
    candidates = [
        candidate
        for candidate in candidate_artifact.get("candidates") or []
        if isinstance(candidate, dict)
        and candidate.get("candidate_id") in auto_ids
        and candidate.get("source_class") == "taiwan_tfda_open_data"
    ]
    source_records = [_source_evidence_record(candidate) for candidate in candidates]
    selected_anchors, excluded = _selected_common_serving_anchors(source_records)

    return {
        "artifact_type": "accurate_intake_tfda_batch_promotion",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "claim_scope": "tfda_batch_promotion_with_selected_runtime_anchors",
        "policy_version": POLICY_VERSION,
        "food_kb_truth_updated": True,
        "runtime_truth_changed": True,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "canonical_eval_promoted": False,
        "source_evidence_records": source_records,
        "selected_common_serving_anchors": selected_anchors,
        "excluded_auto_eligible_candidates": excluded,
        "summary": {
            "source_evidence_count": len(source_records),
            "selected_runtime_anchor_count": len(selected_anchors),
            "excluded_auto_eligible_count": len(excluded),
        },
    }


def build_tfda_per100g_source_evidence_artifact(
    promotion_artifact: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "accurate_intake_tfda_per100g_source_evidence_tw",
        "artifact_schema_version": "1.0",
        "policy_version": POLICY_VERSION,
        "runtime_role": "source_evidence_only",
        "runtime_estimate_allowed": False,
        "packetizer_common_serving_allowed": False,
        "macro_contract": {
            "fields": list(SOURCE_EVIDENCE_MACRO_FIELDS),
            "source_denominator": "per_100g_edible_portion",
            "runtime_truth_allowed": False,
            "missing_macro_policy": "preserve_null_do_not_invent",
        },
        "records": promotion_artifact["source_evidence_records"],
    }


def build_tfda_selected_anchor_artifact(
    promotion_artifact: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "accurate_intake_tfda_selected_common_serving_anchors",
        "artifact_schema_version": "1.0",
        "policy_version": POLICY_VERSION,
        "runtime_role": "common_serving_anchor",
        "runtime_estimate_allowed": True,
        "anchors": promotion_artifact["selected_common_serving_anchors"],
    }


def apply_selected_anchor_metadata_to_small_anchor_store(
    small_anchor_payload: dict[str, Any],
    selected_anchor_artifact: dict[str, Any],
) -> dict[str, Any]:
    selected_by_id = {
        anchor["anchor_id"]: anchor
        for anchor in selected_anchor_artifact.get("anchors") or []
        if isinstance(anchor, dict)
    }
    updated = json.loads(json.dumps(small_anchor_payload, ensure_ascii=False))
    for item in updated.get("anchors") or []:
        anchor_id = item.get("anchor_id")
        selected = selected_by_id.get(anchor_id)
        if not selected:
            continue
        for key in (
            "runtime_role",
            "runtime_estimate_allowed",
            "runtime_truth_allowed",
            "serving_basis",
            "portion_basis",
            "kcal_point",
            "kcal_range",
            "source_refs",
            "source_provenance",
            "approval_metadata",
            "range_policy",
        ):
            item[key] = selected[key]
    return updated


def _source_evidence_record(candidate: dict[str, Any]) -> dict[str, Any]:
    label = str(candidate.get("canonical_label") or "")
    evidence_id = f"tfda_per100g_{_stable_hash(candidate.get('candidate_id'))[:12]}"
    return {
        "record_kind": "source_evidence_only",
        "source_evidence_id": evidence_id,
        "source_candidate_id": str(candidate.get("candidate_id") or ""),
        "canonical_name": label,
        "aliases": list(candidate.get("aliases") or []),
        "category": candidate.get("category"),
        "kcal_per_100g": candidate.get("kcal_point"),
        **source_evidence_macro_fields(candidate),
        "serving_basis": candidate.get("serving_basis")
        or {"unit_type": "g", "amount": 100, "label": "per_100g_edible_portion"},
        "runtime_role": "source_evidence_only",
        "runtime_estimate_allowed": False,
        "packetizer_common_serving_allowed": False,
        "source_class": "taiwan_tfda_open_data",
        "source_provenance": candidate.get("source_provenance") or {},
        "approval_metadata": {
            "approval_mode": "batch_policy_approved",
            "approval_scope": "source_class_and_per100g_evidence_batch",
            "policy_version": POLICY_VERSION,
            "approved_by": "user_batch_policy",
            "approved_at": None,
            "runtime_truth_allowed": False,
        },
    }


def _selected_common_serving_anchors(
    source_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    selected: list[dict[str, Any]] = []
    used_source_ids: set[str] = set()
    for anchor_id, defaults in SELECTED_PORTION_DEFAULTS.items():
        matching = [
            record
            for record in source_records
            if any(keyword in record["canonical_name"] for keyword in defaults["match_keywords"])
        ]
        if not matching:
            continue
        source = matching[0]
        used_source_ids.add(source["source_candidate_id"])
        selected.append(_common_serving_anchor(anchor_id=anchor_id, defaults=defaults, source=source))

    excluded = {
        record["source_candidate_id"]: "no_selected_mvp_portion_default"
        for record in source_records
        if record["source_candidate_id"] not in used_source_ids
    }
    return selected, excluded


def _common_serving_anchor(
    *,
    anchor_id: str,
    defaults: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    point = int(defaults.get("runtime_kcal_point") or _portion_point_kcal(
        source["kcal_per_100g"],
        defaults["portion_basis"]["portion_grams"],
    ))
    low, high = defaults.get("runtime_kcal_range") or _range_from_point(
        point,
        defaults["range_multiplier"],
    )
    return {
        "anchor_id": anchor_id,
        "canonical_name": defaults["canonical_name"],
        "runtime_role": "common_serving_anchor",
        "runtime_estimate_allowed": True,
        "runtime_truth_allowed": True,
        "serving_basis": defaults["serving_basis"],
        "portion_basis": defaults["portion_basis"],
        "kcal_point": point,
        "kcal_range": [low, high],
        "baseline_likely_kcal": point,
        "baseline_kcal_range": [low, high],
        "source_refs": [
            {
                "source_evidence_id": source["source_evidence_id"],
                "source_candidate_id": source["source_candidate_id"],
                "runtime_role": "source_evidence_only",
                "serving_basis": "per_100g",
                "kcal_per_100g": source["kcal_per_100g"],
            }
        ],
        "source_provenance": source["source_provenance"],
        "kcal_basis": {
            "runtime_value_source": "existing_mvp_anchor_baseline",
            "tfda_role": "source_provenance_per_100g_support",
        },
        "approval_metadata": {
            "approval_mode": "batch_policy_approved",
            "approval_scope": "selected_mvp_portion_default_anchor",
            "policy_version": POLICY_VERSION,
            "approved_by": "user_batch_policy",
            "approved_at": None,
            "runtime_truth_allowed": True,
        },
        "range_policy": {
            "uncertainty_category": defaults["uncertainty_category"],
            "range_multiplier": defaults["range_multiplier"],
            "range_basis": "category_policy",
        },
    }


def _portion_point_kcal(kcal_per_100g: Any, grams: Any) -> int:
    return int(round(float(kcal_per_100g) * float(grams) / 100))


def _range_from_point(point: int, multiplier: float) -> tuple[int, int]:
    return max(int(round(point * (1 - multiplier))), 0), int(round(point * (1 + multiplier)))


def _stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


__all__ = [
    "POLICY_VERSION",
    "apply_selected_anchor_metadata_to_small_anchor_store",
    "build_tfda_batch_promotion_artifact",
    "build_tfda_per100g_source_evidence_artifact",
    "build_tfda_selected_anchor_artifact",
]
