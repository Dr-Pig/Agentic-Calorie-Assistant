from __future__ import annotations

from typing import Any

from app.composition.current_shell_browser_activation_contract import (
    REQUIRED_CURRENT_SHELL_STEPS,
    REQUIRED_SELF_USE_FLOW_SUMMARY_FLAGS,
)


def object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def body_read_model_blockers(payload: dict[str, Any]) -> list[str]:
    body_values = object_dict(payload.get("body_plan_read_model_values"))
    if not body_values:
        return ["product_pages_browser_smoke.body_read_model_values_missing"]
    blockers: list[str] = []
    expected = {
        "daily_target": "1550 kcal",
        "tdee": "1819 kcal",
        "current_weight": "70 kg",
        "target_weight": "65 kg",
        "activity": "light",
        "goal": "Lose weight",
    }
    for field, expected_value in expected.items():
        if body_values.get(field) != expected_value:
            blockers.append(f"product_pages_browser_smoke.body_read_model_value_mismatch:{field}")
    local_date = payload.get("local_date") if isinstance(payload.get("local_date"), str) else "2026-05-05"
    if f"{local_date} | 70.4 kg" not in str(body_values.get("weight_history") or ""):
        blockers.append("product_pages_browser_smoke.body_read_model_value_mismatch:weight_history")
    return blockers


def target_candidate_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if int_value(payload.get("target_candidate_count_rendered")) < 2:
        blockers.append("product_pages_target_candidate_ui_smoke.target_candidate_count_too_low")
    rendered = [str(item) for item in list_value(payload.get("target_candidate_names_rendered"))]
    for required_name in ("luwei", "milk tea"):
        if required_name not in rendered:
            blockers.append(f"product_pages_target_candidate_ui_smoke.target_candidate_missing:{required_name}")
    if int_value(payload.get("manager_provider_call_count")) != 0:
        blockers.append("product_pages_target_candidate_ui_smoke.manager_provider_called")
    return blockers


def body_noplan_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    body_values = object_dict(payload.get("body_values"))
    today_values = object_dict(payload.get("today_values"))
    for field in ("daily_target", "tdee", "active_target", "remaining"):
        if str(body_values.get(field) or "") != "--":
            blockers.append(f"product_pages_body_noplan_degraded_smoke.body_{field}_not_hidden")
    for field in ("budget", "consumed", "remaining"):
        if str(today_values.get(field) or "") != "0":
            blockers.append(f"product_pages_body_noplan_degraded_smoke.today_{field}_not_zero")
    return blockers


def self_use_flow_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = object_dict(payload.get("summary"))
    for flag in REQUIRED_SELF_USE_FLOW_SUMMARY_FLAGS:
        if summary.get(flag) is not True:
            blocker_name = flag.removesuffix("_checked")
            blockers.append(f"product_pages_self_use_flow_gate.{blocker_name}_not_checked")
    if str(summary.get("strongest_consumed_pass_type") or "") != "browser_executed":
        blockers.append("product_pages_self_use_flow_gate.strongest_pass_type_not_browser_executed")
    if int_value(summary.get("current_shell_steps_checked")) < len(REQUIRED_CURRENT_SHELL_STEPS):
        blockers.append("product_pages_self_use_flow_gate.current_shell_fixture_step_count_too_low")
    return blockers
