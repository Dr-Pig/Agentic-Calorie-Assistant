from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from scripts.accurate_intake_pre_live_axis_summary import build_capability_axis_summary
from scripts.accurate_intake_non_fooddb_manager_tool_contract_gate_checks import (
    pre_live_contract_blockers,
)

REQUIRED_PRE_LIVE_EVIDENCE = (
    "phase_c_gate",
    "accurate_intake_mvp_gate",
    "browser_shell_smoke",
    "chat_history_reload_gate",
    "free_text_manual_target_gate",
    "dogfood_review_queue",
    "local_dogfood_data_hygiene",
    "local_operator_data_hygiene_bundle",
    "pl_ce_local_review_decision_pack",
    "product_pages_self_use_flow_gate",
    "ui_context_alignment_pack",
    "browser_activation_evidence_gate",
    "manager_tool_surface_inventory",
    "non_fooddb_manager_tool_contract",
    "manager_tool_choice_regression_wall",
    "context_conditioned_intent_wall",
    "non_fooddb_read_only_tool_loop_fake_smoke",
    "non_fooddb_mutation_tool_guard_smoke",
    "manager_intent_readiness_review_pack",
    "context_live_diagnostic_case_matrix",
    "context_live_diagnostic_anti_overfit_guard",
    "context_live_diagnostic_holdout_plan",
    "context_live_provider_input_preflight",
    "context_live_response_contract_dry_run",
    "context_live_diagnostic_gate",
)

_EXPECTED_STATUS_BY_GROUP = {
    "phase_c_gate": "pass",
    "accurate_intake_mvp_gate": "pass",
    "browser_shell_smoke": "pass",
    "chat_history_reload_gate": "pass",
    "free_text_manual_target_gate": "pass",
    "dogfood_review_queue": "generated",
    "local_dogfood_data_hygiene": "pass",
    "local_operator_data_hygiene_bundle": "local_operator_data_hygiene_ready",
    "pl_ce_local_review_decision_pack": "ready_for_human_pl_ce_review",
    "product_pages_self_use_flow_gate": "product_pages_self_use_flow_ready_for_human_review",
    "ui_context_alignment_pack": "ui_context_alignment_ready_for_human_review",
    "browser_activation_evidence_gate": "browser_activation_evidence_ready_for_human_review",
    "manager_tool_surface_inventory": "manager_tool_surface_inventory_ready_for_human_review",
    "non_fooddb_manager_tool_contract": "non_fooddb_manager_tool_contract_ready_for_human_review",
    "manager_tool_choice_regression_wall": "manager_tool_choice_regression_wall_pass",
    "context_conditioned_intent_wall": "pass",
    "non_fooddb_read_only_tool_loop_fake_smoke": "non_fooddb_read_only_tool_loop_fake_smoke_pass",
    "non_fooddb_mutation_tool_guard_smoke": "non_fooddb_mutation_tool_guard_smoke_pass",
    "manager_intent_readiness_review_pack": "manager_intent_readiness_ready_for_human_review",
    "context_live_diagnostic_case_matrix": "pass",
    "context_live_diagnostic_anti_overfit_guard": "pass",
    "context_live_diagnostic_holdout_plan": "pass",
    "context_live_provider_input_preflight": "pass",
    "context_live_response_contract_dry_run": "pass",
    "context_live_diagnostic_gate": "context_live_diagnostic_gate_ready_without_live_canary",
}


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("summary") if isinstance(payload.get("summary"), dict) else {}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _evidence_missing(group_id: str, payload: dict[str, Any]) -> bool:
    if str(payload.get("status") or "") != _EXPECTED_STATUS_BY_GROUP[group_id]:
        return True
    if group_id == "browser_shell_smoke" and payload.get("browser_executed") is not True:
        return True
    if group_id == "context_live_diagnostic_case_matrix" and payload.get("plan_only") is not True:
        return True
    if group_id == "context_live_diagnostic_anti_overfit_guard" and payload.get("plan_only") is not True:
        return True
    if group_id == "context_live_diagnostic_holdout_plan" and payload.get("plan_only") is not True:
        return True
    if group_id == "context_live_provider_input_preflight" and payload.get("plan_only") is not True:
        return True
    if group_id == "context_live_response_contract_dry_run" and payload.get("plan_only") is not True:
        return True
    if (
        group_id == "context_live_diagnostic_gate"
        and payload.get("status") != "context_live_diagnostic_gate_ready_without_live_canary"
    ):
        return True
    return False


