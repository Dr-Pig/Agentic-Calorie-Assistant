from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import REQUIRED_CASE_IDS


REQUIRED_INPUTS = (
    "context_live_diagnostic_case_matrix",
    "context_live_diagnostic_anti_overfit_guard",
    "context_live_provider_input_preflight",
    "context_live_response_contract_dry_run",
    "context_live_diagnostic_canary",
)

EXPECTED_ARTIFACT_TYPES = {
    "context_live_diagnostic_case_matrix": "accurate_intake_context_live_diagnostic_case_matrix",
    "context_live_diagnostic_anti_overfit_guard": "accurate_intake_context_live_diagnostic_anti_overfit_guard",
    "context_live_provider_input_preflight": "accurate_intake_context_live_provider_input_preflight",
    "context_live_response_contract_dry_run": "accurate_intake_context_live_response_contract_dry_run",
    "context_live_diagnostic_canary": "accurate_intake_context_live_diagnostic_canary",
}

EXPECTED_STATUSES = {
    "context_live_diagnostic_case_matrix": "pass",
    "context_live_diagnostic_anti_overfit_guard": "pass",
    "context_live_provider_input_preflight": "pass",
    "context_live_response_contract_dry_run": "pass",
    "context_live_diagnostic_canary": {"not_invoked", "live_diagnostic_pass"},
}

FORBIDDEN_TRUTHY_FLAGS = (
    "fooddb_used",
    "fooddb_truth_used",
    "fooddb_evidence_used",
    "web_tavily_used",
    "web_tavily_invoked",
    "websearch_evidence_used",
    "runtime_truth_changed",
    "mutation_changed",
    "manager_context_packet_schema_changed",
    "shared_contract_changed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "readiness_claimed",
    "user_facing_rollout",
    "production_selected",
    "production_db_used",
    "deterministic_selected_intent",
    "deterministic_selected_target",
    "raw_text_intent_router_used",
)


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


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _allowed_statuses(expected: Any) -> set[str]:
    if isinstance(expected, str):
        return {expected}
    if isinstance(expected, set | frozenset | list | tuple):
        return {str(item) for item in expected}
    return {str(expected)}


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return False


def _identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("artifact_type") != EXPECTED_ARTIFACT_TYPES[group_id]:
        blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    if _status(payload) not in _allowed_statuses(EXPECTED_STATUSES[group_id]):
        blockers.append(f"{group_id}.unexpected_status:{_status(payload)}")
    upstream_blockers = payload.get("blockers")
    if group_id == "context_live_diagnostic_canary" and _status(payload) == "not_invoked":
        if upstream_blockers not in (None, [], ["missing_provider_token"]):
            blockers.append(f"{group_id}.unexpected_not_invoked_blockers")
    elif upstream_blockers not in (None, []):
        blockers.append(f"{group_id}.upstream_blockers_present")
    return blockers


def _forbidden_claim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{group_id}.{flag}"
        for flag in FORBIDDEN_TRUTHY_FLAGS
        if _claim_is_true(payload.get(flag))
    ]


def _matrix_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _dict(payload.get("summary"))
    case_ids = payload.get("case_ids")
    if isinstance(case_ids, list) and [str(item) for item in case_ids] != list(REQUIRED_CASE_IDS):
        blockers.append("context_live_diagnostic_case_matrix.fixed_case_order_mismatch")
    if _int(summary.get("case_count")) != len(REQUIRED_CASE_IDS):
        blockers.append("context_live_diagnostic_case_matrix.case_count_mismatch")
    if _int(summary.get("target_candidate_cases")) < 1:
        blockers.append("context_live_diagnostic_case_matrix.target_candidate_cases_missing")
    if _int(summary.get("pending_pin_cases")) < 1:
        blockers.append("context_live_diagnostic_case_matrix.pending_pin_cases_missing")
    if _int(summary.get("ambiguity_cases")) < 1:
        blockers.append("context_live_diagnostic_case_matrix.ambiguity_cases_missing")
    return blockers


