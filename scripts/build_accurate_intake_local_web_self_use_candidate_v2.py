from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.current_shell_compatibility_ids import (  # noqa: E402
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS,
    CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG,
    LEGACY_LOCAL_REVIEW_GROUP_IDS,
    LEGACY_LOCAL_REVIEW_READY_STATUSES,
    LEGACY_READY_FOR_LOCAL_REVIEW_FLAGS,
    first_group_payload,
    matches_alias,
)
from scripts.accurate_intake_non_fooddb_manager_tool_contract_gate_checks import (  # noqa: E402
    candidate_contract_blockers,
)

REQUIRED_EVIDENCE = (
    "browser_shell_smoke",
    "chat_history_reload",
    "free_text_manual_target",
    "dogfood_review_queue",
    "local_dogfood_data_hygiene",
    "pre_live_decision_pack",
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID,
    "product_pages_self_use_flow_gate",
    "ui_context_alignment_pack",
    "today_macro_mirror_gate",
    "bootstrap_same_truth_gate",
    "body_observation_same_truth_gate",
    "clarify_commit_correction_same_truth_gate",
    "browser_activation_evidence_gate",
    "manager_tool_surface_inventory",
    "non_fooddb_manager_tool_contract",
    "manager_tool_choice_regression_wall",
    "context_conditioned_intent_wall",
    "non_fooddb_read_only_tool_loop_fake_smoke",
    "non_fooddb_mutation_tool_guard_smoke",
    "context_live_diagnostic_case_matrix",
    "context_live_diagnostic_anti_overfit_guard",
    "context_live_diagnostic_holdout_plan",
    "context_live_diagnostic_gate",
    "mvp_gate",
    "phase_c_gate",
)

EXPECTED_STATUS_BY_GROUP = {
    "browser_shell_smoke": "pass",
    "chat_history_reload": "pass",
    "free_text_manual_target": "pass",
    "dogfood_review_queue": "generated",
    "local_dogfood_data_hygiene": "pass",
    "pre_live_decision_pack": "generated",
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS
    ),
    "product_pages_self_use_flow_gate": "product_pages_self_use_flow_ready_for_human_review",
    "ui_context_alignment_pack": "ui_context_alignment_ready_for_human_review",
    "today_macro_mirror_gate": "today_macro_mirror_gate_ready_for_human_review",
    "bootstrap_same_truth_gate": "bootstrap_same_truth_gate_ready_for_human_review",
    "body_observation_same_truth_gate": "body_observation_same_truth_gate_ready_for_human_review",
    "clarify_commit_correction_same_truth_gate": "clarify_commit_correction_same_truth_gate_ready_for_human_review",
    "browser_activation_evidence_gate": "browser_activation_evidence_ready_for_human_review",
    "manager_tool_surface_inventory": "manager_tool_surface_inventory_ready_for_human_review",
    "non_fooddb_manager_tool_contract": "non_fooddb_manager_tool_contract_ready_for_human_review",
    "manager_tool_choice_regression_wall": "manager_tool_choice_regression_wall_pass",
    "context_conditioned_intent_wall": "pass",
    "non_fooddb_read_only_tool_loop_fake_smoke": "non_fooddb_read_only_tool_loop_fake_smoke_pass",
    "non_fooddb_mutation_tool_guard_smoke": "non_fooddb_mutation_tool_guard_smoke_pass",
    "context_live_diagnostic_case_matrix": "pass",
    "context_live_diagnostic_anti_overfit_guard": "pass",
    "context_live_diagnostic_holdout_plan": "pass",
    "context_live_diagnostic_gate": "context_live_diagnostic_gate_ready_without_live_canary",
    "mvp_gate": "pass",
    "phase_c_gate": "pass",
}

def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))

def _truthy_claim(payload: dict[str, Any], *keys: str) -> bool:
    return any(payload.get(key) is True for key in keys)


APPSHELL_GATE_LABELS = {
    "browser_activation_evidence_gate": "browser activation evidence gate",
    "product_pages_self_use_flow_gate": "product pages self-use flow gate",
}


