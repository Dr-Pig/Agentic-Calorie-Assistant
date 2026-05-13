from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .fooddb_grokfast_live_diagnostic_case_catalog import REQUIRED_CASE_IDS


LIVE_STAGES = ("single-case", "full-matrix")


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _summary(diagnostic: dict[str, Any]) -> dict[str, Any]:
    return _dict(diagnostic.get("summary"))


def _case_ids(diagnostic: dict[str, Any]) -> list[str]:
    selected = [
        str(case_id or "").strip()
        for case_id in _list(diagnostic.get("selected_case_ids"))
        if str(case_id or "").strip()
    ]
    if selected:
        return selected
    return [
        str(_dict(case).get("case_id") or "").strip()
        for case in _list(diagnostic.get("cases"))
        if str(_dict(case).get("case_id") or "").strip()
    ]


def _base_blockers(diagnostic: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if diagnostic.get("artifact_type") != "accurate_intake_grokfast_fooddb_packet_smoke":
        blockers.append("diagnostic.unexpected_artifact_type")
    if diagnostic.get("status") != "pass":
        blockers.append("diagnostic.status_not_pass")
    if diagnostic.get("live_provider_used") is not True:
        blockers.append("diagnostic.live_provider_not_used")
    for flag in (
        "runtime_truth_changed",
        "runtime_mutation_attempted",
        "readiness_claimed",
        "self_use_approved",
        "production_selected",
    ):
        if diagnostic.get(flag) is True:
            blockers.append(f"diagnostic.{flag}")
    return blockers


def _single_case_blockers(diagnostic: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    case_ids = _case_ids(diagnostic)
    if len(case_ids) != 1:
        blockers.append("single_case_live_probe_expected_one_case_id")
    elif case_ids[0] not in REQUIRED_CASE_IDS:
        blockers.append("single_case_live_probe_unknown_case_id")
    if int(_summary(diagnostic).get("case_count", 0) or 0) != 1:
        blockers.append("single_case_live_probe_case_count_mismatch")
    return blockers


def _full_matrix_blockers(
    diagnostic: dict[str, Any],
    prior_single_case_stage_gate: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if prior_single_case_stage_gate.get("status") != "fooddb_live_single_case_probe_pass":
        blockers.append("single_case_stage_gate_required_before_full_matrix")
    case_ids = _case_ids(diagnostic)
    if case_ids != list(REQUIRED_CASE_IDS):
        blockers.append("full_matrix_live_probe_case_order_mismatch")
    if int(_summary(diagnostic).get("case_count", 0) or 0) != len(REQUIRED_CASE_IDS):
        blockers.append("full_matrix_live_probe_case_count_mismatch")
    return blockers


def build_fooddb_live_diagnostic_stage_gate_artifact(
    *,
    live_stage: str,
    fooddb_live_diagnostic: dict[str, Any],
    prior_single_case_stage_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if live_stage not in LIVE_STAGES:
        raise ValueError(f"Unsupported fooddb live diagnostic live_stage={live_stage}")
    diagnostic = _dict(fooddb_live_diagnostic)
    prior = _dict(prior_single_case_stage_gate)
    blockers = _base_blockers(diagnostic)
    if live_stage == "single-case":
        blockers.extend(_single_case_blockers(diagnostic))
    else:
        blockers.extend(_full_matrix_blockers(diagnostic, prior))
    blockers = list(dict.fromkeys(blockers))
    if blockers:
        status = "blocked"
    elif live_stage == "single-case":
        status = "fooddb_live_single_case_probe_pass"
    else:
        status = "fooddb_live_full_matrix_probe_pass"
    case_ids = _case_ids(diagnostic)
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_fooddb_live_diagnostic_stage_gate",
        "status": status,
        "live_stage": live_stage,
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "claim_scope": "fooddb_live_diagnostic_stage_order_gate",
        "blockers": blockers,
        "diagnostic_only": True,
        "local_only": True,
        "live_provider_invoked": diagnostic.get("live_provider_used") is True,
        "single_case_live_probe_required": live_stage == "single-case",
        "single_case_live_probe_passed": status == "fooddb_live_single_case_probe_pass",
        "full_matrix_live_probe_requires_single_case": True,
        "full_matrix_live_probe_allowed": status == "fooddb_live_full_matrix_probe_pass",
        "ad_hoc_live_case_selection_allowed": False,
        "fixed_case_matrix_used": True,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "readiness_claimed": False,
        "summary": {
            "case_ids": case_ids,
            "provider_output_count": int(_summary(diagnostic).get("case_count", 0) or 0),
            "pass_count": int(_summary(diagnostic).get("pass_count", 0) or 0),
            "fail_count": int(_summary(diagnostic).get("fail_count", 0) or 0),
        },
    }


__all__ = ["LIVE_STAGES", "build_fooddb_live_diagnostic_stage_gate_artifact"]
