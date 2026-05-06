from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
)


LIVE_STAGES = ("single-case", "full-matrix")


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _case_ids(canary: dict[str, Any]) -> list[str]:
    output_ids = [
        str(_dict(output).get("case_id") or "")
        for output in _list(canary.get("provider_outputs"))
        if str(_dict(output).get("case_id") or "")
    ]
    if output_ids:
        return output_ids
    traces = [
        str(_dict(trace).get("case_id") or "")
        for trace in _list(canary.get("provider_traces"))
        if str(_dict(trace).get("case_id") or "")
    ]
    return traces


def _canary_summary(canary: dict[str, Any]) -> dict[str, Any]:
    summary = _dict(canary.get("summary"))
    provider_output_count = _int(summary.get("provider_output_count"))
    provider_input_count = _int(summary.get("provider_input_count"))
    case_ids = _case_ids(canary)
    if not provider_output_count and case_ids:
        provider_output_count = len(case_ids)
    return {
        "provider_input_count": provider_input_count,
        "provider_output_count": provider_output_count,
        "case_ids": case_ids,
        "blocked_response_count": _int(summary.get("blocked_response_count")),
    }


def _base_blockers(canary: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if canary.get("artifact_type") != "accurate_intake_context_live_diagnostic_canary":
        blockers.append("canary.unexpected_artifact_type")
    if canary.get("status") != "live_diagnostic_pass":
        blockers.append("canary.status_not_live_diagnostic_pass")
    if canary.get("live_invoked") is not True or canary.get("live_provider_invoked") is not True:
        blockers.append("canary.live_provider_not_invoked")
    if canary.get("response_contract_status") != "pass":
        blockers.append("canary.response_contract_not_pass")
    if _canary_summary(canary)["blocked_response_count"] != 0:
        blockers.append("canary.blocked_response_count_nonzero")
    for flag in (
        "fooddb_used",
        "web_tavily_used",
        "runtime_truth_changed",
        "mutation_changed",
        "manager_context_packet_schema_changed",
        "product_readiness_claimed",
        "private_self_use_approved",
        "readiness_claimed",
    ):
        if canary.get(flag) is True:
            blockers.append(f"canary.{flag}")
    return blockers


def _single_case_blockers(canary: dict[str, Any]) -> list[str]:
    summary = _canary_summary(canary)
    blockers: list[str] = []
    if summary["provider_output_count"] != 1:
        blockers.append("single_case_live_probe_expected_one_provider_output")
    if len(summary["case_ids"]) != 1:
        blockers.append("single_case_live_probe_expected_one_case_id")
    elif summary["case_ids"][0] not in REQUIRED_CASE_IDS:
        blockers.append("single_case_live_probe_unknown_case_id")
    return blockers


def _full_matrix_blockers(
    canary: dict[str, Any],
    prior_single_case_stage_gate: dict[str, Any],
) -> list[str]:
    summary = _canary_summary(canary)
    blockers: list[str] = []
    if prior_single_case_stage_gate.get("status") != "context_live_single_case_probe_pass":
        blockers.append("single_case_stage_gate_required_before_full_matrix")
    if summary["provider_output_count"] != len(REQUIRED_CASE_IDS):
        blockers.append("full_matrix_live_probe_output_count_mismatch")
    if summary["case_ids"] and summary["case_ids"] != list(REQUIRED_CASE_IDS):
        blockers.append("full_matrix_live_probe_case_order_mismatch")
    return blockers


def build_context_live_diagnostic_stage_gate_artifact(
    *,
    live_stage: str,
    context_live_diagnostic_canary: dict[str, Any],
    prior_single_case_stage_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    canary = _dict(context_live_diagnostic_canary)
    prior = _dict(prior_single_case_stage_gate)
    if live_stage not in LIVE_STAGES:
        raise ValueError(f"Unsupported context live diagnostic live_stage={live_stage}")
    blockers = _base_blockers(canary)
    if live_stage == "single-case":
        blockers.extend(_single_case_blockers(canary))
    else:
        blockers.extend(_full_matrix_blockers(canary, prior))
    blockers = list(dict.fromkeys(blockers))
    if blockers:
        status = "blocked"
    elif live_stage == "single-case":
        status = "context_live_single_case_probe_pass"
    else:
        status = "context_live_full_matrix_probe_pass"
    summary = _canary_summary(canary)
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_stage_gate",
            "status": status,
            "live_stage": live_stage,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pl_ce_context_live_diagnostic_stage_order_gate",
            "blockers": blockers,
            "diagnostic_only": True,
            "local_only": True,
            "live_llm_invoked": canary.get("live_llm_invoked") is True,
            "live_provider_invoked": canary.get("live_provider_invoked") is True,
            "single_case_live_probe_required": live_stage == "single-case",
            "single_case_live_probe_passed": status == "context_live_single_case_probe_pass",
            "full_matrix_live_probe_requires_single_case": True,
            "full_matrix_live_probe_allowed": status == "context_live_full_matrix_probe_pass",
            "ad_hoc_live_case_selection_allowed": False,
            "fixed_case_matrix_used": True,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "shared_contract_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "readiness_claimed": False,
            "semantic_owner": "live_manager_provider",
            "deterministic_role": "validate_live_stage_order_not_select_intent",
            "summary": summary,
        }
    )


__all__ = ["LIVE_STAGES", "build_context_live_diagnostic_stage_gate_artifact"]
