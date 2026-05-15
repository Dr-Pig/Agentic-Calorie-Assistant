from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition import current_shell_body_observation_gate_contract as body_obs
from app.composition.accurate_intake_current_shell_claim_boundary import build_current_shell_appshell_claim_boundary_fields
from app.composition.current_shell_browser_activation_contract import (
    BROWSER_ARTIFACTS,
    EXPECTED_ARTIFACT_TYPES,
    EXPECTED_SMOKE_IDS,
    EXPECTED_STATUSES,
    FORBIDDEN_TRUTHY_FLAGS,
    REQUIRED_INPUTS,
    REQUIRED_SELF_USE_FLOW_SUMMARY_FLAGS,
    REQUIRED_TRUE_FLAGS,
)
from app.composition.current_shell_browser_activation_evidence_checks import (
    artifact_statuses,
    input_blockers,
    input_payloads,
    list_value,
    object_dict,
)
from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE,
    LEGACY_BROWSER_ACTIVATION_ARTIFACT_TYPES,
    set_legacy_alias_metadata,
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def build_current_shell_browser_activation_evidence_gate_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = input_payloads(input_artifacts)
    blockers = input_blockers(inputs)

    all_browser_executed = all(inputs[group_id].get("browser_executed") is True for group_id in BROWSER_ARTIFACTS)
    self_use_flow_summary = object_dict(inputs["product_pages_self_use_flow_gate"].get("summary"))
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
            "included_artifact_statuses": artifact_statuses(inputs),
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
                "requires_body_observation_same_truth_gate": True,
                "requires_current_shell_fixture_e2e": True,
                "requires_product_pages_self_use_flow_gate": True,
                "requires_visual_qa": True,
                "requires_no_debug_trace_leak": True,
                "self_use_flow_gate_checked": self_use_flow_checked,
                "self_use_flow_gate_strongest_pass_type": self_use_flow_summary.get(
                    "strongest_consumed_pass_type"
                )
                or "not_available",
                "body_observation_same_truth_checked": (
                    body_obs.body_observation_same_truth_checked(
                        inputs[body_obs.BODY_OBSERVATION_SAME_TRUTH_GATE_ID]
                    )
                    and self_use_flow_summary.get("body_observation_same_truth_checked") is True
                ),
                "current_shell_fixture_step_count": len(
                    list_value(inputs["current_shell_fixture_e2e"].get("completed_current_shell_steps"))
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
    "build_current_shell_browser_activation_evidence_gate_artifact",
]