def _anti_overfit_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _dict(payload.get("summary"))
    if summary.get("fixed_case_matrix_used") is not True:
        blockers.append("context_live_diagnostic_anti_overfit_guard.fixed_case_matrix_not_used")
    if _int(summary.get("distinct_intent_count")) < 8:
        blockers.append("context_live_diagnostic_anti_overfit_guard.distinct_intent_count_too_low")
    if _int(summary.get("distinct_workflow_effect_count")) < 8:
        blockers.append("context_live_diagnostic_anti_overfit_guard.distinct_workflow_effect_count_too_low")
    if _int(summary.get("holdout_utterance_variant_count")) < 20:
        blockers.append("context_live_diagnostic_anti_overfit_guard.holdout_variant_count_too_low")
    return blockers


def _preflight_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("provider_call_ready") is not False:
        blockers.append("context_live_provider_input_preflight.provider_call_ready")
    if payload.get("human_approval_required_before_live_provider") is not True:
        blockers.append("context_live_provider_input_preflight.human_approval_required_missing")
    if payload.get("fixed_case_matrix_used") is not True:
        blockers.append("context_live_provider_input_preflight.fixed_case_matrix_not_used")
    if len(_list(payload.get("provider_inputs"))) != len(REQUIRED_CASE_IDS):
        blockers.append("context_live_provider_input_preflight.provider_input_count_mismatch")
    return blockers


def _dry_run_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _dict(payload.get("summary"))
    if payload.get("diagnostic_only") is not True:
        blockers.append("context_live_response_contract_dry_run.diagnostic_only_not_true")
    if payload.get("fixture_only") is not True:
        blockers.append("context_live_response_contract_dry_run.fixture_only_not_true")
    if payload.get("full_matrix_required") is not True:
        blockers.append("context_live_response_contract_dry_run.full_matrix_not_required")
    if payload.get("provider_call_ready") is not False:
        blockers.append("context_live_response_contract_dry_run.provider_call_ready")
    if _int(summary.get("case_count")) != len(REQUIRED_CASE_IDS):
        blockers.append("context_live_response_contract_dry_run.case_count_mismatch")
    if _int(summary.get("validated_response_count")) != len(REQUIRED_CASE_IDS):
        blockers.append("context_live_response_contract_dry_run.validated_response_count_mismatch")
    if _int(summary.get("blocked_response_count")) != 0:
        blockers.append("context_live_response_contract_dry_run.blocked_response_count_nonzero")
    if _int(summary.get("target_candidate_response_count")) < 1:
        blockers.append("context_live_response_contract_dry_run.target_candidate_response_missing")
    if _int(summary.get("ambiguity_preserved_response_count")) < 1:
        blockers.append("context_live_response_contract_dry_run.ambiguity_response_missing")
    return blockers


def _canary_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    status = _status(payload)
    summary = _dict(payload.get("summary"))
    if status == "not_invoked":
        if payload.get("live_invoked") is not False:
            blockers.append("context_live_diagnostic_canary.not_invoked_live_flag")
        if payload.get("failure_family") != "missing_provider_token":
            blockers.append("context_live_diagnostic_canary.not_invoked_failure_family_mismatch")
        return blockers
    if status == "live_diagnostic_pass":
        if payload.get("live_invoked") is not True:
            blockers.append("context_live_diagnostic_canary.live_invoked_not_true")
        if payload.get("live_provider_invoked") is not True:
            blockers.append("context_live_diagnostic_canary.live_provider_not_true")
        if payload.get("semantic_owner") != "live_manager_provider":
            blockers.append("context_live_diagnostic_canary.semantic_owner_not_live_manager")
        if payload.get("response_contract_status") != "pass":
            blockers.append("context_live_diagnostic_canary.response_contract_not_pass")
        if _int(summary.get("provider_output_count")) < 1:
            blockers.append("context_live_diagnostic_canary.provider_output_count_missing")
        if _int(summary.get("blocked_response_count")) != 0:
            blockers.append("context_live_diagnostic_canary.blocked_response_count_nonzero")
        return blockers
    blockers.append(f"context_live_diagnostic_canary.unsupported_status:{status}")
    return blockers


