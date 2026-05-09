from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_memory_edd"
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SUITE_PATH = ROOT / "docs" / "quality" / "runtime_lab_memory_edd_golden_set.yaml"

EXPECTED_RUNTIME_EFFECTS: dict[str, bool] = {
    "runtime_connected": False,
    "user_facing_behavior_changed": False,
    "canonical_mutation_changed": False,
    "durable_product_memory_written": False,
    "manager_context_packet_changed": False,
}

REQUIRED_CASE_TYPES = {
    "explicit_preference",
    "negative_preference",
    "temporary_preference",
    "repeated_pattern",
    "golden_order",
    "correction_not_memory",
    "suppression",
    "stale_conflict",
    "scope_leak",
    "prompt_injection_attempt",
}

REQUIRED_RUBRIC_DIMENSIONS = {
    "extraction",
    "promotion_legality",
    "retrieval_precision",
    "omission",
    "no_canonical_mutation",
    "scope_isolation",
    "secret_redaction",
}

REQUIRED_PRODUCT_TRUTH_REFS = {
    "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
    "docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md",
    "docs/quality/ADVANCED_MEMORY_MECHANISM_BUILD_SPEC.md",
}


def load_runtime_lab_memory_edd_suite(
    path: Path | str = DEFAULT_SUITE_PATH,
) -> dict[str, Any]:
    suite_path = Path(path)
    raw = yaml.safe_load(suite_path.read_text(encoding="utf-8")) or {}
    artifact = dict(raw)

    cases = [dict(case) for case in artifact.get("cases", [])]
    for case in cases:
        case.setdefault("expected_runtime_effects", dict(EXPECTED_RUNTIME_EFFECTS))

    case_type_counts = Counter(str(case.get("case_type")) for case in cases)
    split_counts = Counter(str(case.get("split")) for case in cases)
    rubric = [dict(item) for item in artifact.get("rubric", [])]

    blockers = _validate_suite(
        artifact=artifact,
        cases=cases,
        case_type_counts=case_type_counts,
        split_counts=split_counts,
        rubric=rubric,
    )

    return {
        **artifact,
        "artifact_type": "runtime_lab_memory_edd_golden_set",
        "status": "pass" if not blockers else "fail",
        "source_path": str(suite_path.relative_to(ROOT)),
        "case_count": len(cases),
        "case_types": sorted(case_type_counts),
        "split_counts": dict(sorted(split_counts.items())),
        "cases": cases,
        "rubric": rubric,
        "blockers": blockers,
        "runtime_connected": False,
        "lab_isolated": True,
        "manager_context_packet_changed": False,
        "durable_product_memory_written": False,
    }


