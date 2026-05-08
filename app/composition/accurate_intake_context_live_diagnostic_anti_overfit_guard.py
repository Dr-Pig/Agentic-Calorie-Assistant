from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _case_ids(matrix: dict[str, Any]) -> list[str]:
    cases = matrix.get("cases")
    if not isinstance(cases, list):
        return []
    return [str(_object_dict(case).get("case_id") or "") for case in cases]


def _distinct_case_values(matrix: dict[str, Any], key: str) -> set[str]:
    cases = matrix.get("cases")
    if not isinstance(cases, list):
        return set()
    values: set[str] = set()
    for case in cases:
        value = _object_dict(case).get(key)
        if value:
            values.add(str(value))
    return values


def _holdout_variant_blockers(matrix: dict[str, Any]) -> tuple[int, list[str]]:
    cases = matrix.get("cases")
    if not isinstance(cases, list):
        return 0, ["holdout_cases_missing"]
    blockers: list[str] = []
    total = 0
    for case in cases:
        row = _object_dict(case)
        case_id = str(row.get("case_id") or "unknown")
        variants = row.get("holdout_utterance_variants")
        if not isinstance(variants, list) or len(variants) < 2:
            blockers.append(f"{case_id}.holdout_utterance_variants_too_low")
            continue
        primary = str(row.get("utterance") or "")
        normalized = {str(value).strip() for value in variants if str(value).strip()}
        total += len(normalized)
        if len(normalized) < 2:
            blockers.append(f"{case_id}.holdout_utterance_variants_too_low")
        if primary in normalized:
            blockers.append(f"{case_id}.holdout_repeats_primary_utterance")
    return total, blockers


def _blockers(matrix: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _object_dict(matrix.get("summary"))
    distinct_intents = _distinct_case_values(matrix, "expected_manager_intent")
    distinct_workflow_effects = _distinct_case_values(matrix, "expected_workflow_effect")
    holdout_variant_count, holdout_blockers = _holdout_variant_blockers(matrix)
    if matrix.get("artifact_type") != "accurate_intake_context_live_diagnostic_case_matrix":
        blockers.append("unexpected_matrix_artifact_type")
    if matrix.get("status") != "pass":
        blockers.append("matrix_status_not_pass")
    if matrix.get("plan_only") is not True:
        blockers.append("matrix_not_plan_only")
    for flag in (
        "live_llm_invoked",
        "live_provider_invoked",
        "live_provider_approved",
        "fooddb_used",
        "web_tavily_used",
        "runtime_truth_changed",
        "mutation_changed",
        "manager_context_packet_schema_changed",
        "shared_contract_changed",
        "product_readiness_claimed",
        "private_self_use_approved",
    ):
        if matrix.get(flag) is True:
            blockers.append(f"matrix_{flag}")
    if _case_ids(matrix) != list(REQUIRED_CASE_IDS):
        blockers.append("fixed_case_matrix_mismatch")
    if _int_value(summary.get("case_count")) < len(REQUIRED_CASE_IDS):
        blockers.append("case_count_too_low")
    if holdout_variant_count < len(REQUIRED_CASE_IDS) * 2:
        blockers.append("holdout_utterance_variant_count_too_low")
    blockers.extend(holdout_blockers)
    if _int_value(summary.get("compound_cases")) < 1:
        blockers.append("compound_case_missing")
    if _int_value(summary.get("ambiguity_cases")) < 1:
        blockers.append("ambiguity_case_missing")
    if _int_value(summary.get("pending_pin_cases")) < 1:
        blockers.append("pending_pin_case_missing")
    if _int_value(summary.get("target_candidate_cases")) < 1:
        blockers.append("target_candidate_case_missing")
    if len(distinct_intents) < 8:
        blockers.append("intent_diversity_too_low")
    if len(distinct_workflow_effects) < 8:
        blockers.append("workflow_effect_diversity_too_low")
    return blockers


def build_context_live_diagnostic_anti_overfit_guard_artifact(
    context_live_diagnostic_case_matrix: dict[str, Any],
) -> dict[str, Any]:
    matrix = _object_dict(context_live_diagnostic_case_matrix)
    blockers = _blockers(matrix)
    summary = _object_dict(matrix.get("summary"))
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_anti_overfit_guard",
            "status": "pass" if not blockers else "blocked",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "current_shell_compatibility_context_live_diagnostic_anti_overfit_guard",
            "diagnostic_only": True,
            "plan_only": True,
            "local_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "shared_contract_changed": False,
            "blockers": blockers,
            "summary": {
                "fixed_case_matrix_used": _case_ids(matrix) == list(REQUIRED_CASE_IDS),
                "case_count": _int_value(summary.get("case_count")),
                "holdout_utterance_variant_count": _holdout_variant_blockers(matrix)[0],
                "compound_cases": _int_value(summary.get("compound_cases")),
                "ambiguity_cases": _int_value(summary.get("ambiguity_cases")),
                "pending_pin_cases": _int_value(summary.get("pending_pin_cases")),
                "target_candidate_cases": _int_value(summary.get("target_candidate_cases")),
                "distinct_intent_count": len(
                    _distinct_case_values(matrix, "expected_manager_intent")
                ),
                "distinct_workflow_effect_count": len(
                    _distinct_case_values(matrix, "expected_workflow_effect")
                ),
            },
        }
    )


__all__ = ["build_context_live_diagnostic_anti_overfit_guard_artifact"]
