from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.nutrition.application.food_evidence_candidate_macro_validation import (
    macro_projection,
    macro_validation_reasons,
)
from app.nutrition.application.food_evidence_candidate_normalization import NO_TRUTH_FLAGS


ALLOWED_SOURCE_CLASSES = {
    "existing_repo_seed",
    "taiwan_tfda_open_data",
    "official_brand_chain_page",
    "local_taiwan_packaged_extract",
    "open_food_facts",
    "usda_fallback",
}
SOURCE_CLASS_COMPATIBILITY = {
    "existing_repo_seed": {"alias_coverage_prior", "generic_anchor_candidate"},
    "taiwan_tfda_open_data": {"generic_anchor_candidate", "listed_component_anchor_candidate"},
    "official_brand_chain_page": {"exact_card_candidate"},
    "local_taiwan_packaged_extract": {"exact_card_candidate"},
    "open_food_facts": {"packaged_candidate"},
    "usda_fallback": {"fallback_anchor_candidate"},
}
PR110_GAP_REQUIREMENTS = {
    "breakfast_combo": ["蛋餅", "拿鐵"],
    "chicken_bento_rice_modifier": ["雞腿便當", "白飯"],
    "bubble_tea_sugar_size_modifier": ["珍珠奶茶"],
    "luwei_listed_components": ["豆干", "海帶", "貢丸", "青菜"],
}
def build_food_evidence_candidate_validation_artifact(
    *,
    candidate_artifact: dict[str, Any],
    gap_register: dict[str, Any] | None,
) -> dict[str, Any]:
    candidates = [
        candidate
        for candidate in candidate_artifact.get("candidates", [])
        if isinstance(candidate, dict)
    ]
    collision_ids = _candidate_ids_with_label_or_alias_collision(candidates)
    validated = [
        _validate_candidate(candidate, collision_ids=collision_ids)
        for candidate in candidates
    ]
    source_repair_report = _source_repair_report(candidate_artifact)

    return {
        "artifact_type": "accurate_intake_food_evidence_candidate_validation",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "claim_scope": "food_evidence_candidate_validation_only",
        "truth_owner": "none",
        "semantic_owner": "none",
        "runtime_truth": False,
        **NO_TRUTH_FLAGS,
        "pipeline_stage_boundary": {
            "implemented_stage": "validator_passed",
            "next_stages_not_implemented": [
                "auto_eligible_packet_candidate",
                "packet_ready",
            ],
        },
        "summary": {
            "candidate_count": len(validated),
            "validator_passed_count": _count_status(validated, "validator_passed"),
            "rejected_count": _count_status(validated, "rejected"),
            "needs_source_repair_count": _count_status(validated, "needs_source_repair"),
            "source_parse_error_count": len(source_repair_report),
        },
        "source_repair_report": source_repair_report,
        "validated_candidates": validated,
        "pr110_coverage_report": _build_pr110_coverage_report(
            validated_candidates=validated,
            gap_register=gap_register,
        ),
    }


def _validate_candidate(
    candidate: dict[str, Any],
    *,
    collision_ids: set[str],
) -> dict[str, Any]:
    reasons = _validation_reasons(candidate)
    candidate_id = str(candidate.get("candidate_id") or "unknown-candidate")
    if candidate_id in collision_ids:
        reasons.append("duplicate_or_alias_collision")

    if "duplicate_or_alias_collision" in reasons and len(reasons) == 1:
        status = "needs_source_repair"
    elif "duplicate_or_alias_collision" in reasons:
        status = "needs_source_repair"
    elif reasons:
        status = "rejected"
    else:
        status = "validator_passed"

    return {
        "candidate_id": candidate_id,
        "source_id": str(candidate.get("source_id") or ""),
        "source_class": str(candidate.get("source_class") or ""),
        "evidence_role": str(candidate.get("evidence_role") or ""),
        "canonical_label": str(candidate.get("canonical_label") or ""),
        "aliases": list(candidate.get("aliases") or []),
        "kcal_point": candidate.get("kcal_point"),
        **macro_projection(candidate),
        "validation_status": status,
        "validation_reasons": reasons,
        "runtime_truth_allowed": False,
        "packet_ready": False,
        "promotion_status": "validator_passed" if status == "validator_passed" else status,
    }