def _validate_suite(
    *,
    artifact: dict[str, Any],
    cases: list[dict[str, Any]],
    case_type_counts: Counter[str],
    split_counts: Counter[str],
    rubric: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []

    missing_case_types = REQUIRED_CASE_TYPES - set(case_type_counts)
    if missing_case_types:
        blockers.append(f"missing_case_types:{','.join(sorted(missing_case_types))}")

    duplicated_case_types = [
        case_type for case_type, count in case_type_counts.items() if count != 1
    ]
    if duplicated_case_types:
        blockers.append(f"case_type_count_not_one:{','.join(sorted(duplicated_case_types))}")

    expected_splits = {"fixture": 6, "holdout": 2, "negative": 2}
    if dict(split_counts) != expected_splits:
        blockers.append(f"split_counts:{dict(split_counts)}")

    rubric_dimensions = {str(item.get("dimension_id")) for item in rubric}
    missing_dimensions = REQUIRED_RUBRIC_DIMENSIONS - rubric_dimensions
    if missing_dimensions:
        blockers.append(f"missing_rubric_dimensions:{','.join(sorted(missing_dimensions))}")

    for flag in (
        "runtime_connected",
        "user_facing_behavior_changed",
        "canonical_mutation_changed",
        "durable_product_memory_written",
        "manager_context_packet_changed",
    ):
        if artifact.get(flag) is not False:
            blockers.append(f"artifact_effect_flag_not_false:{flag}")

    for case in cases:
        case_id = str(case.get("case_id"))
        if case.get("expected_runtime_effects") != EXPECTED_RUNTIME_EFFECTS:
            blockers.append(f"{case_id}.runtime_effects")
        oracle = case.get("oracle") or {}
        if oracle.get("semantic_oracle_source") != "product_rule_and_trace_fields":
            blockers.append(f"{case_id}.semantic_oracle_source")
        if oracle.get("raw_keyword_route_allowed") is not False:
            blockers.append(f"{case_id}.raw_keyword_route_allowed")
        if "raw_keyword_rules" in case or "raw_input_keyword" in oracle:
            blockers.append(f"{case_id}.raw_keyword_semantic_oracle")

    return blockers


def build_reviewed_dogfood_edd_suite_projection(
    suite: dict[str, Any],
    dogfood_review: dict[str, Any],
) -> dict[str, Any]:
    base_cases = [dict(case) for case in suite.get("cases", [])]
    review_cases = [
        dict(case) for case in dogfood_review.get("reviewed_case_proposals", [])
    ]
    blockers = _projection_blockers(suite, dogfood_review)

    projected_cases = base_cases if blockers else [*base_cases, *review_cases]
    split_counts = Counter(str(case.get("split")) for case in projected_cases)
    case_type_counts = Counter(str(case.get("case_type")) for case in projected_cases)

    return {
        **suite,
        "artifact_type": "runtime_lab_memory_edd_suite_projection",
        "status": "pass" if not blockers else "blocked",
        "base_artifact_type": suite.get("artifact_type"),
        "dogfood_review_artifact_type": dogfood_review.get("artifact_type"),
        "base_case_count": len(base_cases),
        "reviewed_dogfood_case_count": 0 if blockers else len(review_cases),
        "case_count": len(projected_cases),
        "case_types": sorted(case_type_counts),
        "split_counts": dict(sorted(split_counts.items())),
        "cases": projected_cases,
        "blockers": blockers,
        "canonical_golden_set_mutated": False,
        "reviewed_cases_promoted_to_canonical": False,
        "runtime_connected": False,
        "lab_isolated": True,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "non_claims": [
            "not_product_activation_evidence",
            "not_private_self_use_approval",
            "not_canonical_golden_set_mutation",
        ],
    }


def _projection_blockers(
    suite: dict[str, Any],
    dogfood_review: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    base_case_ids = {str(case.get("case_id")) for case in suite.get("cases", [])}
    policy = suite.get("golden_set_policy") or {}
    truth_refs = set(policy.get("product_truth_source") or [])
    if not REQUIRED_PRODUCT_TRUTH_REFS <= truth_refs:
        blockers.append("missing_product_truth_source_refs")
    if suite.get("status") != "pass":
        blockers.append("base_suite_not_pass")
        blockers.extend(str(blocker) for blocker in suite.get("blockers", []))
    if dogfood_review.get("status") != "pass":
        blockers.append("dogfood_review_not_pass")
        blockers.extend(str(blocker) for blocker in dogfood_review.get("blockers", []))
    if dogfood_review.get("artifact_type") != "runtime_lab_memory_dogfood_replay_review":
        blockers.append("unsupported_dogfood_review_artifact")
    for case in dogfood_review.get("reviewed_case_proposals", []):
        case_id = str(case.get("case_id"))
        if case_id in base_case_ids:
            blockers.append(f"duplicate_case_id:{case_id}")
        trace_fields = case.get("trace_fields") or {}
        if not trace_fields.get("source_refs"):
            blockers.append(f"{case_id}.missing_source_refs")
        if case.get("expected_runtime_effects") != EXPECTED_RUNTIME_EFFECTS:
            blockers.append(f"{case_id}.runtime_effects")
    return blockers


__all__ = [
    "DEFAULT_SUITE_PATH",
    "EXPECTED_RUNTIME_EFFECTS",
    "REQUIRED_PRODUCT_TRUTH_REFS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_reviewed_dogfood_edd_suite_projection",
    "load_runtime_lab_memory_edd_suite",
]
