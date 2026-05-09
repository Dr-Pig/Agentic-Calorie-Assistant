from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_current_shell_claim_boundary import build_current_shell_appshell_claim_boundary_fields
from app.composition.current_shell_browser_activation_contract import (
    BROWSER_ARTIFACTS,
    EXPECTED_ARTIFACT_TYPES,
    EXPECTED_SMOKE_IDS,
    EXPECTED_STATUSES,
    FORBIDDEN_TRUTHY_FLAGS,
    REQUIRED_INPUTS,
    REQUIRED_PRODUCT_LOOP_STEPS,
    REQUIRED_SELF_USE_FLOW_SUMMARY_FLAGS,
    REQUIRED_TRUE_FLAGS,
    route_backed_macro_budget_truth_blockers,
)
from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
    LEGACY_BROWSER_ACTIVATION_ARTIFACT_TYPES,
    LEGACY_LOCAL_MVP_ARTIFACT_TYPES,
    LEGACY_LOCAL_MVP_GROUP_IDS,
    LEGACY_LOCAL_MVP_READY_STATUSES,
    matches_alias,
    set_legacy_alias_metadata,
)

def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


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
    if group_id == CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID:
        if not matches_alias(
            payload.get("status"),
            EXPECTED_STATUSES[group_id],
            *LEGACY_LOCAL_MVP_READY_STATUSES,
        ):
            blockers.append(f"{group_id}.unexpected_status:{_status(payload)}")
    elif _status(payload) != EXPECTED_STATUSES[group_id]:
        blockers.append(f"{group_id}.unexpected_status:{_status(payload)}")
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


def _forbidden_claim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
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
    if group_id == CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID:
        if payload.get("activation_gate_status") != "blocked_pending_human_and_browser_activation":
            blockers.append(
                f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID}.unexpected_activation_gate_status"
            )
    if group_id == "product_pages_browser_smoke":
        blockers.extend(route_backed_macro_budget_truth_blockers(group_id, payload))
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
        if _int_value(payload.get("manager_provider_call_count")) != 0:
            blockers.append("product_pages_seven_day_diary_smoke.manager_provider_called")
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
    if group_id == "product_pages_body_noplan_degraded_smoke":
        body_values = _object_dict(payload.get("body_values"))
        today_values = _object_dict(payload.get("today_values"))
        for field in ("daily_target", "tdee", "active_target", "remaining"):
            if str(body_values.get(field) or "") != "--":
                blockers.append(f"product_pages_body_noplan_degraded_smoke.body_{field}_not_hidden")
        for field in ("budget", "consumed", "remaining"):
            if str(today_values.get(field) or "") != "0":
                blockers.append(f"product_pages_body_noplan_degraded_smoke.today_{field}_not_zero")
    if group_id == "fixture_full_product_loop_e2e":
        completed_steps = {str(item) for item in _list_value(payload.get("completed_product_loop_steps"))}
        for required_step in REQUIRED_PRODUCT_LOOP_STEPS:
            if required_step not in completed_steps:
                blockers.append(f"fixture_full_product_loop_e2e.completed_step_missing:{required_step}")
    if group_id == "product_pages_self_use_flow_gate":
        summary = _object_dict(payload.get("summary"))
        for flag in REQUIRED_SELF_USE_FLOW_SUMMARY_FLAGS:
            if summary.get(flag) is not True:
                blocker_name = flag.removesuffix("_checked")
                blockers.append(f"product_pages_self_use_flow_gate.{blocker_name}_not_checked")
        if str(summary.get("strongest_consumed_pass_type") or "") != "browser_executed":
            blockers.append("product_pages_self_use_flow_gate.strongest_pass_type_not_browser_executed")
        if _int_value(summary.get("fixture_product_loop_steps_checked")) < len(REQUIRED_PRODUCT_LOOP_STEPS):
            blockers.append("product_pages_self_use_flow_gate.fixture_product_loop_step_count_too_low")
    return blockers


