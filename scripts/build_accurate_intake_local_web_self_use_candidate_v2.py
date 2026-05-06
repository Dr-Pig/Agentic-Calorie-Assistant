from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_EVIDENCE = (
    "browser_shell_smoke",
    "chat_history_reload",
    "free_text_manual_target",
    "dogfood_review_queue",
    "local_dogfood_data_hygiene",
    "pre_live_decision_pack",
    "pl_ce_local_review_decision_pack",
    "context_live_diagnostic_case_matrix",
    "context_live_diagnostic_anti_overfit_guard",
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
    "pl_ce_local_review_decision_pack": "ready_for_human_pl_ce_review",
    "context_live_diagnostic_case_matrix": "pass",
    "context_live_diagnostic_anti_overfit_guard": "pass",
    "context_live_diagnostic_gate": "context_live_diagnostic_gate_ready_without_live_canary",
    "mvp_gate": "pass",
    "phase_c_gate": "pass",
}

def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))

def _truthy_claim(payload: dict[str, Any], *keys: str) -> bool:
    return any(payload.get(key) is True for key in keys)

def build_local_web_self_use_candidate_v2(evidence: dict[str, Any]) -> dict[str, Any]:
    required_evidence_output = {}
    blockers = []

    # 1. Check all required evidence is present and clean
    for group_id in REQUIRED_EVIDENCE:
        payload = dict(evidence.get(group_id) or {})
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
            if status != expected_status:
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
        if pre_live_pack.get("ready_for_pl_ce_local_review") is not True:
            blockers.append("pre-live missing PL+CE local review gate")
        for missing_group in pre_live_pack.get("missing_evidence") or []:
            blockers.append(f"pre-live missing evidence: {missing_group}")
        for blocker in pre_live_pack.get("blockers") or []:
            blockers.append(f"pre-live blocker: {blocker}")
        if (
            pre_live_pack.get("ready_for_live_diagnostic_decision") is True
            or pre_live_pack.get("live_canary_approved") is True
        ):
            blockers.append("pre-live overclaim")

    pl_ce_pack = dict(evidence.get("pl_ce_local_review_decision_pack") or {})
    if pl_ce_pack and (
        pl_ce_pack.get("ready_for_live_diagnostic_decision") is True
        or pl_ce_pack.get("ready_for_fdb_integration") is True
        or pl_ce_pack.get("real_fooddb_pass_claimed") is True
    ):
        blockers.append("PL+CE local review overclaim")

    blockers = sorted(list(set(blockers)))
    candidate_prepared = len(blockers) == 0

    return _json_safe({
        "local_web_self_use_candidate_v2": {
            "candidate_prepared": candidate_prepared,
            "private_self_use_approved": False,
            "product_readiness_claimed": False,
            "live_manager_required": False,
            "production_selected": False,
            "rollout_approved": False,
            "kimi_activated": False,
            "live_provider_called": False,
            "required_evidence": required_evidence_output,
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
