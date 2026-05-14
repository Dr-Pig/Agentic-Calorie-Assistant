from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
QUALITY = ROOT / "docs" / "quality"

COVERAGE_MATRIX_PATH = QUALITY / "advanced_core_golden_set_coverage_matrix.yaml"
RECOMMENDATION_GOLDEN_PATH = (
    QUALITY / "advanced_product_lab_recommendation_golden_set.yaml"
)
PROACTIVE_GOLDEN_PATH = QUALITY / "advanced_product_lab_proactive_golden_set.yaml"
CROSS_JOURNEY_GOLDEN_PATH = (
    QUALITY / "advanced_product_lab_cross_journey_golden_set.yaml"
)
REUSABLE_MEAL_GOLDEN_PATH = (
    QUALITY / "advanced_product_lab_reusable_meal_golden_set.yaml"
)


def load_advanced_core_coverage_matrix() -> dict[str, Any]:
    return _load_yaml(COVERAGE_MATRIX_PATH)


def load_recommendation_golden_set() -> dict[str, Any]:
    return _load_yaml(RECOMMENDATION_GOLDEN_PATH)


def load_proactive_golden_set() -> dict[str, Any]:
    return _load_yaml(PROACTIVE_GOLDEN_PATH)


def load_cross_journey_golden_set() -> dict[str, Any]:
    return _load_yaml(CROSS_JOURNEY_GOLDEN_PATH)


def load_reusable_meal_alignment_golden_set() -> dict[str, Any]:
    return _load_yaml(REUSABLE_MEAL_GOLDEN_PATH)


def load_all_advanced_core_golden_sets() -> list[dict[str, Any]]:
    return [
        load_recommendation_golden_set(),
        load_proactive_golden_set(),
        load_cross_journey_golden_set(),
        load_reusable_meal_alignment_golden_set(),
    ]


def validate_golden_set_contract(artifact: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    cases = list(artifact.get("cases") or [])
    contract = dict(artifact.get("suite_contract") or {})
    required_fields = set((artifact.get("case_schema") or {}).get("required_fields") or [])

    if artifact.get("status") != "active_alignment_contract":
        blockers.append("status_not_active_alignment_contract")
    if artifact.get("mainline_activation_enabled") is not False:
        blockers.append("mainline_activation_enabled_not_false")
    if artifact.get("raw_keyword_semantic_oracle_allowed") is not False:
        blockers.append("raw_keyword_semantic_oracle_allowed_not_false")

    expected_splits = dict(contract.get("required_split_counts") or {})
    split_counts = _count_by(cases, "split")
    if split_counts != expected_splits:
        blockers.append(f"split_counts.expected_{expected_splits}_actual_{split_counts}")

    required_case_types = set(contract.get("required_case_types") or [])
    case_types = {str(case.get("case_type")) for case in cases}
    if case_types != required_case_types:
        blockers.append(f"case_types.expected_{sorted(required_case_types)}_actual_{sorted(case_types)}")

    case_ids = [str(case.get("case_id")) for case in cases]
    if len(case_ids) != len(set(case_ids)):
        blockers.append("case_ids.duplicate")

    for case in cases:
        case_id = str(case.get("case_id", "unknown"))
        missing = sorted(required_fields - set(case))
        if missing:
            blockers.append(f"{case_id}.missing_required_fields:{','.join(missing)}")
        oracle = dict(case.get("oracle") or {})
        if oracle.get("semantic_oracle_source") != "product_rule_and_trace_fields":
            blockers.append(f"{case_id}.oracle_not_product_trace")
        if oracle.get("raw_keyword_route_allowed") is not False:
            blockers.append(f"{case_id}.raw_keyword_route_allowed")
        if not case.get("product_truth"):
            blockers.append(f"{case_id}.missing_product_truth")
        if not case.get("expected_trace_fields"):
            blockers.append(f"{case_id}.missing_expected_trace_fields")
        mutation_posture = dict(case.get("mutation_posture") or {})
        if "canonical_mutation" not in mutation_posture:
            blockers.append(f"{case_id}.missing_canonical_mutation_posture")
        if "mainline_activation" not in mutation_posture:
            blockers.append(f"{case_id}.missing_mainline_activation_posture")

    return {
        "artifact_type": "advanced_core_golden_set_contract_validation",
        "status": "pass" if not blockers else "fail",
        "validated_artifact_type": artifact.get("artifact_type"),
        "case_count": len(cases),
        "split_counts": split_counts,
        "case_types": sorted(case_types),
        "blockers": blockers,
    }


def build_advanced_core_golden_set_alignment_report() -> dict[str, Any]:
    matrix = load_advanced_core_coverage_matrix()
    validations = [validate_golden_set_contract(item) for item in load_all_advanced_core_golden_sets()]
    blockers: list[str] = []
    for validation in validations:
        blockers.extend(
            f"{validation['validated_artifact_type']}:{blocker}"
            for blocker in validation["blockers"]
        )

    required_domains = list(matrix.get("coverage_domains") or [])
    if set(required_domains) != {
        "memory",
        "rescue",
        "recommendation",
        "proactive",
        "context_engineering",
        "reusable_meal",
        "cross_journey",
    }:
        blockers.append("coverage_domains_missing_required_advanced_core_domain")

    return {
        "artifact_type": "advanced_core_golden_set_alignment_report",
        "status": "pass" if not blockers else "fail",
        "owner": matrix.get("owner"),
        "consumer": matrix.get("consumer"),
        "existing_sets_policy": matrix.get("existing_sets_policy"),
        "product_surface_policy": dict(matrix.get("product_surface_policy") or {}),
        "coverage_domains": required_domains,
        "new_golden_sets": list(matrix.get("new_golden_sets") or []),
        "mainline_activation_enabled": matrix.get("mainline_activation_enabled"),
        "raw_keyword_semantic_oracle_allowed": matrix.get(
            "raw_keyword_semantic_oracle_allowed"
        ),
        "validations": validations,
        "blockers": blockers,
    }


def _load_yaml(path: Path) -> dict[str, Any]:
    return dict(yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {})


def _count_by(cases: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        key = str(case.get(field))
        counts[key] = counts.get(key, 0) + 1
    return counts


__all__ = [
    "COVERAGE_MATRIX_PATH",
    "CROSS_JOURNEY_GOLDEN_PATH",
    "PROACTIVE_GOLDEN_PATH",
    "RECOMMENDATION_GOLDEN_PATH",
    "REUSABLE_MEAL_GOLDEN_PATH",
    "build_advanced_core_golden_set_alignment_report",
    "load_advanced_core_coverage_matrix",
    "load_all_advanced_core_golden_sets",
    "load_cross_journey_golden_set",
    "load_proactive_golden_set",
    "load_recommendation_golden_set",
    "load_reusable_meal_alignment_golden_set",
    "validate_golden_set_contract",
]
