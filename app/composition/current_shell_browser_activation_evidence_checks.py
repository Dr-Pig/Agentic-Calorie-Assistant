from __future__ import annotations

from typing import Any

from app.composition import current_shell_body_observation_gate_contract as body_obs
from app.composition.current_shell_browser_activation_contract import (
    EXPECTED_ARTIFACT_TYPES,
    EXPECTED_SMOKE_IDS,
    EXPECTED_STATUSES,
    FORBIDDEN_TRUTHY_FLAGS,
    REQUIRED_INPUTS,
    REQUIRED_CURRENT_SHELL_STEPS,
    REQUIRED_TRUE_FLAGS,
    route_backed_macro_budget_truth_blockers,
)
from app.composition.current_shell_browser_activation_evidence_leaf_checks import (
    body_noplan_blockers,
    body_read_model_blockers,
    int_value,
    self_use_flow_blockers,
    target_candidate_blockers,
)
from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
    LEGACY_LOCAL_MVP_ARTIFACT_TYPES,
    LEGACY_LOCAL_MVP_GROUP_IDS,
    LEGACY_LOCAL_MVP_READY_STATUSES,
    matches_alias,
)
from app.composition.current_shell_fooddb_triad_same_truth_contract import (
    fooddb_triad_same_truth_blockers,
)


def object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def input_payloads(input_artifacts: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: object_dict(
            input_artifacts.get(group_id)
            if group_id != CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID
            else input_artifacts.get(group_id)
            or next(
                (
                    input_artifacts.get(legacy_group_id)
                    for legacy_group_id in LEGACY_LOCAL_MVP_GROUP_IDS
                    if isinstance(input_artifacts.get(legacy_group_id), dict)
                ),
                {},
            )
        )
        for group_id in REQUIRED_INPUTS
    }


def input_blockers(inputs: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(identity_blockers(group_id, payload))
        blockers.extend(forbidden_claim_blockers(group_id, payload))
        blockers.extend(required_true_blockers(group_id, payload))
        blockers.extend(group_specific_blockers(group_id, payload))
    return blockers


def artifact_statuses(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "smoke_id": payload.get("smoke_id") or "not_available",
            "status": status(payload),
            "browser_executed": payload.get("browser_executed", "not_applicable"),
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in payloads.items()
    }


def identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if group_id == CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID:
        if not matches_alias(
            payload.get("status"),
            EXPECTED_STATUSES[group_id],
            *LEGACY_LOCAL_MVP_READY_STATUSES,
        ):
            blockers.append(f"{group_id}.unexpected_status:{status(payload)}")
    elif status(payload) != EXPECTED_STATUSES[group_id]:
        blockers.append(f"{group_id}.unexpected_status:{status(payload)}")
    expected_type = EXPECTED_ARTIFACT_TYPES.get(group_id)
    if group_id == CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID:
        if expected_type and not matches_alias(
            payload.get("artifact_type"),
            expected_type,
            *LEGACY_LOCAL_MVP_ARTIFACT_TYPES,
        ):
            blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    elif expected_type and payload.get("artifact_type") != expected_type:
        blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    expected_smoke_id = EXPECTED_SMOKE_IDS.get(group_id)
    if expected_smoke_id and payload.get("smoke_id") != expected_smoke_id:
        blockers.append(f"{group_id}.unexpected_smoke_id:{payload.get('smoke_id')}")
    return blockers


def forbidden_claim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{group_id}.{flag}"
        for flag in FORBIDDEN_TRUTHY_FLAGS
        if claim_is_true(payload.get(flag))
    ]


def required_true_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for flag in REQUIRED_TRUE_FLAGS.get(group_id, ()):
        if payload.get(flag) is not True:
            suffix = "browser_not_executed" if flag == "browser_executed" else f"{flag}_not_true"
            blockers.append(f"{group_id}.{suffix}")
    return blockers


def claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return False


def group_specific_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    blockers.extend(body_obs.body_observation_same_truth_blockers(group_id, payload))
    if group_id == CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID:
        if payload.get("activation_gate_status") != "blocked_pending_human_and_browser_activation":
            blockers.append(f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID}.unexpected_activation_gate_status")
    if group_id == "product_pages_browser_smoke":
        blockers.extend(route_backed_macro_budget_truth_blockers(group_id, payload))
        blockers.extend(fooddb_triad_same_truth_blockers(group_id, payload))
        blockers.extend(body_read_model_blockers(payload))
    if group_id == "product_pages_seven_day_diary_smoke":
        if int_value(payload.get("day_count_checked")) < 7:
            blockers.append("product_pages_seven_day_diary_smoke.seven_day_window_incomplete")
        if int_value(payload.get("manager_provider_call_count")) != 0:
            blockers.append("product_pages_seven_day_diary_smoke.manager_provider_called")
    if group_id == "product_pages_target_candidate_ui_smoke":
        blockers.extend(target_candidate_blockers(payload))
    if group_id == "product_pages_body_noplan_degraded_smoke":
        blockers.extend(body_noplan_blockers(payload))
    if group_id == "current_shell_fixture_e2e":
        completed_steps = {str(item) for item in list_value(payload.get("completed_current_shell_steps"))}
        for required_step in REQUIRED_CURRENT_SHELL_STEPS:
            if required_step not in completed_steps:
                blockers.append(f"current_shell_fixture_e2e.completed_step_missing:{required_step}")
    if group_id == "product_pages_self_use_flow_gate":
        blockers.extend(self_use_flow_blockers(payload))
    return blockers