def _validation_reasons(candidate: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not str(candidate.get("canonical_label") or "").strip():
        reasons.append("missing_label")
    if not _valid_kcal(candidate.get("kcal_point")):
        reasons.append("invalid_kcal_point")
    if not _valid_serving_basis(candidate.get("serving_basis")):
        reasons.append("invalid_serving_basis")
    if not _valid_provenance(candidate.get("source_provenance")):
        reasons.append("missing_source_provenance")
    if candidate.get("runtime_truth_allowed") is not False:
        reasons.append("runtime_truth_allowed_not_false")

    source_class = str(candidate.get("source_class") or "")
    evidence_role = str(candidate.get("evidence_role") or "")
    if source_class not in ALLOWED_SOURCE_CLASSES:
        reasons.append("unsupported_source_class")
    elif evidence_role not in SOURCE_CLASS_COMPATIBILITY.get(source_class, set()):
        reasons.append("source_class_role_mismatch")

    reasons.extend(macro_validation_reasons(candidate))
    return reasons


def _valid_kcal(value: Any) -> bool:
    try:
        kcal = float(value)
    except (TypeError, ValueError):
        return False
    return 0 < kcal < 2000


def _valid_serving_basis(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    amount = value.get("amount")
    unit_type = value.get("unit_type")
    try:
        amount_float = float(amount)
    except (TypeError, ValueError):
        return False
    return amount_float > 0 and bool(str(unit_type or "").strip())


def _valid_provenance(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    required = ("source_id", "source_file", "row_index", "raw_row_hash")
    return all(value.get(key) not in (None, "") for key in required)


def _candidate_ids_with_label_or_alias_collision(candidates: list[dict[str, Any]]) -> set[str]:
    token_to_ids: dict[str, set[str]] = {}
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "unknown-candidate")
        tokens = [str(candidate.get("canonical_label") or "").strip()]
        tokens.extend(str(alias).strip() for alias in candidate.get("aliases") or [])
        for token in {token.casefold() for token in tokens if token}:
            token_to_ids.setdefault(token, set()).add(candidate_id)
    return {
        candidate_id
        for ids in token_to_ids.values()
        if len(ids) > 1
        for candidate_id in ids
    }


def _source_repair_report(candidate_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for source_report in candidate_artifact.get("source_reports") or []:
        if not isinstance(source_report, dict):
            continue
        parse_error = source_report.get("parse_error")
        if not parse_error:
            continue
        reports.append(
            {
                "source_id": str(source_report.get("source_id") or "unknown-source"),
                "repair_status": "needs_source_repair",
                "reason": f"parse_error:{parse_error}",
            }
        )
    return reports


def _build_pr110_coverage_report(
    *,
    validated_candidates: list[dict[str, Any]],
    gap_register: dict[str, Any] | None,
) -> dict[str, Any]:
    requested_families = _gap_families(gap_register)
    passed_labels = {
        label
        for candidate in validated_candidates
        if candidate["validation_status"] == "validator_passed"
        for label in [candidate["canonical_label"], *candidate["aliases"]]
        if label
    }
    coverage = []
    for family in requested_families:
        required = PR110_GAP_REQUIREMENTS.get(family, [])
        matched = [keyword for keyword in required if _keyword_is_covered(keyword, passed_labels)]
        missing = [keyword for keyword in required if keyword not in matched]
        if not required:
            status = "not_mapped"
        elif not missing:
            status = "covered"
        elif matched:
            status = "partial"
        else:
            status = "not_covered"
        coverage.append(
            {
                "gap_family": family,
                "required_keywords": required,
                "matched_keywords": matched,
                "missing_keywords": missing,
                "coverage_status": status,
            }
        )
    return {
        "source": "food_gap_register",
        "truth_promotion_allowed": False,
        "gap_family_coverage": coverage,
    }


def _gap_families(gap_register: dict[str, Any] | None) -> list[str]:
    if not isinstance(gap_register, dict):
        return []
    families: list[str] = []
    for candidate in gap_register.get("food_gap_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        family = str(candidate.get("gap_family") or "")
        if family and family not in families:
            families.append(family)
    return families


def _keyword_is_covered(keyword: str, labels: set[str]) -> bool:
    return any(keyword in label or label in keyword for label in labels)


def _count_status(items: list[dict[str, Any]], status: str) -> int:
    return sum(1 for item in items if item["validation_status"] == status)


__all__ = ["build_food_evidence_candidate_validation_artifact"]
