from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
GOLDEN_SET_PATH = (
    ROOT / "docs" / "quality" / "advanced_product_lab_context_engineering_golden_set.yaml"
)
EXPECTED_CASE_IDS = [f"ce-stress-{index:03d}" for index in range(1, 31)]


def load_context_engineering_golden_set() -> dict[str, Any]:
    data = yaml.safe_load(GOLDEN_SET_PATH.read_text(encoding="utf-8-sig"))
    return dict(data)


def golden_set_case_ids() -> list[str]:
    return [str(item["case_id"]) for item in load_context_engineering_golden_set()["cases"]]


def validate_context_engineering_golden_set(
    artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    golden_set = artifact or load_context_engineering_golden_set()
    cases = list(golden_set.get("cases") or [])
    blockers: list[str] = []

    _expect_equal(
        blockers,
        "artifact_type",
        golden_set.get("artifact_type"),
        "advanced_product_lab_context_engineering_golden_set",
    )
    _expect_equal(blockers, "version", golden_set.get("version"), 2)
    _expect_equal(blockers, "status", golden_set.get("status"), "active")

    if len(cases) != 30:
        blockers.append(f"case_count.expected_30_actual_{len(cases)}")

    case_ids = [str(item.get("case_id")) for item in cases]
    if case_ids != EXPECTED_CASE_IDS:
        blockers.append("case_ids.not_contiguous_ce_stress_001_to_030")
    if len(case_ids) != len(set(case_ids)):
        blockers.append("case_ids.duplicate")

    required_fields = set((golden_set.get("case_schema") or {}).get("required_fields") or [])
    for case in cases:
        missing = sorted(required_fields - set(case))
        if missing:
            blockers.append(f"{case.get('case_id', 'unknown')}.missing_required_fields:{','.join(missing)}")

    split_targets = dict(golden_set.get("split_targets") or {})
    split_counts = _count_by(cases, "split")
    _validate_counts(blockers, "split_counts", split_counts, split_targets)

    category_targets = dict(golden_set.get("category_targets") or {})
    category_counts = _count_by(cases, "category")
    _validate_counts(blockers, "category_counts", category_counts, category_targets)

    policy = dict(golden_set.get("evaluation_policy") or {})
    no_keyword_oracle = policy.get("no_raw_keyword_semantic_oracle") is True
    if not no_keyword_oracle:
        blockers.append("evaluation_policy.no_raw_keyword_semantic_oracle_not_true")
    if policy.get("eval_assets_do_not_define_product_truth") is not True:
        blockers.append("evaluation_policy.eval_assets_do_not_define_product_truth_not_true")
    if policy.get("semantic_decision_owner") != "manager_llm_structured_output":
        blockers.append("evaluation_policy.semantic_decision_owner_not_manager_llm")

    return {
        "artifact_type": "advanced_product_lab_context_engineering_golden_set_validation",
        "status": "pass" if not blockers else "fail",
        "case_count": len(cases),
        "split_counts": split_counts,
        "category_counts": category_counts,
        "no_raw_keyword_semantic_oracle": no_keyword_oracle,
        "blockers": blockers,
    }


def build_context_engineering_golden_set_loader_artifact() -> dict[str, Any]:
    golden_set = load_context_engineering_golden_set()
    validation = validate_context_engineering_golden_set(golden_set)
    policy = dict(golden_set.get("evaluation_policy") or {})
    return {
        "artifact_type": "advanced_product_lab_context_engineering_golden_set_loader_v2",
        "status": validation["status"],
        "runtime_effect_allowed": False,
        "mainline_activation_enabled": False,
        "canonical_mutation_allowed": False,
        "validated_case_count": validation["case_count"],
        "split_counts": validation["split_counts"],
        "category_counts": validation["category_counts"],
        "semantic_decision_owner": policy.get("semantic_decision_owner"),
        "validation": validation,
    }


def _count_by(cases: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        key = str(case.get(field))
        counts[key] = counts.get(key, 0) + 1
    return counts


def _expect_equal(blockers: list[str], field: str, actual: object, expected: object) -> None:
    if actual != expected:
        blockers.append(f"{field}.expected_{expected}_actual_{actual}")


def _validate_counts(
    blockers: list[str],
    label: str,
    counts: dict[str, int],
    targets: dict[str, int],
) -> None:
    if counts != targets:
        blockers.append(f"{label}.expected_{targets}_actual_{counts}")


__all__ = [
    "GOLDEN_SET_PATH",
    "build_context_engineering_golden_set_loader_artifact",
    "golden_set_case_ids",
    "load_context_engineering_golden_set",
    "validate_context_engineering_golden_set",
]
