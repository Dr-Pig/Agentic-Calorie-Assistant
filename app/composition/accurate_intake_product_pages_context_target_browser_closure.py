from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


READY_STATUS = "context_target_browser_closure_ready_for_self_use_flow_gate"
REQUIRED_MANAGER_GATES = (
    "rt4_context_packet_acceptance",
    "rt7b_blocking_clarify_pending_followup_boundary",
    "rt7d_optional_refinement_attach_boundary",
    "rt14_limited_live_ladder",
)
REQUIRED_SHORT_TERM_TRUE_FIELDS = (
    "browser_executed",
    "browser_reload_checked",
    "pending_followup_created",
    "pending_followup_reloaded",
    "context_policy_version_present",
    "loaded_context_summary_present",
    "omitted_context_summary_present",
    "pending_pins_present_after_followup",
    "chat_history_context_fields_reloaded",
    "chat_context_status_ui_rendered",
    "assistant_followup_bubble_rendered",
    "assistant_commit_bubble_rendered",
    "today_same_day_meal_rendered",
    "today_summary_rendered",
    "product_pages_no_debug_trace",
)
REQUIRED_TARGET_CANDIDATE_TRUE_FIELDS = (
    "browser_executed",
    "browser_reload_checked",
    "chat_history_reloaded",
    "target_candidate_surface_checked",
    "target_candidate_list_read_only",
    "context_strip_read_only",
    "product_pages_no_debug_trace",
)
SHORT_TERM_TRUE_FIELD_BLOCKERS = {
    "browser_executed": "browser_not_executed",
    "browser_reload_checked": "browser_reload_not_checked",
    "pending_followup_created": "pending_followup_not_created",
    "pending_followup_reloaded": "pending_followup_not_reloaded",
    "context_policy_version_present": "context_policy_version_missing",
    "loaded_context_summary_present": "loaded_context_summary_missing",
    "omitted_context_summary_present": "omitted_context_summary_missing",
    "pending_pins_present_after_followup": "pending_pins_not_present_after_followup",
    "chat_history_context_fields_reloaded": "chat_history_context_fields_not_reloaded",
    "chat_context_status_ui_rendered": "chat_context_status_ui_not_rendered",
    "assistant_followup_bubble_rendered": "assistant_followup_bubble_not_rendered",
    "assistant_commit_bubble_rendered": "assistant_commit_bubble_not_rendered",
    "today_same_day_meal_rendered": "today_same_day_meal_not_rendered",
    "today_summary_rendered": "today_summary_not_rendered",
    "product_pages_no_debug_trace": "product_pages_debug_trace_leaked",
}
TARGET_CANDIDATE_TRUE_FIELD_BLOCKERS = {
    "browser_executed": "browser_not_executed",
    "browser_reload_checked": "browser_reload_not_checked",
    "chat_history_reloaded": "chat_history_not_reloaded",
    "target_candidate_surface_checked": "target_candidate_surface_not_checked",
    "target_candidate_list_read_only": "target_candidate_list_not_read_only",
    "context_strip_read_only": "context_strip_not_read_only",
    "product_pages_no_debug_trace": "product_pages_debug_trace_leaked",
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _manager_gate_statuses(manager_gate_ledger_artifact: dict[str, Any] | None) -> dict[str, str | None]:
    gates = (manager_gate_ledger_artifact or {}).get("gates") or []
    if not isinstance(gates, list):
        return {gate_id: None for gate_id in REQUIRED_MANAGER_GATES}
    by_id = {
        str(gate.get("gate_id")): str(gate.get("status"))
        for gate in gates
        if isinstance(gate, dict) and gate.get("gate_id") is not None
    }
    return {gate_id: by_id.get(gate_id) for gate_id in REQUIRED_MANAGER_GATES}


def _short_term_context_blockers(report: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if report.get("smoke_id") != "accurate_intake_product_pages_short_term_context_smoke_v1":
        blockers.append(f"short_term_context_report.unexpected_smoke_id:{report.get('smoke_id')}")
    if report.get("status") != "pass":
        blockers.append(f"short_term_context_report.status_not_pass:{report.get('status')}")
    for field in REQUIRED_SHORT_TERM_TRUE_FIELDS:
        if report.get(field) is not True:
            blockers.append(f"short_term_context_report.{SHORT_TERM_TRUE_FIELD_BLOCKERS[field]}")
    provider_calls = [item for item in _list(report.get("fake_provider_calls")) if isinstance(item, dict)]
    if not any(
        call.get("context_policy_version_present") is True
        and call.get("loaded_context_summary_present") is True
        and call.get("omitted_context_summary_present") is True
        for call in provider_calls
    ):
        blockers.append("short_term_context_report.fake_provider_context_input_not_proven")
    if not any(
        call.get("pending_followup_pin_present") is True or call.get("pending_draft_pin_present") is True
        for call in provider_calls
    ):
        blockers.append("short_term_context_report.fake_provider_pending_pin_input_not_proven")
    if any(call.get("raw_user_input_used_for_fixture_selection") is True for call in provider_calls):
        blockers.append("short_term_context_report.fake_provider_used_raw_user_input")
    return blockers


def _target_candidate_blockers(report: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if report.get("smoke_id") != "accurate_intake_product_pages_target_candidate_ui_smoke_v1":
        blockers.append(f"target_candidate_report.unexpected_smoke_id:{report.get('smoke_id')}")
    if report.get("status") != "pass":
        blockers.append(f"target_candidate_report.status_not_pass:{report.get('status')}")
    for field in REQUIRED_TARGET_CANDIDATE_TRUE_FIELDS:
        if report.get(field) is not True:
            blockers.append(f"target_candidate_report.{TARGET_CANDIDATE_TRUE_FIELD_BLOCKERS[field]}")
    if int(report.get("target_candidate_count_rendered") or 0) < 1:
        blockers.append("target_candidate_report.target_candidate_count_missing")
    if not _list(report.get("target_candidate_names_rendered")):
        blockers.append("target_candidate_report.target_candidate_names_missing")
    if int(report.get("manager_provider_call_count") or 0) != 0:
        blockers.append("target_candidate_report.manager_provider_called")
    return blockers


def build_context_target_browser_closure_artifact(
    *,
    manager_gate_ledger_artifact: dict[str, Any] | None,
    short_term_context_report: dict[str, Any],
    target_candidate_report: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    upstream_gate_statuses = _manager_gate_statuses(manager_gate_ledger_artifact)
    for gate_id, status in upstream_gate_statuses.items():
        if status != "green":
            blockers.append(f"manager_runtime_gate.{gate_id}_not_green:{status}")
    blockers.extend(_short_term_context_blockers(short_term_context_report))
    blockers.extend(_target_candidate_blockers(target_candidate_report))

    status = READY_STATUS if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_product_pages_context_target_browser_closure",
            "status": status,
            "pass_type": "browser_executed",
            "browser_executed": (
                short_term_context_report.get("browser_executed") is True
                and target_candidate_report.get("browser_executed") is True
            ),
            "claim_scope": "appshell_context_target_browser_closure_for_self_use_flow_gate_input",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "blockers": blockers,
            "upstream_manager_gates": upstream_gate_statuses,
            "browser_reports_checked": [
                str(short_term_context_report.get("smoke_id")),
                str(target_candidate_report.get("smoke_id")),
            ],
            "context_engineering_present": not any(
                blocker.startswith("short_term_context_report.") for blocker in blockers
            ),
            "session_state_injected": bool(short_term_context_report.get("chat_history_context_fields_reloaded")),
            "pending_meal_or_correction_context_present": bool(
                short_term_context_report.get("pending_pins_present_after_followup")
            ),
            "target_candidate_list_read_only": bool(
                target_candidate_report.get("target_candidate_list_read_only")
            ),
            "context_strip_read_only": bool(target_candidate_report.get("context_strip_read_only")),
            "target_candidate_count_rendered": target_candidate_report.get("target_candidate_count_rendered"),
            "target_candidate_names_rendered": _list(target_candidate_report.get("target_candidate_names_rendered")),
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "ui_truth_owner": False,
            "frontend_semantic_owner": False,
            "frontend_selects_target": False,
            "frontend_infers_context_snapshot": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "live_provider_called": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        }
    )


__all__ = ["build_context_target_browser_closure_artifact"]