def _evidence_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for flag in (
        "shared_contract_changed",
        "manager_context_packet_schema_changed",
        "manager_context_packet_changed",
        "nutrition_evidence_store_port_changed",
        "food_evidence_record_schema_changed",
        "packet_ready_anchor_schema_changed",
        "packetizer_format_changed",
        "packetizer_contract_changed",
        "basket_semantics_changed",
        "estimate_output_format_changed",
        "food_evidence_promotion_policy_changed",
        "runtime_truth_changed",
        "mutation_changed",
        "production_db_touched",
        "production_db_ready_claimed",
        "runtime_web_activation_approved",
        "live_canary_approved",
        "kimi_active_runtime_default_allowed",
        "kimi_activated",
        "grokfast_activated",
        "web_ready",
        "product_ready",
        "production_selected",
        "rollout_approved",
        "live_manager_required",
        "websearch_evidence_used",
        "web_tavily",
        "fooddb_evidence_used",
        "fooddb_schema_changed",
        "writes_performed",
        "import_allowed",
        "production_db_used",
        "fooddb_truth_updated",
        "live_llm_invoked",
        "web_tavily_used",
        "web_tavily_invoked",
        "private_self_use_approved",
        "product_readiness_claimed",
        "ready_for_live_diagnostic_decision",
        "ready_for_fdb_integration",
        "real_fooddb_pass_claimed",
        "live_provider_invoked",
        "live_provider_approved",
        "fooddb_used",
        "plan_only_bypassed",
    ):
        if payload.get(flag) is True:
            blockers.append(f"{group_id}_{flag}")
    if group_id == "context_live_diagnostic_case_matrix":
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        if int(summary.get("case_count") or 0) < 10:
            blockers.append("context_live_diagnostic_case_matrix_case_count_too_low")
        if int(summary.get("compound_cases") or 0) < 1:
            blockers.append("context_live_diagnostic_case_matrix_compound_case_missing")
    if group_id == "product_pages_self_use_flow_gate":
        summary = _summary(payload)
        for flag, blocker in (
            ("three_distinct_pages_verified", "product_pages_self_use_flow_gate_three_distinct_pages_not_verified"),
            ("seven_day_diary_checked", "product_pages_self_use_flow_gate_seven_day_diary_not_checked"),
            ("short_term_context_checked", "product_pages_self_use_flow_gate_short_term_context_not_checked"),
            ("target_candidate_ui_checked", "product_pages_self_use_flow_gate_target_candidate_ui_not_checked"),
        ):
            if summary.get(flag) is not True:
                blockers.append(blocker)
    if group_id == "ui_context_alignment_pack":
        summary = _summary(payload)
        for flag, blocker in (
            ("chat_context_reload_checked", "ui_context_alignment_pack_chat_context_reload_not_checked"),
            ("seven_day_diary_checked", "ui_context_alignment_pack_seven_day_diary_not_checked"),
            ("body_read_model_checked", "ui_context_alignment_pack_body_read_model_not_checked"),
        ):
            if summary.get(flag) is not True:
                blockers.append(blocker)
    if group_id == "browser_activation_evidence_gate":
        if payload.get("all_required_browser_artifacts_executed") is not True:
            blockers.append("browser_activation_evidence_gate_browser_artifacts_not_all_executed")
        if payload.get("browser_executed_required") is not True:
            blockers.append("browser_activation_evidence_gate_browser_execution_not_required")
    if group_id == "manager_tool_surface_inventory":
        summary = _summary(payload)
        direct_lane_ids = payload.get("required_direct_lane_ids")
        manager_tools = payload.get("required_manager_tools")
        if not isinstance(direct_lane_ids, list) or len(direct_lane_ids) < 7:
            blockers.append("manager_tool_surface_inventory_required_direct_lane_count_too_low")
        if not isinstance(manager_tools, list) or len(manager_tools) < 10:
            blockers.append("manager_tool_surface_inventory_required_manager_tool_count_too_low")
        if int(summary.get("direct_lane_count") or 0) < 7:
            blockers.append("manager_tool_surface_inventory_direct_lane_count_too_low")
        if int(summary.get("target_tool_count") or 0) < 10:
            blockers.append("manager_tool_surface_inventory_target_tool_count_too_low")
    if group_id == "non_fooddb_manager_tool_contract":
        blockers.extend(pre_live_contract_blockers(payload))
    if group_id == "manager_tool_choice_regression_wall":
        summary = _summary(payload)
        if payload.get("semantic_owner") != "fixture_manager_structured_decision":
            blockers.append("manager_tool_choice_regression_wall_semantic_owner_not_fixture_manager")
        if int(summary.get("case_count") or 0) < 11:
            blockers.append("manager_tool_choice_regression_wall_case_count_too_low")
    if group_id == "context_conditioned_intent_wall":
        summary = _summary(payload)
        if payload.get("manager_fixture_semantic_source_used") is not True:
            blockers.append("context_conditioned_intent_wall_fixture_semantic_source_missing")
        if int(summary.get("scenario_count") or 0) < 11:
            blockers.append("context_conditioned_intent_wall_scenario_count_too_low")
    if group_id == "non_fooddb_read_only_tool_loop_fake_smoke":
        summary = _summary(payload)
        if int(summary.get("case_count") or 0) < 6:
            blockers.append("non_fooddb_read_only_tool_loop_fake_smoke_case_count_too_low")
    if group_id == "non_fooddb_mutation_tool_guard_smoke":
        summary = _summary(payload)
        if int(summary.get("case_count") or 0) < 10:
            blockers.append("non_fooddb_mutation_tool_guard_smoke_case_count_too_low")
    if group_id == "context_live_diagnostic_anti_overfit_guard":
        summary = _summary(payload)
        if payload.get("plan_only") is not True:
            blockers.append("context_live_diagnostic_anti_overfit_guard_plan_only_not_true")
        if summary.get("fixed_case_matrix_used") is not True:
            blockers.append("context_live_diagnostic_anti_overfit_guard_fixed_case_matrix_missing")
        if int(summary.get("case_count") or 0) < 10:
            blockers.append("context_live_diagnostic_anti_overfit_guard_case_count_too_low")
        if int(summary.get("compound_cases") or 0) < 1:
            blockers.append("context_live_diagnostic_anti_overfit_guard_compound_case_missing")
        if int(summary.get("ambiguity_cases") or 0) < 1:
            blockers.append("context_live_diagnostic_anti_overfit_guard_ambiguity_case_missing")
    if group_id == "context_live_diagnostic_holdout_plan":
        summary = _summary(payload)
        if payload.get("plan_only") is not True:
            blockers.append("context_live_diagnostic_holdout_plan_plan_only_not_true")
        if payload.get("fixed_case_matrix_used") is not True:
            blockers.append("context_live_diagnostic_holdout_plan_fixed_case_matrix_missing")
        if payload.get("holdout_variants_withheld_from_default_live_prompt") is not True:
            blockers.append("context_live_diagnostic_holdout_plan_holdouts_not_withheld")
        if payload.get("ad_hoc_live_case_selection_allowed") is not False:
            blockers.append("context_live_diagnostic_holdout_plan_ad_hoc_case_selection_allowed")
        if payload.get("provider_optimized_case_selection_allowed") is not False:
            blockers.append("context_live_diagnostic_holdout_plan_provider_optimized_selection_allowed")
        if int(summary.get("case_count") or 0) < 10:
            blockers.append("context_live_diagnostic_holdout_plan_case_count_too_low")
        if int(summary.get("withheld_holdout_variant_count") or 0) < 20:
            blockers.append("context_live_diagnostic_holdout_plan_withheld_holdout_count_too_low")
        if int(summary.get("cases_with_holdouts") or 0) < 10:
            blockers.append("context_live_diagnostic_holdout_plan_cases_with_holdouts_too_low")
        if int(summary.get("compound_cases") or 0) < 1:
            blockers.append("context_live_diagnostic_holdout_plan_compound_case_missing")
        if int(summary.get("ambiguity_cases") or 0) < 1:
            blockers.append("context_live_diagnostic_holdout_plan_ambiguity_case_missing")
    if group_id == "context_live_provider_input_preflight":
        summary = _summary(payload)
        if payload.get("plan_only") is not True:
            blockers.append("context_live_provider_input_preflight_plan_only_not_true")
        if payload.get("fixture_only") is not True:
            blockers.append("context_live_provider_input_preflight_fixture_only_not_true")
        if payload.get("provider_call_ready") is not False:
            blockers.append("context_live_provider_input_preflight_provider_call_ready")
        if payload.get("human_approval_required_before_live_provider") is not True:
            blockers.append(
                "context_live_provider_input_preflight_human_approval_before_live_missing"
            )
        if payload.get("fixed_case_matrix_used") is not True:
            blockers.append("context_live_provider_input_preflight_fixed_case_matrix_missing")
        if payload.get("response_schema_strict") is not True:
            blockers.append("context_live_provider_input_preflight_response_schema_not_strict")
        if payload.get("deterministic_selected_intent") is not False:
            blockers.append("context_live_provider_input_preflight_deterministic_selected_intent")
        if payload.get("raw_text_intent_router_used") is not False:
            blockers.append("context_live_provider_input_preflight_raw_text_intent_router_used")
        if int(summary.get("case_count") or 0) < 10:
            blockers.append("context_live_provider_input_preflight_case_count_too_low")
        if int(summary.get("blocked_input_count") or 0) != 0:
            blockers.append("context_live_provider_input_preflight_blocked_input_count_nonzero")
        if int(summary.get("strict_schema_input_count") or 0) < 10:
            blockers.append("context_live_provider_input_preflight_strict_schema_count_too_low")
        if int(summary.get("target_candidate_inputs") or 0) < 1:
            blockers.append("context_live_provider_input_preflight_target_candidate_inputs_missing")
        if int(summary.get("pending_pin_inputs") or 0) < 1:
            blockers.append("context_live_provider_input_preflight_pending_pin_inputs_missing")
    if group_id == "context_live_response_contract_dry_run":
        summary = _summary(payload)
        if payload.get("plan_only") is not True:
            blockers.append("context_live_response_contract_dry_run_plan_only_not_true")
        if payload.get("fixture_only") is not True:
            blockers.append("context_live_response_contract_dry_run_fixture_only_not_true")
        if payload.get("provider_call_ready") is not False:
            blockers.append("context_live_response_contract_dry_run_provider_call_ready")
        if payload.get("human_approval_required_before_live_provider") is not True:
            blockers.append(
                "context_live_response_contract_dry_run_human_approval_before_live_missing"
            )
        if payload.get("response_schema_strict") is not True:
            blockers.append("context_live_response_contract_dry_run_response_schema_not_strict")
        if payload.get("deterministic_selected_intent") is not False:
            blockers.append("context_live_response_contract_dry_run_deterministic_selected_intent")
        if payload.get("raw_text_intent_router_used") is not False:
            blockers.append("context_live_response_contract_dry_run_raw_text_intent_router_used")
        if int(summary.get("case_count") or 0) < 10:
            blockers.append("context_live_response_contract_dry_run_case_count_too_low")
        if int(summary.get("blocked_response_count") or 0) != 0:
            blockers.append("context_live_response_contract_dry_run_blocked_response_count_nonzero")
        if int(summary.get("validated_response_count") or 0) < 10:
            blockers.append("context_live_response_contract_dry_run_validated_response_count_too_low")
        if int(summary.get("target_candidate_response_count") or 0) < 1:
            blockers.append("context_live_response_contract_dry_run_target_candidate_response_missing")
        if int(summary.get("ambiguity_preserved_response_count") or 0) < 1:
            blockers.append("context_live_response_contract_dry_run_ambiguity_response_missing")
        if int(summary.get("mutation_request_count") or 0) != 0:
            blockers.append("context_live_response_contract_dry_run_mutation_request_count_nonzero")
    if group_id == "context_live_diagnostic_gate":
        summary = _summary(payload)
        if payload.get("live_provider_allowed") is not False:
            blockers.append("context_live_diagnostic_gate_live_provider_allowed")
        if payload.get("live_provider_required") is not False:
            blockers.append("context_live_diagnostic_gate_live_provider_required")
        if payload.get("fixed_case_matrix_used") is not True:
            blockers.append("context_live_diagnostic_gate_fixed_case_matrix_missing")
        if payload.get("ad_hoc_live_case_selection_allowed") is not False:
            blockers.append("context_live_diagnostic_gate_ad_hoc_live_case_selection_allowed")
        if payload.get("anti_overfit_guard_required") is not True:
            blockers.append("context_live_diagnostic_gate_anti_overfit_guard_missing")
        if payload.get("holdout_plan_required") is not True:
            blockers.append("context_live_diagnostic_gate_holdout_plan_missing")
        if payload.get("response_contract_dry_run_required") is not True:
            blockers.append("context_live_diagnostic_gate_response_contract_dry_run_missing")
        if payload.get("diagnostic_only") is not True:
            blockers.append("context_live_diagnostic_gate_diagnostic_only_missing")
        if int(summary.get("fixed_case_count") or 0) < 10:
            blockers.append("context_live_diagnostic_gate_fixed_case_count_too_low")
        if int(summary.get("dry_run_validated_response_count") or 0) < 10:
            blockers.append("context_live_diagnostic_gate_dry_run_validated_count_too_low")
        if int(summary.get("live_blocked_response_count") or 0) != 0:
            blockers.append("context_live_diagnostic_gate_live_blocked_response_count_nonzero")
    if group_id == "manager_intent_readiness_review_pack":
        summary = _summary(payload)
        if payload.get("review_required_before_provider_call") is not True:
            blockers.append(
                "manager_intent_readiness_review_pack_review_required_before_provider_call_missing"
            )
        if payload.get("semantic_owner") != "fixture_manager_structured_decision":
            blockers.append("manager_intent_readiness_review_pack_semantic_owner_not_fixture_manager")
        if int(summary.get("intent_wall_scenarios") or 0) < 11:
            blockers.append("manager_intent_readiness_review_pack_intent_wall_scenarios_too_low")
        if int(summary.get("contextual_interactions") or 0) < 11:
            blockers.append("manager_intent_readiness_review_pack_contextual_interactions_too_low")
        if int(summary.get("fake_provider_handoff_scenarios") or 0) < 6:
            blockers.append("manager_intent_readiness_review_pack_fake_provider_handoffs_too_low")
        if int(summary.get("responder_allowed_fact_scenarios") or 0) < 5:
            blockers.append("manager_intent_readiness_review_pack_responder_scenarios_too_low")
        if int(summary.get("context_covered_capabilities") or 0) < 9:
            blockers.append("manager_intent_readiness_review_pack_context_capabilities_too_low")
        if int(summary.get("context_blocked_capabilities") or 0) > 0:
            blockers.append("manager_intent_readiness_review_pack_context_blocked_capabilities_present")
        if int(summary.get("context_known_runtime_gaps") or 0) > 0:
            blockers.append("manager_intent_readiness_review_pack_context_known_runtime_gaps_present")
        if summary.get("session_pending_followup_carryover_checked") is not True:
            blockers.append("manager_intent_readiness_review_pack_pending_followup_not_checked")
        if summary.get("session_target_candidate_ui_checked") is not True:
            blockers.append("manager_intent_readiness_review_pack_target_candidate_ui_not_checked")
        if summary.get("session_long_context_checked") is not True:
            blockers.append("manager_intent_readiness_review_pack_long_context_not_checked")
    return blockers


