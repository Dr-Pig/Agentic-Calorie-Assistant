from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_pl_ce_browser_activation_evidence_gate import (
    BROWSER_ARTIFACTS,
    EXPECTED_STATUSES as BROWSER_GATE_EXPECTED_STATUSES,
    REQUIRED_INPUTS as BROWSER_GATE_REQUIRED_INPUTS,
)
from app.composition.accurate_intake_pl_ce_local_mvp_candidate_bundle import (
    EXPECTED_STATUSES as LOCAL_MVP_EXPECTED_STATUSES,
    REQUIRED_INPUTS as LOCAL_MVP_REQUIRED_INPUTS,
)


REQUIRED_INPUTS = (
    "pl_ce_local_mvp_candidate_bundle",
    "pl_ce_browser_activation_evidence_gate",
)

EXPECTED_STATUSES = {
    "pl_ce_local_mvp_candidate_bundle": "pl_ce_local_mvp_candidate_ready_for_human_review",
    "pl_ce_browser_activation_evidence_gate": "browser_activation_evidence_ready_for_human_review",
}

EXPECTED_ARTIFACT_TYPES = {
    "pl_ce_local_mvp_candidate_bundle": "accurate_intake_pl_ce_local_mvp_candidate_bundle",
    "pl_ce_browser_activation_evidence_gate": "accurate_intake_pl_ce_browser_activation_evidence_gate",
}

EXPECTED_UPSTREAM_REQUIRED_INPUTS = {
    "pl_ce_local_mvp_candidate_bundle": tuple(LOCAL_MVP_REQUIRED_INPUTS),
    "pl_ce_browser_activation_evidence_gate": tuple(BROWSER_GATE_REQUIRED_INPUTS),
}

EXPECTED_NESTED_STATUSES = {
    "pl_ce_local_mvp_candidate_bundle": dict(LOCAL_MVP_EXPECTED_STATUSES),
    "pl_ce_browser_activation_evidence_gate": dict(BROWSER_GATE_EXPECTED_STATUSES),
}

FORBIDDEN_TRUTHY_FLAGS = (
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "live_provider_called",
    "web_tavily_used",
    "web_tavily_invoked",
    "websearch_evidence_used",
    "fooddb_evidence_used",
    "fooddb_truth_updated",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "manager_context_packet_schema_changed",
    "runtime_truth_changed",
    "mutation_changed",
    "mutation_authority",
    "frontend_semantic_owner",
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "canonical_eval_promoted",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


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


def _allowed_statuses(expected_status: Any) -> set[str]:
    if isinstance(expected_status, str):
        return {expected_status}
    if isinstance(expected_status, set | frozenset | tuple | list):
        return {str(status) for status in expected_status}
    return {str(expected_status)}


def _identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _status(payload) != EXPECTED_STATUSES[group_id]:
        blockers.append(f"{group_id}.unexpected_status:{_status(payload)}")
    if payload.get("artifact_type") != EXPECTED_ARTIFACT_TYPES[group_id]:
        blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    return blockers


def _claim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{group_id}.{flag}"
        for flag in FORBIDDEN_TRUTHY_FLAGS
        if _claim_is_true(payload.get(flag))
    ]


def _list_contains_all(value: Any, expected_values: tuple[str, ...]) -> bool:
    if not isinstance(value, list):
        return False
    return set(expected_values).issubset(set(str(item) for item in value))


def _structural_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("artifact_schema_version") != "1.0":
        blockers.append(f"{group_id}.missing_artifact_schema_version")

    upstream_blockers = payload.get("blockers")
    if upstream_blockers != []:
        suffix = "upstream_blockers_present" if upstream_blockers else "upstream_blockers_missing"
        blockers.append(f"{group_id}.{suffix}")

    if not _list_contains_all(
        payload.get("required_inputs"),
        EXPECTED_UPSTREAM_REQUIRED_INPUTS[group_id],
    ):
        blockers.append(f"{group_id}.required_inputs_incomplete")

    included_statuses = payload.get("included_artifact_statuses")
    if not isinstance(included_statuses, dict) or not included_statuses:
        blockers.append(f"{group_id}.included_artifact_statuses_missing")
    elif not set(EXPECTED_UPSTREAM_REQUIRED_INPUTS[group_id]).issubset(included_statuses):
        blockers.append(f"{group_id}.included_artifact_statuses_incomplete")
    else:
        for input_id, expected_status in EXPECTED_NESTED_STATUSES[group_id].items():
            nested_status = _object_dict(included_statuses.get(input_id))
            nested_status_value = str(nested_status.get("status") or "")
            if nested_status_value not in _allowed_statuses(expected_status):
                blockers.append(
                    f"{group_id}.included_artifact_statuses."
                    f"{input_id}.unexpected_status:{nested_status.get('status')}"
                )
            if group_id == "pl_ce_browser_activation_evidence_gate" and input_id in BROWSER_ARTIFACTS:
                if nested_status.get("browser_executed") is not True:
                    blockers.append(
                        f"{group_id}.included_artifact_statuses."
                        f"{input_id}.browser_not_executed"
                    )

    if payload.get("aggregate_only") is not True:
        blockers.append(f"{group_id}.aggregate_only_not_true")
    if payload.get("self_generated_evidence_used") is not False:
        blockers.append(f"{group_id}.self_generated_evidence_not_false")
    if payload.get("review_required_before_provider_call") is not True:
        blockers.append(f"{group_id}.review_required_before_provider_call_not_true")
    return blockers


