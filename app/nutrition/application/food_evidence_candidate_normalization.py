from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any, Iterable

from app.nutrition.application.food_evidence_candidate_record_values import stable_hash
from app.nutrition.application.food_evidence_candidate_macro_fields import (
    macro_fields_for_candidate,
)
from app.nutrition.application.food_evidence_candidate_source_mapping import (
    candidate_from_csv_record,
    candidate_from_json_record,
    candidate_from_xlsx_record,
    record_id,
)
from app.nutrition.application.food_evidence_candidate_source_records import (
    normalize_source,
)
from app.nutrition.application.food_raw_source_inventory import (
    NON_CLAIM_FLAGS,
    RAW_SOURCE_DEFINITIONS,
    RawSourceDefinition,
)

NO_TRUTH_FLAGS = {
    **NON_CLAIM_FLAGS,
    "runtime_truth_changed": False,
}

EVIDENCE_ROLE_BY_SOURCE_ID = {
    "newtaipei_brand_candidates": "exact_card_candidate",
    "local_tw_packaged_extract_188_2": "exact_card_candidate",
    "openfoodfacts_taiwan_small": "packaged_candidate",
    "usda_food_list_sample": "fallback_anchor_candidate",
    "base_nutrition_db": "alias_coverage_prior",
}
TFDA_LISTED_COMPONENT_PREFIXES = (
    "豆干",
    "豆乾",
    "海帶",
    "海帶芽",
    "貢丸",
    "高麗菜",
    "四季豆",
    "青江菜",
    "小白菜",
    "空心菜",
    "A菜",
    "大陸妹",
    "萵苣",
    "花椰菜",
    "豆皮",
    "豆腐皮",
    "百頁豆腐",
    "米血",
    "豬血糕",
    "黑輪",
    "甜不辣",
    "香菇",
    "金針菇",
    "杏鮑菇",
    "鴨血",
    "凍豆腐",
    "白蘿蔔",
    "蘿蔔",
    "玉米筍",
    "木耳",
    "冬粉",
)
TFDA_LISTED_COMPONENT_DISQUALIFIERS = (
    "奶茶",
    "飲料",
    "水餃",
    "壽司",
    "蒸蛋",
    "魚",
    "雞",
    "罐頭",
    "料理包",
    "蘿蔔糕",
    "麵",
    "酥",
)


def build_food_evidence_candidate_artifact(
    scan_roots: Iterable[Path | str],
) -> dict[str, Any]:
    roots = [Path(root) for root in scan_roots]
    candidates: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []

    for definition in RAW_SOURCE_DEFINITIONS:
        report, source_candidates, source_rejections = normalize_source(
            definition,
            roots,
            normalize_json_record=partial(
                candidate_from_json_record, build_candidate=_candidate
            ),
            normalize_csv_record=partial(
                candidate_from_csv_record, build_candidate=_candidate
            ),
            normalize_xlsx_record=partial(
                candidate_from_xlsx_record, build_candidate=_candidate
            ),
            build_rejection=_rejection,
            resolve_record_id=record_id,
        )
        reports.append(report)
        candidates.extend(source_candidates)
        rejections.extend(source_rejections)

    parse_error_count = sum(1 for report in reports if report.get("parse_error"))
    present_reports = [report for report in reports if report["local_path_present"]]

    return {
        "artifact_type": "accurate_intake_food_evidence_candidates",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "claim_scope": "food_evidence_candidate_normalization_only",
        "truth_owner": "none",
        "semantic_owner": "none",
        "runtime_truth": False,
        **NO_TRUTH_FLAGS,
        "pipeline_stage_boundary": {
            "implemented_stage": "candidate",
            "next_stages_not_implemented": [
                "validator_passed",
                "auto_eligible_packet_candidate",
                "packet_ready",
            ],
        },
        "candidate_summary": {
            "source_count": len(RAW_SOURCE_DEFINITIONS),
            "present_source_count": len(present_reports),
            "parsed_count": sum(report["parsed_count"] for report in reports),
            "candidate_count": len(candidates),
            "rejected_count": len(rejections),
            "parse_error_count": parse_error_count,
        },
        "source_reports": reports,
        "candidates": candidates,
        "rejections": rejections,
    }


def _candidate(
    *,
    definition: RawSourceDefinition,
    label: str,
    row_index: int,
    record_id: str | None,
    kcal: float,
    aliases: list[str],
    category: str | None,
    brand: str | None,
    serving_basis: dict[str, Any],
    source_url: str | None,
    raw_record: dict[str, Any],
    extra_provenance: dict[str, Any] | None,
) -> dict[str, Any]:
    candidate_hash = stable_hash(
        {
            "source_id": definition.source_id,
            "label": label,
            "row_index": row_index,
            "record_id": record_id,
            "kcal": kcal,
        }
    )[:12]
    return {
        "candidate_id": f"cand_{definition.source_id}_{candidate_hash}",
        "source_id": definition.source_id,
        "source_class": definition.source_class,
        "source_role": definition.source_role,
        "evidence_role": _evidence_role(definition, label=label, aliases=aliases),
        "promotion_status": "candidate",
        "runtime_truth_allowed": False,
        "canonical_label": label,
        "aliases": aliases,
        "brand": brand,
        "category": category,
        "serving_basis": serving_basis,
        "kcal_point": kcal,
        "kcal_range": None,
        **macro_fields_for_candidate(
            raw_record=raw_record,
            serving_basis=serving_basis,
        ),
        "source_provenance": {
            "source_id": definition.source_id,
            "source_file": definition.filename,
            "row_index": row_index,
            "record_id": record_id,
            "source_url": source_url,
            "raw_row_hash": stable_hash(raw_record),
            **(extra_provenance or {}),
        },
        "quality_flags": [],
    }


def _rejection(
    definition: RawSourceDefinition,
    row_index: int,
    record_id: str | None,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "source_id": definition.source_id,
        "source_class": definition.source_class,
        "source_file": definition.filename,
        "row_index": row_index,
        "record_id": record_id,
        "reasons": reasons,
    }


def _evidence_role(
    definition: RawSourceDefinition,
    *,
    label: str,
    aliases: list[str],
) -> str:
    if definition.source_id in EVIDENCE_ROLE_BY_SOURCE_ID:
        return EVIDENCE_ROLE_BY_SOURCE_ID[definition.source_id]
    if definition.source_class == "taiwan_tfda_open_data":
        if _is_tfda_listed_component_candidate(label=label, aliases=aliases):
            return "listed_component_anchor_candidate"
        return "generic_anchor_candidate"
    return f"{definition.intended_roles[0]}_candidate"


def _is_tfda_listed_component_candidate(*, label: str, aliases: list[str]) -> bool:
    tokens = [label] if label else list(aliases)
    for token in tokens:
        normalized = str(token or "").strip()
        if not normalized:
            continue
        if any(
            disqualifier in normalized
            for disqualifier in TFDA_LISTED_COMPONENT_DISQUALIFIERS
        ):
            continue
        if normalized.endswith("乾") and not normalized.startswith(("豆干", "豆乾")):
            continue
        if any(
            normalized.startswith(prefix) for prefix in TFDA_LISTED_COMPONENT_PREFIXES
        ):
            return True
    return False


__all__ = ["build_food_evidence_candidate_artifact"]
