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


def _blockers(matrix: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _object_dict(matrix.get("summary"))
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
    if _int_value(summary.get("compound_cases")) < 1:
        blockers.append("compound_case_missing")
    if _int_value(summary.get("ambiguity_cases")) < 1:
        blockers.append("ambiguity_case_missing")
    if _int_value(summary.get("pending_pin_cases")) < 1:
        blockers.append("pending_pin_case_missing")
    if _int_value(summary.get("target_candidate_cases")) < 1:
        blockers.append("target_candidate_case_missing")
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
            "claim_scope": "pl_ce_context_live_diagnostic_anti_overfit_guard",
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
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": blockers,
            "summary": {
                "fixed_case_matrix_used": _case_ids(matrix) == list(REQUIRED_CASE_IDS),
                "case_count": _int_value(summary.get("case_count")),
                "compound_cases": _int_value(summary.get("compound_cases")),
                "ambiguity_cases": _int_value(summary.get("ambiguity_cases")),
                "pending_pin_cases": _int_value(summary.get("pending_pin_cases")),
                "target_candidate_cases": _int_value(summary.get("target_candidate_cases")),
            },
        }
    )


__all__ = ["build_context_live_diagnostic_anti_overfit_guard_artifact"]