def _artifact_statuses(inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "status": _status(payload),
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in inputs.items()
    }


def build_context_live_diagnostic_review_pack_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = {group_id: _dict(input_artifacts.get(group_id)) for group_id in REQUIRED_INPUTS}
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_identity_blockers(group_id, payload))
        blockers.extend(_forbidden_claim_blockers(group_id, payload))
    blockers.extend(_matrix_blockers(inputs["context_live_diagnostic_case_matrix"]))
    blockers.extend(_anti_overfit_blockers(inputs["context_live_diagnostic_anti_overfit_guard"]))
    blockers.extend(_preflight_blockers(inputs["context_live_provider_input_preflight"]))
    blockers.extend(_dry_run_blockers(inputs["context_live_response_contract_dry_run"]))
    blockers.extend(_canary_blockers(inputs["context_live_diagnostic_canary"]))
    blockers = list(dict.fromkeys(blockers))

    canary = inputs["context_live_diagnostic_canary"]
    canary_status = _status(canary)
    live_invoked = canary.get("live_invoked") is True
    if blockers:
        status = "blocked"
    elif canary_status == "live_diagnostic_pass":
        status = "context_live_diagnostic_review_ready_with_live_canary"
    else:
        status = "context_live_diagnostic_review_ready_without_live_canary"
    canary_summary = _dict(canary.get("summary"))
    matrix_summary = _dict(inputs["context_live_diagnostic_case_matrix"].get("summary"))
    dry_summary = _dict(inputs["context_live_response_contract_dry_run"].get("summary"))
    anti_summary = _dict(inputs["context_live_diagnostic_anti_overfit_guard"].get("summary"))
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_review_pack",
            "status": status,
            "claim_scope": "pl_ce_context_live_diagnostic_review_for_human_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "required_inputs": list(REQUIRED_INPUTS),
            "blockers": blockers,
            "included_artifact_statuses": _artifact_statuses(inputs),
            "diagnostic_only": True,
            "aggregate_only": True,
            "human_review_required": True,
            "review_required_before_provider_activation": True,
            "fixed_case_matrix_used": True,
            "blocked_live_canary_is_not_pass": True,
            "live_canary_status": canary_status,
            "live_llm_invoked": live_invoked,
            "live_provider_invoked": live_invoked,
            "semantic_owner": "live_manager_provider" if live_invoked else "not_invoked",
            "deterministic_role": "validate_artifacts_not_select_intent",
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "fooddb_used": False,
            "fooddb_evidence_used": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "readiness_claimed": False,
            "summary": {
                "fixed_case_count": _int(matrix_summary.get("case_count")),
                "dry_run_validated_response_count": _int(
                    dry_summary.get("validated_response_count")
                ),
                "dry_run_blocked_response_count": _int(dry_summary.get("blocked_response_count")),
                "anti_overfit_distinct_intent_count": _int(
                    anti_summary.get("distinct_intent_count")
                ),
                "anti_overfit_holdout_variant_count": _int(
                    anti_summary.get("holdout_utterance_variant_count")
                ),
                "live_provider_input_count": _int(canary_summary.get("provider_input_count")),
                "live_provider_output_count": _int(canary_summary.get("provider_output_count")),
                "live_blocked_response_count": _int(canary_summary.get("blocked_response_count")),
                "live_target_candidate_response_count": _int(
                    canary_summary.get("target_candidate_response_count")
                ),
                "live_ambiguity_preserved_response_count": _int(
                    canary_summary.get("ambiguity_preserved_response_count")
                ),
            },
        }
    )


__all__ = [
    "REQUIRED_INPUTS",
    "build_context_live_diagnostic_review_pack_artifact",
]
