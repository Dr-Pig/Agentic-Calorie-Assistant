from __future__ import annotations

from typing import Any

from app.composition import current_shell_body_observation_gate_contract as body_obs
from app.composition.current_shell_product_pages_flow_contract import (
    BROWSER_INPUTS,
    EXPECTED_ARTIFACT_TYPES,
    EXPECTED_PASS_TYPES,
    EXPECTED_SMOKE_IDS,
    EXPECTED_STATUSES,
    FORBIDDEN_TRUTHY_FLAGS,
    REQUIRED_CURRENT_SHELL_STEPS,
    REQUIRED_TRUE_FLAGS,
)

def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


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


def _identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _status(payload) != EXPECTED_STATUSES[group_id]:
        blockers.append(f"{group_id}.unexpected_status:{_status(payload)}")
    expected_type = EXPECTED_ARTIFACT_TYPES.get(group_id)
    if expected_type and payload.get("artifact_type") != expected_type:
        blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    expected_pass_type = EXPECTED_PASS_TYPES.get(group_id)
    if expected_pass_type and payload.get("pass_type") != expected_pass_type:
        blockers.append(f"{group_id}.unexpected_pass_type:{payload.get('pass_type')}")
    expected_smoke_id = EXPECTED_SMOKE_IDS.get(group_id)
    if expected_smoke_id and payload.get("smoke_id") != expected_smoke_id:
        blockers.append(f"{group_id}.unexpected_smoke_id:{payload.get('smoke_id')}")
    if payload.get("blockers") not in (None, []):
        blockers.append(f"{group_id}.upstream_blockers_present")
    return blockers


def _required_true_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for flag in REQUIRED_TRUE_FLAGS.get(group_id, ()):
        if payload.get(flag) is not True:
            suffix = "browser_not_executed" if flag == "browser_executed" else f"{flag}_not_true"
            blockers.append(f"{group_id}.{suffix}")
    return blockers


def _forbidden_claim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{group_id}.{flag}"
        for flag in FORBIDDEN_TRUTHY_FLAGS
        if _claim_is_true(payload.get(flag))
    ]


def _group_specific_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    blockers.extend(body_obs.body_observation_same_truth_blockers(group_id, payload))
    if group_id == "product_pages_renderer_source_map":
        summary = _object_dict(payload.get("summary"))
        if _int_value(summary.get("page_count")) != 3:
            blockers.append("product_pages_renderer_source_map.page_count_mismatch")
        if _int_value(summary.get("selector_count")) < 30:
            blockers.append("product_pages_renderer_source_map.selector_count_too_low")
        if _int_value(summary.get("endpoint_count")) < 7:
            blockers.append("product_pages_renderer_source_map.endpoint_count_too_low")
    if group_id == "product_pages_renderer_source_closure_gate":
        summary = _object_dict(payload.get("summary"))
        if _int_value(summary.get("page_count")) != 3:
            blockers.append("product_pages_renderer_source_closure_gate.page_count_mismatch")
        if _int_value(summary.get("endpoint_method_contract_count")) < 7:
            blockers.append(
                "product_pages_renderer_source_closure_gate.endpoint_method_contract_count_too_low"
            )
    if group_id == "product_pages_seven_day_diary_smoke":
        if _int_value(payload.get("day_count_checked")) < 7:
            blockers.append("product_pages_seven_day_diary_smoke.seven_day_window_incomplete")
        if _int_value(payload.get("manager_provider_call_count")) != 0:
            blockers.append("product_pages_seven_day_diary_smoke.manager_provider_called")
    if group_id == "product_pages_body_noplan_degraded_smoke":
        body_values = _object_dict(payload.get("body_values"))
        today_values = _object_dict(payload.get("today_values"))
        for field in ("daily_target", "tdee", "active_target", "remaining"):
            if str(body_values.get(field) or "") != "--":
                blockers.append(f"product_pages_body_noplan_degraded_smoke.body_{field}_not_hidden")
        for field in ("budget", "consumed", "remaining"):
            if str(today_values.get(field) or "") != "0":
                blockers.append(f"product_pages_body_noplan_degraded_smoke.today_{field}_not_zero")
    if group_id == "product_pages_target_candidate_ui_smoke":
        if _int_value(payload.get("target_candidate_count_rendered")) < 2:
            blockers.append("product_pages_target_candidate_ui_smoke.target_candidate_count_too_low")
        rendered = [str(item) for item in _list_value(payload.get("target_candidate_names_rendered"))]
        for required_name in ("luwei", "milk tea"):
            if required_name not in rendered:
                blockers.append(
                    f"product_pages_target_candidate_ui_smoke.target_candidate_missing:{required_name}"
                )
        if _int_value(payload.get("manager_provider_call_count")) != 0:
            blockers.append("product_pages_target_candidate_ui_smoke.manager_provider_called")
    if group_id == "product_pages_context_target_browser_closure":
        if _int_value(payload.get("target_candidate_count_rendered")) < 1:
            blockers.append(
                "product_pages_context_target_browser_closure.target_candidate_count_missing"
            )
        if not _list_value(payload.get("target_candidate_names_rendered")):
            blockers.append(
                "product_pages_context_target_browser_closure.target_candidate_names_missing"
            )
    if group_id == "current_shell_fixture_e2e":
        completed_steps = {str(item) for item in _list_value(payload.get("completed_current_shell_steps"))}
        for required_step in REQUIRED_CURRENT_SHELL_STEPS:
            if required_step not in completed_steps:
                blockers.append(f"current_shell_fixture_e2e.completed_step_missing:{required_step}")
    return blockers


def _artifact_statuses(inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "smoke_id": payload.get("smoke_id") or "not_available",
            "status": _status(payload),
            "browser_executed": payload.get("browser_executed", "not_applicable"),
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in inputs.items()
    }


def _strongest_consumed_pass_type(inputs: dict[str, dict[str, Any]]) -> str:
    ranking = {
        "static": 0,
        "contract": 1,
        "fixture": 2,
        "runtime_backed": 3,
        "browser_executed": 4,
    }
    strongest = "contract"
    for payload in inputs.values():
        pass_type = str(payload.get("pass_type") or "")
        if ranking.get(pass_type, -1) > ranking[strongest]:
            strongest = pass_type
    if any(inputs[group_id].get("browser_executed") is True for group_id in BROWSER_INPUTS):
        return "browser_executed"
    return strongest