def _resolved_required_payload(evidence: dict[str, Any], group_id: str) -> dict[str, Any]:
    if group_id == CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID:
        payload, _resolved_group_id = first_group_payload(
            evidence,
            CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID,
            *LEGACY_LOCAL_REVIEW_GROUP_IDS,
        )
        return payload
    return dict(evidence.get(group_id) or {})


def _appshell_claim_boundary_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    label = APPSHELL_GATE_LABELS.get(group_id)
    if label is None:
        return []
    blockers: list[str] = []
    if payload.get("pass_type") != "contract":
        blockers.append(f"{label} pass type mismatch")
    if not payload.get("current_shell_sync_contract_source"):
        blockers.append(f"{label} current shell sync contract source missing")
    if not payload.get("manager_runtime_gate_ledger_source"):
        blockers.append(f"{label} manager runtime gate ledger source missing")
    boundary = payload.get("appshell_claim_boundary")
    if not isinstance(boundary, dict):
        blockers.append(f"{label} appshell claim boundary missing")
        return blockers
    if boundary.get("status") != "ready_for_runtime_and_browser_claims":
        blockers.append(f"{label} appshell claim not ready")
    if boundary.get("runtime_backed_claim_ready") is not True:
        blockers.append(f"{label} runtime-backed claim not ready")
    if boundary.get("browser_executed_claim_ready") is not True:
        blockers.append(f"{label} browser-executed claim not ready")
    return blockers


def _any_truthy_claim(evidence: dict[str, Any], *keys: str) -> bool:
    for payload in evidence.values():
        if isinstance(payload, dict) and _truthy_claim(payload, *keys):
            return True
    return False


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _appshell_browser_evidence_chain(evidence: dict[str, Any]) -> dict[str, Any]:
    product_pages_flow = _resolved_required_payload(evidence, "product_pages_self_use_flow_gate")
    browser_activation = _resolved_required_payload(evidence, "browser_activation_evidence_gate")
    product_pages_summary = (
        product_pages_flow.get("summary")
        if isinstance(product_pages_flow.get("summary"), dict)
        else {}
    )
    browser_activation_summary = (
        browser_activation.get("summary")
        if isinstance(browser_activation.get("summary"), dict)
        else {}
    )
    claim_boundary = (
        browser_activation.get("appshell_claim_boundary")
        if isinstance(browser_activation.get("appshell_claim_boundary"), dict)
        else {}
    )

    return _json_safe(
        {
            "product_pages_self_use_flow_status": str(product_pages_flow.get("status") or ""),
            "browser_activation_status": str(browser_activation.get("status") or ""),
            "claim_boundary_status": str(claim_boundary.get("status") or ""),
            "runtime_backed_claim_ready": claim_boundary.get("runtime_backed_claim_ready") is True,
            "browser_executed_claim_ready": claim_boundary.get("browser_executed_claim_ready") is True,
            "browser_artifact_count": _int_value(
                browser_activation_summary.get("browser_artifact_count")
            ),
            "browser_executed_count": _int_value(
                browser_activation_summary.get("browser_executed_count")
            ),
            "all_required_browser_artifacts_executed": (
                browser_activation.get("all_required_browser_artifacts_executed") is True
            ),
            "browser_executed_required": (
                browser_activation.get("browser_executed_required") is True
            ),
            "product_pages_self_use_flow_checked": (
                browser_activation_summary.get("self_use_flow_gate_checked") is True
            ),
            "self_use_flow_gate_strongest_pass_type": str(
                browser_activation_summary.get("self_use_flow_gate_strongest_pass_type")
                or product_pages_summary.get("strongest_consumed_pass_type")
                or ""
            ),
            "today_macro_runtime_mirror_checked": (
                product_pages_summary.get("today_macro_runtime_mirror_checked") is True
            ),
            "renderer_source_closure_checked": (
                product_pages_summary.get("renderer_source_closure_checked") is True
            ),
            "context_target_browser_closure_checked": (
                product_pages_summary.get("context_target_browser_closure_checked") is True
            ),
            "body_noplan_degraded_checked": (
                product_pages_summary.get("body_noplan_degraded_checked") is True
            ),
            "body_observation_same_truth_checked": (
                product_pages_summary.get("body_observation_same_truth_checked") is True
                and browser_activation_summary.get("body_observation_same_truth_checked") is True
            ),
            "fixture_product_loop_steps_checked": _int_value(
                product_pages_summary.get("fixture_product_loop_steps_checked")
            ),
            "live_llm_invoked": _any_truthy_claim(
                evidence,
                "live_provider_called",
                "live_provider_used",
                "live_provider_invoked",
                "live_llm_invoked",
            ),
            "fooddb_evidence_used": _any_truthy_claim(
                evidence,
                "ready_for_fdb_integration",
                "fooddb_truth_updated",
                "fooddb_evidence_used",
                "fooddb_used",
                "real_fooddb_pass_claimed",
                "fooddb_schema_changed",
                "food_evidence_promotion_policy_changed",
            ),
            "websearch_evidence_used": _any_truthy_claim(
                evidence,
                "web_tavily_used",
                "web_tavily_invoked",
                "web_tavily",
                "websearch_evidence_used",
                "WebSearch",
            ),
            "runtime_truth_changed": _any_truthy_claim(evidence, "runtime_truth_changed"),
            "mutation_changed": _any_truthy_claim(evidence, "mutation_changed"),
            "frontend_semantic_owner": _any_truthy_claim(evidence, "frontend_semantic_owner"),
        }
    )


