from __future__ import annotations

from typing import Any

from app.composition.current_shell_ui_context_alignment_constants import (
    EXPECTED_ARTIFACT_TYPES,
    EXPECTED_SMOKE_IDS,
    EXPECTED_STATUSES,
    FORBIDDEN_TRUTHY_FLAGS,
    REQUIRED_INPUTS,
    REQUIRED_TRUE_FLAGS,
)


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _expected_weight_history_value(payload: dict[str, Any]) -> str:
    local_date = payload.get("local_date")
    if isinstance(local_date, str) and local_date:
        return f"{local_date} | 70.4 kg"
    return "2026-05-05 | 70.4 kg"


def _allowed_statuses(expected_status: Any) -> set[str]:
    if isinstance(expected_status, str):
        return {expected_status}
    if isinstance(expected_status, set | frozenset | tuple | list):
        return {str(status) for status in expected_status}
    return {str(expected_status)}


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {
            "",
            "0",
            "false",
            "no",
            "none",
            "null",
            "not_available",
            "not_checked",
        }
    return True


def _identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _status(payload) not in _allowed_statuses(EXPECTED_STATUSES[group_id]):
        blockers.append(f"{group_id}.unexpected_status:{_status(payload)}")
    expected_type = EXPECTED_ARTIFACT_TYPES.get(group_id)
    if expected_type and payload.get("artifact_type") != expected_type:
        blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    expected_smoke_id = EXPECTED_SMOKE_IDS.get(group_id)
    if expected_smoke_id and payload.get("smoke_id") != expected_smoke_id:
        blockers.append(f"{group_id}.unexpected_smoke_id:{payload.get('smoke_id')}")
    if payload.get("blockers") not in (None, []):
        blockers.append(f"{group_id}.upstream_blockers_present")
    return blockers


def _claim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{group_id}.{flag}"
        for flag in FORBIDDEN_TRUTHY_FLAGS
        if _claim_is_true(payload.get(flag))
    ]


def _required_true_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for flag in REQUIRED_TRUE_FLAGS.get(group_id, ()):
        if payload.get(flag) is not True:
            suffix = "browser_not_executed" if flag == "browser_executed" else f"{flag}_not_true"
            blockers.append(f"{group_id}.{suffix}")
    return blockers


def _group_specific_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if group_id == "product_pages_browser_smoke":
        body_values = _object_dict(payload.get("body_plan_read_model_values"))
        if not body_values:
            blockers.append("product_pages_browser_smoke.body_read_model_values_missing")
        expected_body_values = {
            "daily_target": "1550 kcal",
            "tdee": "1819 kcal",
            "current_weight": "70 kg",
            "target_weight": "65 kg",
            "activity": "light",
            "goal": "Lose weight",
        }
        for field, expected_value in expected_body_values.items():
            if body_values and body_values.get(field) != expected_value:
                blockers.append(f"product_pages_browser_smoke.body_read_model_value_mismatch:{field}")
        if body_values and _expected_weight_history_value(payload) not in str(
            body_values.get("weight_history") or ""
        ):
            blockers.append("product_pages_browser_smoke.body_read_model_value_mismatch:weight_history")
    if group_id == "product_pages_seven_day_diary_smoke":
        if _int_value(payload.get("day_count_checked")) < 7:
            blockers.append("product_pages_seven_day_diary_smoke.seven_day_window_incomplete")
    return blockers


def _artifact_statuses(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for group_id, payload in payloads.items():
        statuses[group_id] = {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "smoke_id": payload.get("smoke_id") or "not_available",
            "status": _status(payload),
            "browser_executed": payload.get("browser_executed", "not_applicable"),
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
    return statuses