def build_pre_live_self_use_decision_pack(evidence: dict[str, Any]) -> dict[str, Any]:
    evidence_status = {
        group_id: dict(evidence.get(group_id) or {})
        for group_id in REQUIRED_PRE_LIVE_EVIDENCE
    }
    missing_evidence = [
        group_id
        for group_id, payload in evidence_status.items()
        if _evidence_missing(group_id, payload)
    ]
    blockers: list[str] = []
    for group_id, payload in evidence_status.items():
        blockers.extend(_evidence_blockers(group_id, payload))
    selected_option = (
        "stay_local_self_use"
        if missing_evidence or blockers
        else "ready_for_human_limited_live_canary_decision"
    )
    ready_for_pl_ce_local_review = (
        not _evidence_missing(
            "pl_ce_local_review_decision_pack",
            evidence_status["pl_ce_local_review_decision_pack"],
        )
        and not any(
            blocker.startswith("pl_ce_local_review_decision_pack_")
            for blocker in blockers
        )
    )
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pre_live_self_use_decision_pack",
            "status": "generated",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pre_live_local_web_self_use_decision_pack",
            "required_evidence": list(REQUIRED_PRE_LIVE_EVIDENCE),
            "evidence_status": evidence_status,
            "missing_evidence": missing_evidence,
            "blockers": blockers,
            "selected_option": selected_option,
            "capability_axis_summary": build_capability_axis_summary(
                evidence_status,
                selected_option=selected_option,
                ready_for_pl_ce_local_review=ready_for_pl_ce_local_review,
            ),
            "selection_reason": (
                "pre_live_evidence_missing"
                if missing_evidence
                else "pre_live_evidence_blocked"
                if blockers
                else "local_web_self_use_evidence_ready_for_human_live_decision"
            ),
            "ready_for_pl_ce_local_review": ready_for_pl_ce_local_review,
            "ready_for_live_diagnostic_decision": False,
            "live_llm_invoked": False,
            "web_tavily_invoked": False,
            "live_canary_approved": False,
            "kimi_active_runtime_default_allowed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "runtime_web_activation_approved": False,
            "production_db_ready_claimed": False,
            "not_claiming": [
                "product_ready",
                "rollout_ready",
                "live_llm_ready",
                "web_ready",
                "production_db_ready",
                "kimi_ready",
            ],
        }
    )


def _load_evidence(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _write_output(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a pre-live Accurate Intake local web self-use decision pack."
    )
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_pre_live_self_use_decision_pack.json",
    )
    args = parser.parse_args(argv)

    pack = build_pre_live_self_use_decision_pack(_load_evidence(Path(args.evidence_json)))
    _write_output(Path(args.output), pack)
    print(json.dumps(pack, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