def _artifact_statuses(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "smoke_id": payload.get("smoke_id") or "not_available",
            "status": _status(payload),
            "browser_executed": payload.get("browser_executed", "not_applicable"),
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in payloads.items()
    }


def build_pl_ce_browser_activation_evidence_gate_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = {
        group_id: _object_dict(
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
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_identity_blockers(group_id, payload))
        blockers.extend(_forbidden_claim_blockers(group_id, payload))
        blockers.extend(_required_true_blockers(group_id, payload))
        blockers.extend(_group_specific_blockers(group_id, payload))

    all_browser_executed = all(inputs[group_id].get("browser_executed") is True for group_id in BROWSER_ARTIFACTS)
    self_use_flow_summary = _object_dict(inputs["product_pages_self_use_flow_gate"].get("summary"))
    self_use_flow_checked = (
        inputs["product_pages_self_use_flow_gate"].get("status")
        == EXPECTED_STATUSES["product_pages_self_use_flow_gate"]
        and inputs["product_pages_self_use_flow_gate"].get("all_required_browser_artifacts_executed") is True
        and all(self_use_flow_summary.get(flag) is True for flag in REQUIRED_SELF_USE_FLOW_SUMMARY_FLAGS)
        and self_use_flow_summary.get("strongest_consumed_pass_type") == "browser_executed"
    )
    status = "browser_activation_evidence_ready_for_human_review" if not blockers else "blocked"
    payload = {
            "artifact_schema_version": "1.0",
            "artifact_type": CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE,
            "status": status,
            "claim_scope": "current_shell_compatibility_browser_activation_evidence_for_human_review_only",
            **build_current_shell_appshell_claim_boundary_fields(),
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "required_inputs": list(REQUIRED_INPUTS),
            "browser_required_inputs": list(BROWSER_ARTIFACTS),
            "blockers": blockers,
            "included_artifact_statuses": _artifact_statuses(inputs),
            "browser_executed_required": True,
            "all_required_browser_artifacts_executed": all_browser_executed,
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "aggregate_only": True,
            "self_generated_evidence_used": False,
            "review_required_before_provider_call": True,
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
            "production_db_used": False,
            "manager_context_packet_schema_changed": False,
            "mutation_authority": False,
            "summary": {
                "browser_artifact_count": len(BROWSER_ARTIFACTS),
                "browser_executed_count": sum(
                    1
                    for group_id in BROWSER_ARTIFACTS
                    if inputs[group_id].get("browser_executed") is True
                ),
                "requires_three_distinct_pages": True,
                "requires_seven_day_today_diary": True,
                "requires_short_term_context_render": True,
                "requires_target_candidate_ui": True,
                "requires_body_noplan_degraded_browser": True,
                "requires_fixture_full_product_loop_e2e": True,
                "requires_product_pages_self_use_flow_gate": True,
                "requires_visual_qa": True,
                "requires_no_debug_trace_leak": True,
                "self_use_flow_gate_checked": self_use_flow_checked,
                "self_use_flow_gate_strongest_pass_type": self_use_flow_summary.get(
                    "strongest_consumed_pass_type"
                )
                or "not_available",
                "fixture_product_loop_step_count": len(
                    _list_value(inputs["fixture_full_product_loop_e2e"].get("completed_product_loop_steps"))
                ),
            },
        }
    set_legacy_alias_metadata(payload, legacy_artifact_types=LEGACY_BROWSER_ACTIVATION_ARTIFACT_TYPES)
    return _json_safe(payload)


__all__ = [
    "BROWSER_ARTIFACTS",
    "EXPECTED_ARTIFACT_TYPES",
    "EXPECTED_SMOKE_IDS",
    "EXPECTED_STATUSES",
    "REQUIRED_INPUTS",
    "build_pl_ce_browser_activation_evidence_gate_artifact",
]
