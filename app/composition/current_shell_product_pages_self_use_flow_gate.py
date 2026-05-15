from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition import current_shell_body_observation_gate_contract as body_obs
from app.composition.accurate_intake_current_shell_claim_boundary import build_current_shell_appshell_claim_boundary_fields
from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
    LEGACY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPES,
    set_legacy_alias_metadata,
)
from app.composition.current_shell_product_pages_flow_checks import (
    _artifact_statuses,
    _forbidden_claim_blockers,
    _group_specific_blockers,
    _identity_blockers,
    _int_value,
    _list_value,
    _object_dict,
    _required_true_blockers,
    _strongest_consumed_pass_type,
)
from app.composition.current_shell_product_pages_flow_contract import (
    BROWSER_INPUTS,
    EXPECTED_STATUSES,
    REQUIRED_INPUTS,
)

def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def build_current_shell_product_pages_self_use_flow_gate_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = {
        group_id: _object_dict(input_artifacts.get(group_id))
        for group_id in REQUIRED_INPUTS
    }
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_identity_blockers(group_id, payload))
        blockers.extend(_required_true_blockers(group_id, payload))
        blockers.extend(_forbidden_claim_blockers(group_id, payload))
        blockers.extend(_group_specific_blockers(group_id, payload))

    all_browser_executed = all(inputs[group_id].get("browser_executed") is True for group_id in BROWSER_INPUTS)
    renderer_summary = _object_dict(inputs["product_pages_renderer_source_map"].get("summary"))
    closure_summary = _object_dict(inputs["product_pages_renderer_source_closure_gate"].get("summary"))
    completed_steps = _list_value(inputs["current_shell_fixture_e2e"].get("completed_current_shell_steps"))
    status = "product_pages_self_use_flow_ready_for_human_review" if not blockers else "blocked"
    payload = {
            "artifact_schema_version": "1.0",
            "artifact_type": CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
            "status": status,
            "claim_scope": "local_product_pages_self_use_flow_diagnostic_for_human_review_only",
            **build_current_shell_appshell_claim_boundary_fields(),
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "required_inputs": list(REQUIRED_INPUTS),
            "browser_required_inputs": list(BROWSER_INPUTS),
            "browser_executed_required": True,
            "blocked_browser_is_not_pass": True,
            "all_required_browser_artifacts_executed": all_browser_executed,
            "blockers": blockers,
            "included_artifact_statuses": _artifact_statuses(inputs),
            "summary": {
                "pages_verified": ["chat", "today", "body"],
                "three_distinct_pages_verified": inputs["product_pages_visual_qa"].get("three_distinct_pages_verified") is True,
                "renderer_source_map_page_count": _int_value(renderer_summary.get("page_count")),
                "renderer_source_map_selector_count": _int_value(renderer_summary.get("selector_count")),
                "renderer_source_map_endpoint_count": _int_value(renderer_summary.get("endpoint_count")),
                "renderer_source_closure_checked": (
                    inputs["product_pages_renderer_source_closure_gate"].get("route_table_checked") is True
                    and inputs["product_pages_renderer_source_closure_gate"].get("status")
                    == EXPECTED_STATUSES["product_pages_renderer_source_closure_gate"]
                ),
                "renderer_source_closure_endpoint_contract_count": _int_value(closure_summary.get("endpoint_method_contract_count")),
                "seven_day_diary_checked": inputs["product_pages_seven_day_diary_smoke"].get("seven_day_window_checked") is True,
                "body_noplan_degraded_checked": (
                    inputs["product_pages_body_noplan_degraded_smoke"].get("status")
                    == EXPECTED_STATUSES["product_pages_body_noplan_degraded_smoke"]
                    and inputs["product_pages_body_noplan_degraded_smoke"].get("browser_executed") is True
                ),
                "body_observation_same_truth_checked": body_obs.body_observation_same_truth_checked(
                    inputs[body_obs.BODY_OBSERVATION_SAME_TRUTH_GATE_ID]
                ),
                "short_term_context_checked": inputs["product_pages_short_term_context_smoke"].get("chat_history_context_fields_reloaded") is True,
                "target_candidate_ui_checked": inputs["product_pages_target_candidate_ui_smoke"].get("target_candidate_surface_checked") is True,
                "context_target_browser_closure_checked": (
                    inputs["product_pages_context_target_browser_closure"].get("context_engineering_present")
                    is True
                    and inputs["product_pages_context_target_browser_closure"].get("status")
                    == EXPECTED_STATUSES["product_pages_context_target_browser_closure"]
                ),
                "today_macro_runtime_mirror_checked": (
                    inputs["today_macro_runtime_mirror_gate"].get("status")
                    == EXPECTED_STATUSES["today_macro_runtime_mirror_gate"]
                    and inputs["today_macro_runtime_mirror_gate"].get("macro_visible_case_checked") is True
                    and inputs["today_macro_runtime_mirror_gate"].get("macro_guarded_case_checked") is True
                ),
                "route_backed_macro_budget_truth_checked": inputs["product_pages_browser_smoke"].get("route_backed_macro_browser_checked") is True,
                "fooddb_triad_same_truth_checked": inputs["product_pages_browser_smoke"].get("fooddb_triad_same_truth_browser_checked") is True,
                "current_shell_steps_checked": len(completed_steps),
                "strongest_consumed_pass_type": _strongest_consumed_pass_type(inputs),
            },
            "human_review_required": True,
            "review_required_before_provider_call": True,
            "frontend_render_only": inputs["ui_same_truth_contract"].get("frontend_render_only") is True,
            "frontend_semantic_owner": False,
            "fixture_evidence_used": True,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "production_db_used": False,
            "manager_context_packet_schema_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
        }
    set_legacy_alias_metadata(payload, legacy_artifact_types=LEGACY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPES)
    return _json_safe(payload)


__all__ = ["REQUIRED_INPUTS", "build_current_shell_product_pages_self_use_flow_gate_artifact"]