def build_local_web_self_use_candidate_v2(evidence: dict[str, Any]) -> dict[str, Any]:
    required_evidence_output = {}
    blockers = []
    appshell_browser_evidence_chain = _appshell_browser_evidence_chain(evidence)

    # 1. Check all required evidence is present and clean
    for group_id in REQUIRED_EVIDENCE:
        payload = _resolved_required_payload(evidence, group_id)
        present = bool(payload)
        status = str(payload.get("status") or "")
        
        entry = {"present": present, "status": status}
        if group_id not in ("mvp_gate", "phase_c_gate"):
            entry["source"] = payload.get("source")
            
        required_evidence_output[group_id] = entry

        if not present:
            blockers.append(f"missing evidence: {group_id}")
        else:
            expected_status = EXPECTED_STATUS_BY_GROUP[group_id]
            if group_id == CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID:
                if not matches_alias(
                    status,
                    expected_status,
                    *LEGACY_LOCAL_REVIEW_READY_STATUSES,
                ):
                    blockers.append(f"failed evidence: {group_id} status={status}")
            elif status != expected_status:
                blockers.append(f"failed evidence: {group_id} status={status}")

    # 2. Check for blockers in any artifact claims
    for group_id, payload in evidence.items():
        if not isinstance(payload, dict):
            continue
        
        if payload.get("private_self_use_approved") is True:
            blockers.append("private self-use approval attempted")
        
        if payload.get("product_readiness_claimed") is True or payload.get("product_ready") is True:
            blockers.append("readiness overclaim")
            
        if payload.get("web_ready") is True:
            blockers.append("readiness overclaim")

        if _truthy_claim(
            payload,
            "live_provider_called",
            "live_provider_used",
            "live_provider_invoked",
            "live_llm_invoked",
        ):
            blockers.append("live provider used")

        if _truthy_claim(
            payload,
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
        ):
            blockers.append("shared contract change attempted")

        if _truthy_claim(payload, "runtime_truth_changed"):
            blockers.append("runtime truth change attempted")

        if _truthy_claim(payload, "mutation_changed"):
            blockers.append("mutation change attempted")

        if payload.get("local_web_candidate_gate_blocked") is True:
            blockers.append("local web candidate gate evidence blocked")
            
        if _truthy_claim(payload, "kimi_activated"):
            blockers.append("Kimi activated")

        if _truthy_claim(payload, "grokfast_activated", "GrokFast"):
            blockers.append("GrokFast activated")

        if _truthy_claim(
            payload,
            "web_tavily_used",
            "web_tavily_invoked",
            "web_tavily",
            "websearch_evidence_used",
            "WebSearch",
        ):
            blockers.append("websearch used")
            
        if payload.get("production_db_touched") is True:
            blockers.append("production DB touched")

        if (
            payload.get("ready_for_fdb_integration") is True
            or payload.get("fooddb_truth_updated") is True
            or payload.get("fooddb_evidence_used") is True
            or payload.get("fooddb_used") is True
            or payload.get("real_fooddb_pass_claimed") is True
            or payload.get("fooddb_schema_changed") is True
            or payload.get("food_evidence_promotion_policy_changed") is True
        ):
            blockers.append("FoodDB overclaim")

        if group_id == "context_live_diagnostic_case_matrix" and payload.get("plan_only") is not True:
            blockers.append("context live case matrix not plan-only")

        if group_id == "browser_activation_evidence_gate":
            if payload.get("all_required_browser_artifacts_executed") is not True:
                blockers.append("browser activation evidence gate browser artifacts not all executed")
            if payload.get("browser_executed_required") is not True:
                blockers.append("browser activation evidence gate browser execution not required")

        blockers.extend(_appshell_claim_boundary_blockers(group_id, payload))

        if group_id == "manager_tool_surface_inventory":
            summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
            if not isinstance(payload.get("required_direct_lane_ids"), list) or len(payload.get("required_direct_lane_ids")) < 7:
                blockers.append("manager tool inventory required direct lane count too low")
            if not isinstance(payload.get("required_manager_tools"), list) or len(payload.get("required_manager_tools")) < 10:
                blockers.append("manager tool inventory required manager tool count too low")
            if int(summary.get("direct_lane_count") or 0) < 7:
                blockers.append("manager tool inventory direct lane count too low")
            if int(summary.get("target_tool_count") or 0) < 10:
                blockers.append("manager tool inventory target tool count too low")
        if group_id == "non_fooddb_manager_tool_contract":
            blockers.extend(candidate_contract_blockers(payload))

        if group_id == "manager_tool_choice_regression_wall":
            summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
            if payload.get("semantic_owner") != "fixture_manager_structured_decision":
                blockers.append("manager tool choice wall semantic owner mismatch")
            if int(summary.get("case_count") or 0) < 11:
                blockers.append("manager tool choice wall case count too low")

        if group_id == "context_conditioned_intent_wall":
            summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
            if payload.get("manager_fixture_semantic_source_used") is not True:
                blockers.append("context conditioned intent wall fixture semantic source missing")
            if int(summary.get("scenario_count") or 0) < 11:
                blockers.append("context conditioned intent wall scenario count too low")

        if group_id == "non_fooddb_read_only_tool_loop_fake_smoke":
            summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
            if int(summary.get("case_count") or 0) < 6:
                blockers.append("non-fooddb read-only tool smoke case count too low")

        if group_id == "non_fooddb_mutation_tool_guard_smoke":
            summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
            if int(summary.get("case_count") or 0) < 10:
                blockers.append("non-fooddb mutation tool guard smoke case count too low")

        if group_id == "context_live_diagnostic_anti_overfit_guard":
            summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
            if payload.get("plan_only") is not True:
                blockers.append("context live anti-overfit guard not plan-only")
            if summary.get("fixed_case_matrix_used") is not True:
                blockers.append("context live anti-overfit guard missing fixed matrix")
            if int(summary.get("case_count") or 0) < 10:
                blockers.append("context live anti-overfit guard case count too low")
            if int(summary.get("compound_cases") or 0) < 1:
                blockers.append("context live anti-overfit guard compound case missing")
            if int(summary.get("ambiguity_cases") or 0) < 1:
                blockers.append("context live anti-overfit guard ambiguity case missing")

        if group_id == "context_live_diagnostic_holdout_plan":
            summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
            if payload.get("plan_only") is not True:
                blockers.append("context live holdout plan not plan-only")
            if payload.get("fixed_case_matrix_used") is not True:
                blockers.append("context live holdout plan missing fixed matrix")
            if payload.get("holdout_variants_withheld_from_default_live_prompt") is not True:
                blockers.append("context live holdout variants not withheld")
            if payload.get("ad_hoc_live_case_selection_allowed") is not False:
                blockers.append("context live holdout plan allowed ad hoc live cases")
            if payload.get("provider_optimized_case_selection_allowed") is not False:
                blockers.append("context live holdout plan allowed provider-optimized cases")
            if payload.get("blocked_if_single_case_only") is not True:
                blockers.append("context live holdout plan missing single-case blocker")
            if int(summary.get("case_count") or 0) < 10:
                blockers.append("context live holdout plan case count too low")
            if int(summary.get("withheld_holdout_variant_count") or 0) < 20:
                blockers.append("context live holdout plan withheld count too low")
            if int(summary.get("cases_with_holdouts") or 0) < 10:
                blockers.append("context live holdout plan coverage too low")
            if int(summary.get("compound_cases") or 0) < 1:
                blockers.append("context live holdout plan compound case missing")
            if int(summary.get("ambiguity_cases") or 0) < 1:
                blockers.append("context live holdout plan ambiguity case missing")

        if group_id == "context_live_diagnostic_gate":
            if payload.get("live_provider_allowed") is not False:
                blockers.append("context live diagnostic gate allowed live provider")
            if payload.get("live_provider_required") is not False:
                blockers.append("context live diagnostic gate required live provider")
            if payload.get("fixed_case_matrix_used") is not True:
                blockers.append("context live diagnostic gate missing fixed matrix")
            if payload.get("ad_hoc_live_case_selection_allowed") is not False:
                blockers.append("context live diagnostic gate allowed ad hoc live cases")
            if payload.get("anti_overfit_guard_required") is not True:
                blockers.append("context live diagnostic gate missing anti-overfit guard")
            if payload.get("response_contract_dry_run_required") is not True:
                blockers.append("context live diagnostic gate missing response contract dry-run")
            if payload.get("holdout_plan_required") is not True:
                blockers.append("context live diagnostic gate missing holdout plan")

        if payload.get("production_selected") is True:
            blockers.append("readiness overclaim")

        if payload.get("rollout_approved") is True:
            blockers.append("readiness overclaim")

        if payload.get("live_manager_required") is True:
            blockers.append("readiness overclaim")

    pre_live_pack = dict(evidence.get("pre_live_decision_pack") or {})
    if pre_live_pack:
        if pre_live_pack.get("selected_option") != "ready_for_human_limited_live_canary_decision":
            blockers.append(f"pre-live selected option: {pre_live_pack.get('selected_option')}")
        if not any(
            pre_live_pack.get(flag) is True
            for flag in (
                CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG,
                *LEGACY_READY_FOR_LOCAL_REVIEW_FLAGS,
            )
        ):
            blockers.append("pre-live missing CurrentShell compatibility local review gate")
        for missing_group in pre_live_pack.get("missing_evidence") or []:
            blockers.append(f"pre-live missing evidence: {missing_group}")
        for blocker in pre_live_pack.get("blockers") or []:
            blockers.append(f"pre-live blocker: {blocker}")
        if (
            pre_live_pack.get("ready_for_live_diagnostic_decision") is True
            or pre_live_pack.get("live_canary_approved") is True
        ):
            blockers.append("pre-live overclaim")

    current_shell_local_review_pack = _resolved_required_payload(
        evidence,
        CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID,
    )
    if current_shell_local_review_pack and (
        current_shell_local_review_pack.get("ready_for_live_diagnostic_decision") is True
        or current_shell_local_review_pack.get("ready_for_fdb_integration") is True
        or current_shell_local_review_pack.get("real_fooddb_pass_claimed") is True
    ):
        blockers.append("CurrentShell compatibility local review overclaim")

    blockers = sorted(list(set(blockers)))
    candidate_prepared = len(blockers) == 0

    return _json_safe({
        "local_web_self_use_candidate_v2": {
            "candidate_prepared": candidate_prepared,
            "required_evidence": required_evidence_output,
            "appshell_browser_evidence_chain": appshell_browser_evidence_chain,
            "blockers": blockers,
            "next_recommended_slice": (
                ["one_day_realistic_web_dogfood_scenario"]
                if candidate_prepared
                else blockers
            ),
        }
    })

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument(
        "--output", 
        default="artifacts/accurate_intake_local_web_self_use_candidate_v2.json"
    )
    args = parser.parse_args(argv)

    evidence_str = Path(args.evidence_json).read_text(encoding="utf-8")
    evidence = dict(json.loads(evidence_str))
    
    pack = build_local_web_self_use_candidate_v2(evidence)
    
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(pack, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