def _group_specific_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if group_id == "pl_ce_local_mvp_candidate_bundle":
        if payload.get("activation_gate_status") != "blocked_pending_human_and_browser_activation":
            blockers.append("pl_ce_local_mvp_candidate_bundle.unexpected_activation_gate_status")
        fooddb_dependency = _object_dict(payload.get("fooddb_dependency"))
        if fooddb_dependency.get("fooddb_artifact_status") != "blocked_waiting_for_fdb_artifact":
            blockers.append("pl_ce_local_mvp_candidate_bundle.fooddb_stop_gate_missing")
        if fooddb_dependency.get("ready_for_fdb_integration") is not False:
            blockers.append("pl_ce_local_mvp_candidate_bundle.fooddb_integration_not_blocked")
        activation_policy = _object_dict(
            _object_dict(payload.get("browser_gate_policy")).get("activation_gate")
        )
        if activation_policy.get("require_browser_execution") is not True:
            blockers.append("pl_ce_local_mvp_candidate_bundle.activation_browser_not_required")
        if activation_policy.get("browser_executed_required") is not True:
            blockers.append(
                "pl_ce_local_mvp_candidate_bundle.activation_browser_execution_not_required"
            )
    if group_id == "pl_ce_browser_activation_evidence_gate":
        if payload.get("all_required_browser_artifacts_executed") is not True:
            blockers.append(
                "pl_ce_browser_activation_evidence_gate.browser_artifacts_not_all_executed"
            )
        if payload.get("browser_executed_required") is not True:
            blockers.append("pl_ce_browser_activation_evidence_gate.browser_not_required")
        if not _list_contains_all(payload.get("browser_required_inputs"), tuple(BROWSER_ARTIFACTS)):
            blockers.append("pl_ce_browser_activation_evidence_gate.browser_inputs_incomplete")
        summary = _object_dict(payload.get("summary"))
        if summary.get("browser_artifact_count") != len(BROWSER_ARTIFACTS):
            blockers.append("pl_ce_browser_activation_evidence_gate.browser_artifact_count_mismatch")
        if summary.get("browser_executed_count") != len(BROWSER_ARTIFACTS):
            blockers.append("pl_ce_browser_activation_evidence_gate.browser_executed_count_mismatch")
        for flag in (
            "requires_three_distinct_pages",
            "requires_seven_day_today_diary",
            "requires_short_term_context_render",
            "requires_visual_qa",
            "requires_no_debug_trace_leak",
        ):
            if summary.get(flag) is not True:
                blockers.append(f"pl_ce_browser_activation_evidence_gate.{flag}_not_true")
    return blockers


def _artifact_statuses(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "status": _status(payload),
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in payloads.items()
    }


def build_pl_ce_activation_review_manifest_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = {
        group_id: _object_dict(input_artifacts.get(group_id))
        for group_id in REQUIRED_INPUTS
    }
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_identity_blockers(group_id, payload))
        blockers.extend(_claim_blockers(group_id, payload))
        blockers.extend(_structural_blockers(group_id, payload))
        blockers.extend(_group_specific_blockers(group_id, payload))
    status = "pl_ce_activation_review_manifest_ready" if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_activation_review_manifest",
            "status": status,
            "claim_scope": "pl_ce_activation_review_manifest_for_human_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "required_inputs": list(REQUIRED_INPUTS),
            "blockers": blockers,
            "included_artifact_statuses": _artifact_statuses(inputs),
            "review_checkpoints": {
                "local_mvp_candidate_bundle": (
                    "ready_for_human_review"
                    if inputs["pl_ce_local_mvp_candidate_bundle"].get("status")
                    == EXPECTED_STATUSES["pl_ce_local_mvp_candidate_bundle"]
                    else "blocked_or_missing"
                ),
                "browser_activation_evidence_gate": (
                    "ready_for_human_review"
                    if inputs["pl_ce_browser_activation_evidence_gate"].get("status")
                    == EXPECTED_STATUSES["pl_ce_browser_activation_evidence_gate"]
                    else "blocked_or_missing"
                ),
            },
            "remaining_stop_gates": {
                "fooddb_artifact_status": "blocked_waiting_for_fdb_artifact",
                "live_provider_status": "blocked_pending_human_approval",
                "websearch_runtime_status": "blocked_out_of_scope_for_pl_ce",
                "readiness_claim_status": "blocked_not_requested",
                "mutation_status": "blocked_no_mutation_authority",
            },
            "next_allowed_actions": [
                "human_review_local_candidate_bundle",
                "human_review_browser_activation_evidence",
                "prepare_limited_live_diagnostic_plan_only_after_human_approval",
            ],
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "aggregate_only": True,
            "self_generated_evidence_used": False,
            "human_review_required": True,
            "live_diagnostic_human_approval_required": True,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "shared_contract_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "live_provider_called": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "fooddb_evidence_used": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
            "manager_context_packet_schema_changed": False,
            "mutation_authority": False,
        }
    )


__all__ = [
    "EXPECTED_ARTIFACT_TYPES",
    "EXPECTED_STATUSES",
    "REQUIRED_INPUTS",
    "build_pl_ce_activation_review_manifest_artifact",
]
