from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import REQUIRED_CASE_IDS


FORBIDDEN_TRUTHY_FLAGS = (
    "live_llm_invoked",
    "live_provider_invoked",
    "live_provider_approved",
    "ready_for_live_diagnostic_decision",
    "fooddb_used",
    "fooddb_evidence_used",
    "web_tavily_used",
    "websearch_evidence_used",
    "runtime_truth_changed",
    "mutation_changed",
    "manager_context_packet_schema_changed",
    "shared_contract_changed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "readiness_claimed",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return False


def _case_rows(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    return [_dict(row) for row in _list(matrix.get("cases"))]


def _holdout_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case.get("case_id") or "unknown_case")
        primary = str(case.get("utterance") or "").strip()
        variants = [
            str(value).strip()
            for value in _list(case.get("holdout_utterance_variants"))
            if str(value).strip()
        ]
        rows.append(
            {
                "case_id": case_id,
                "primary_utterance_present": bool(primary),
                "holdout_variant_count": len(set(variants)),
                "holdout_repeats_primary": primary in set(variants),
                "withheld_from_default_live_prompt": True,
                "human_review_required_before_promoting_failures": True,
            }
        )
    return rows


def _matrix_blockers(matrix: dict[str, Any], cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if matrix.get("artifact_type") != "accurate_intake_context_live_diagnostic_case_matrix":
        blockers.append("matrix.unexpected_artifact_type")
    if matrix.get("status") != "pass":
        blockers.append("matrix.status_not_pass")
    if matrix.get("plan_only") is not True:
        blockers.append("matrix.plan_only_not_true")
    if [str(case.get("case_id") or "") for case in cases] != list(REQUIRED_CASE_IDS):
        blockers.append("matrix.fixed_case_order_mismatch")
    for case in cases:
        case_id = str(case.get("case_id") or "unknown_case")
        primary = str(case.get("utterance") or "").strip()
        variants = {
            str(value).strip()
            for value in _list(case.get("holdout_utterance_variants"))
            if str(value).strip()
        }
        if len(variants) < 2:
            blockers.append(f"{case_id}.holdout_variants_too_low")
        if primary and primary in variants:
            blockers.append(f"{case_id}.holdout_repeats_primary_utterance")
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if _claim_is_true(matrix.get(flag)):
            blockers.append(f"matrix.{flag}")
    return blockers


def _anti_overfit_blockers(anti_overfit_guard: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if anti_overfit_guard.get("artifact_type") != "accurate_intake_context_live_diagnostic_anti_overfit_guard":
        blockers.append("anti_overfit_guard.unexpected_artifact_type")
    if anti_overfit_guard.get("status") != "pass":
        blockers.append("anti_overfit_guard.status_not_pass")
    summary = _dict(anti_overfit_guard.get("summary"))
    if summary.get("fixed_case_matrix_used") is not True:
        blockers.append("anti_overfit_guard.fixed_case_matrix_not_used")
    if int(summary.get("holdout_utterance_variant_count") or 0) < len(REQUIRED_CASE_IDS) * 2:
        blockers.append("anti_overfit_guard.holdout_variant_count_too_low")
    if int(summary.get("compound_cases") or 0) < 1:
        blockers.append("anti_overfit_guard.compound_cases_missing")
    if int(summary.get("ambiguity_cases") or 0) < 1:
        blockers.append("anti_overfit_guard.ambiguity_cases_missing")
    if int(summary.get("pending_pin_cases") or 0) < 1:
        blockers.append("anti_overfit_guard.pending_pin_cases_missing")
    if int(summary.get("target_candidate_cases") or 0) < 1:
        blockers.append("anti_overfit_guard.target_candidate_cases_missing")
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if _claim_is_true(anti_overfit_guard.get(flag)):
            blockers.append(f"anti_overfit_guard.{flag}")
    return blockers


def build_context_live_diagnostic_holdout_plan_artifact(
    *,
    context_live_diagnostic_case_matrix: dict[str, Any],
    context_live_diagnostic_anti_overfit_guard: dict[str, Any],
) -> dict[str, Any]:
    matrix = _dict(context_live_diagnostic_case_matrix)
    anti_overfit = _dict(context_live_diagnostic_anti_overfit_guard)
    cases = _case_rows(matrix)
    holdout_rows = _holdout_rows(cases)
    blockers = [
        *_matrix_blockers(matrix, cases),
        *_anti_overfit_blockers(anti_overfit),
    ]
    holdout_variant_count = sum(int(row["holdout_variant_count"]) for row in holdout_rows)
    cases_with_holdouts = sum(1 for row in holdout_rows if int(row["holdout_variant_count"]) >= 2)
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_holdout_plan",
            "status": "pass" if not blockers else "blocked",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pl_ce_context_live_diagnostic_holdout_overfit_control",
            "diagnostic_only": True,
            "fixture_only": True,
            "plan_only": True,
            "local_only": True,
            "fixed_case_matrix_used": [str(case.get("case_id") or "") for case in cases]
            == list(REQUIRED_CASE_IDS),
            "holdout_variants_withheld_from_default_live_prompt": True,
            "ad_hoc_live_case_selection_allowed": False,
            "provider_optimized_case_selection_allowed": False,
            "blocked_if_single_case_only": True,
            "human_review_required_before_promoting_failures": True,
            "semantic_owner": "future_live_manager_provider_when_human_approved",
            "deterministic_role": "validate_case_selection_not_select_intent",
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "ready_for_live_diagnostic_decision": False,
            "fooddb_used": False,
            "fooddb_evidence_used": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "shared_contract_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "readiness_claimed": False,
            "blockers": blockers,
            "summary": {
                "fixed_case_count": len(cases),
                "holdout_variant_count": holdout_variant_count,
                "withheld_holdout_variant_count": holdout_variant_count,
                "cases_with_holdouts": cases_with_holdouts,
                "case_ids": [str(case.get("case_id") or "") for case in cases],
                "case_count": len(cases),
                "compound_cases": int(_dict(anti_overfit.get("summary")).get("compound_cases") or 0),
                "ambiguity_cases": int(_dict(anti_overfit.get("summary")).get("ambiguity_cases") or 0),
                "pending_pin_cases": int(_dict(anti_overfit.get("summary")).get("pending_pin_cases") or 0),
                "target_candidate_cases": int(
                    _dict(anti_overfit.get("summary")).get("target_candidate_cases") or 0
                ),
            },
            "holdout_cases": holdout_rows,
        }
    )


__all__ = ["build_context_live_diagnostic_holdout_plan_artifact"]
