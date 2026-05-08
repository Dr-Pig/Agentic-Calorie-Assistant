from __future__ import annotations

from scripts.build_accurate_intake_local_web_self_use_candidate_v2 import build_local_web_self_use_candidate_v2

def _ready_claim_boundary() -> dict:
    return {
        "status": "ready_for_runtime_and_browser_claims",
        "runtime_backed_claim_ready": True,
        "browser_executed_claim_ready": True,
        "required_manager_runtime_gates": ["rt6_bootstrap_no_plan_body_closure"],
        "green_manager_runtime_gates": ["rt6_bootstrap_no_plan_body_closure"],
        "non_green_manager_runtime_gates": [],
    }


def _blocked_claim_boundary() -> dict:
    return {
        "status": "blocked_on_manager_runtime_upstream_gates",
        "runtime_backed_claim_ready": False,
        "browser_executed_claim_ready": False,
        "required_manager_runtime_gates": [
            "rt6_bootstrap_no_plan_body_closure",
            "rt7_clarify_commit_correction_closure",
        ],
        "green_manager_runtime_gates": ["rt3a_react_trace_observable_skeleton"],
        "non_green_manager_runtime_gates": [
            "rt6_bootstrap_no_plan_body_closure",
            "rt7_clarify_commit_correction_closure",
        ],
    }


def _ready_today_macro_mirror_gate() -> dict:
    return {
        "status": "today_macro_mirror_gate_ready_for_human_review",
        "source": "test",
        "pass_type": "contract",
        "frontend_semantic_owner": False,
        "frontend_calculates_macro_values": False,
        "summary": {
            "renderer_contract_fields_checked": 5,
            "visible_case_checked": True,
            "guarded_case_checked": True,
        },
    }


def _ready_body_observation_same_truth_gate() -> dict:
    return {
        "status": "body_observation_same_truth_gate_ready_for_human_review",
        "source": "test",
        "pass_type": "browser_executed",
        "upstream_runtime_gate": "rt6_bootstrap_no_plan_body_closure",
        "summary": {
            "required_browser_flag_count": 7,
            "all_required_browser_flags_true": True,
            "upstream_gate_green": True,
        },
    }


def _ready_bootstrap_same_truth_gate() -> dict:
    return {
        "status": "bootstrap_same_truth_gate_ready_for_human_review",
        "source": "test",
        "pass_type": "browser_executed",
        "upstream_runtime_gate": "rt6_bootstrap_no_plan_body_closure",
        "summary": {
            "required_browser_flag_count": 10,
            "all_required_browser_flags_true": True,
            "upstream_gate_green": True,
        },
    }


def _ready_clarify_commit_correction_same_truth_gate() -> dict:
    return {
        "status": "clarify_commit_correction_same_truth_gate_ready_for_human_review",
        "source": "test",
        "pass_type": "browser_executed",
        "upstream_runtime_gate": "rt7_clarify_commit_correction_closure",
        "summary": {
            "required_short_term_context_flag_count": 9,
            "required_target_candidate_flag_count": 5,
            "required_fixture_step_count": 8,
            "target_candidate_count_rendered": 2,
            "completed_fixture_step_count": 8,
            "upstream_gate_green": True,
        },
    }


def _clean_evidence() -> dict:
    return {
        "browser_shell_smoke": {"status": "pass", "source": "test"},
        "chat_history_reload": {"status": "pass", "source": "test"},
        "free_text_manual_target": {"status": "pass", "source": "test"},
        "dogfood_review_queue": {"status": "generated", "source": "test"},
        "local_dogfood_data_hygiene": {"status": "pass", "source": "test"},
        "pre_live_decision_pack": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pre_live_self_use_decision_pack",
            "status": "generated",
            "source": "test",
            "selected_option": "ready_for_human_limited_live_canary_decision",
            "missing_evidence": [],
            "blockers": [],
            "ready_for_pl_ce_local_review": True,
            "ready_for_live_diagnostic_decision": False,
            "live_canary_approved": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "pl_ce_local_review_decision_pack": {
            "status": "ready_for_human_pl_ce_review",
            "source": "test",
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "real_fooddb_pass_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "product_pages_self_use_flow_gate": {
            "status": "product_pages_self_use_flow_ready_for_human_review",
            "source": "test",
            "pass_type": "contract",
            "current_shell_sync_contract_source": "docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml",
            "manager_runtime_gate_ledger_source": "docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml",
            "appshell_claim_boundary": _ready_claim_boundary(),
        },
        "ui_context_alignment_pack": {"status": "ui_context_alignment_ready_for_human_review", "source": "test"},
        "today_macro_mirror_gate": _ready_today_macro_mirror_gate(),
        "bootstrap_same_truth_gate": _ready_bootstrap_same_truth_gate(),
        "body_observation_same_truth_gate": _ready_body_observation_same_truth_gate(),
        "clarify_commit_correction_same_truth_gate": _ready_clarify_commit_correction_same_truth_gate(),
        "browser_activation_evidence_gate": {
            "status": "browser_activation_evidence_ready_for_human_review",
            "source": "test",
            "pass_type": "contract",
            "current_shell_sync_contract_source": "docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml",
            "manager_runtime_gate_ledger_source": "docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml",
            "appshell_claim_boundary": _ready_claim_boundary(),
            "all_required_browser_artifacts_executed": True,
            "browser_executed_required": True,
        },
        "manager_tool_surface_inventory": {
            "status": "manager_tool_surface_inventory_ready_for_human_review",
            "source": "test",
            "required_direct_lane_ids": [f"lane-{index}" for index in range(7)],
            "required_manager_tools": [f"tool-{index}" for index in range(10)],
            "summary": {
                "direct_lane_count": 7,
                "target_tool_count": 10,
                "mutation_bearing_lane_count": 4,
                "read_only_tool_count": 6,
            },
        },
        "non_fooddb_manager_tool_contract": {
            "status": "non_fooddb_manager_tool_contract_ready_for_human_review",
            "source": "test",
            "summary": {
                "inventory_backed_tool_count": 10,
                "read_only_tool_count": 7,
                "proposal_tool_count": 1,
                "mutation_tool_count": 3,
                "legacy_direct_route_debt_count": 1,
                "direct_lane_bridge_count": 7,
            },
        },
        "manager_tool_choice_regression_wall": {
            "status": "manager_tool_choice_regression_wall_pass",
            "source": "test",
            "semantic_owner": "fixture_manager_structured_decision",
            "summary": {"case_count": 11},
        },
        "context_conditioned_intent_wall": {
            "status": "pass",
            "source": "test",
            "manager_fixture_semantic_source_used": True,
            "summary": {"scenario_count": 11},
        },
        "non_fooddb_read_only_tool_loop_fake_smoke": {
            "status": "non_fooddb_read_only_tool_loop_fake_smoke_pass",
            "source": "test",
            "summary": {"case_count": 6},
        },
        "non_fooddb_mutation_tool_guard_smoke": {
            "status": "non_fooddb_mutation_tool_guard_smoke_pass",
            "source": "test",
            "summary": {"case_count": 10},
        },
        "context_live_diagnostic_case_matrix": {
            "status": "pass",
            "source": "test",
            "plan_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
        },
        "context_live_diagnostic_anti_overfit_guard": {
            "status": "pass",
            "source": "test",
            "plan_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {
                "fixed_case_matrix_used": True,
                "case_count": 11,
                "compound_cases": 1,
                "ambiguity_cases": 1,
            },
        },
        "context_live_diagnostic_holdout_plan": {
            "status": "pass",
            "source": "test",
            "plan_only": True,
            "fixture_only": True,
            "fixed_case_matrix_used": True,
            "holdout_variants_withheld_from_default_live_prompt": True,
            "ad_hoc_live_case_selection_allowed": False,
            "provider_optimized_case_selection_allowed": False,
            "blocked_if_single_case_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {
                "fixed_case_matrix_used": True,
                "case_count": 11,
                "withheld_holdout_variant_count": 22,
                "cases_with_holdouts": 11,
                "compound_cases": 1,
                "ambiguity_cases": 1,
            },
        },
        "context_live_diagnostic_gate": {
            "status": "context_live_diagnostic_gate_ready_without_live_canary",
            "source": "test",
            "live_provider_allowed": False,
            "live_provider_required": False,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fixed_case_matrix_used": True,
            "ad_hoc_live_case_selection_allowed": False,
            "anti_overfit_guard_required": True,
            "holdout_plan_required": True,
            "response_contract_dry_run_required": True,
            "fooddb_used": False,
            "web_tavily_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
        },
        "mvp_gate": {"status": "pass"},
        "phase_c_gate": {"status": "pass"},
    }

def test_candidate_prepared_when_all_clean() -> None:
    evidence = _clean_evidence()
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is True
    assert pack["local_web_self_use_candidate_v2"]["blockers"] == []

def test_candidate_blocked_when_browser_shell_smoke_missing() -> None:
    evidence = _clean_evidence()
    del evidence["browser_shell_smoke"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: browser_shell_smoke" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_when_chat_history_reload_missing() -> None:
    evidence = _clean_evidence()
    del evidence["chat_history_reload"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: chat_history_reload" in pack["local_web_self_use_candidate_v2"]["blockers"]


def test_candidate_blocked_when_today_macro_mirror_gate_missing() -> None:
    evidence = _clean_evidence()
    del evidence["today_macro_mirror_gate"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: today_macro_mirror_gate" in pack["local_web_self_use_candidate_v2"]["blockers"]


def test_candidate_blocked_when_body_observation_same_truth_gate_missing() -> None:
    evidence = _clean_evidence()
    del evidence["body_observation_same_truth_gate"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: body_observation_same_truth_gate" in pack["local_web_self_use_candidate_v2"]["blockers"]


def test_candidate_blocked_when_clarify_commit_correction_same_truth_gate_missing() -> None:
    evidence = _clean_evidence()
    del evidence["clarify_commit_correction_same_truth_gate"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert (
        "missing evidence: clarify_commit_correction_same_truth_gate"
        in pack["local_web_self_use_candidate_v2"]["blockers"]
    )


def test_candidate_blocked_when_free_text_manual_target_missing() -> None:
    evidence = _clean_evidence()
    del evidence["free_text_manual_target"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: free_text_manual_target" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_when_dogfood_review_queue_missing() -> None:
    evidence = _clean_evidence()
    del evidence["dogfood_review_queue"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: dogfood_review_queue" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_when_local_dogfood_data_hygiene_missing() -> None:
    evidence = _clean_evidence()
    del evidence["local_dogfood_data_hygiene"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: local_dogfood_data_hygiene" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_when_pre_live_decision_pack_missing() -> None:
    evidence = _clean_evidence()
    del evidence["pre_live_decision_pack"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: pre_live_decision_pack" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_when_pl_ce_local_review_decision_pack_missing() -> None:
    evidence = _clean_evidence()
    del evidence["pl_ce_local_review_decision_pack"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: pl_ce_local_review_decision_pack" in pack["local_web_self_use_candidate_v2"]["blockers"]


def test_candidate_blocked_when_browser_activation_or_non_fooddb_tool_evidence_missing() -> None:
    evidence = _clean_evidence()
    del evidence["browser_activation_evidence_gate"]
    del evidence["manager_tool_surface_inventory"]
    del evidence["non_fooddb_manager_tool_contract"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: browser_activation_evidence_gate" in pack["local_web_self_use_candidate_v2"]["blockers"]
    assert "missing evidence: manager_tool_surface_inventory" in pack["local_web_self_use_candidate_v2"]["blockers"]
    assert "missing evidence: non_fooddb_manager_tool_contract" in pack["local_web_self_use_candidate_v2"]["blockers"]


def test_candidate_blocks_browser_activation_and_non_fooddb_tool_overclaims() -> None:
    evidence = _clean_evidence()
    evidence["browser_activation_evidence_gate"].update(
        {
            "all_required_browser_artifacts_executed": False,
            "browser_executed_required": False,
            "product_readiness_claimed": True,
        }
    )
    evidence["manager_tool_choice_regression_wall"].update(
        {
            "semantic_owner": "not_fixture_manager",
            "summary": {"case_count": 2},
        }
    )
    evidence["non_fooddb_mutation_tool_guard_smoke"]["live_llm_invoked"] = True
    pack = build_local_web_self_use_candidate_v2(evidence)
    blockers = pack["local_web_self_use_candidate_v2"]["blockers"]
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "browser activation evidence gate browser artifacts not all executed" in blockers
    assert "browser activation evidence gate browser execution not required" in blockers
    assert "readiness overclaim" in blockers
    assert "manager tool choice wall semantic owner mismatch" in blockers
    assert "manager tool choice wall case count too low" in blockers
    assert "live provider used" in blockers


def test_candidate_blocks_manager_tool_inventory_without_surface_proof() -> None:
    evidence = _clean_evidence()
    evidence["manager_tool_surface_inventory"] = {
        "status": "manager_tool_surface_inventory_ready_for_human_review",
        "summary": {"direct_lane_count": 1, "target_tool_count": 2},
    }
    pack = build_local_web_self_use_candidate_v2(evidence)
    blockers = pack["local_web_self_use_candidate_v2"]["blockers"]
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "manager tool inventory required direct lane count too low" in blockers
    assert "manager tool inventory required manager tool count too low" in blockers
    assert "manager tool inventory direct lane count too low" in blockers
    assert "manager tool inventory target tool count too low" in blockers


def test_candidate_blocks_non_fooddb_manager_tool_contract_without_contract_proof() -> None:
    evidence = _clean_evidence()
    evidence["non_fooddb_manager_tool_contract"] = {
        "status": "non_fooddb_manager_tool_contract_ready_for_human_review",
        "summary": {
            "inventory_backed_tool_count": 2,
            "read_only_tool_count": 1,
            "proposal_tool_count": 0,
            "mutation_tool_count": 1,
            "legacy_direct_route_debt_count": 0,
            "direct_lane_bridge_count": 1,
        },
    }
    pack = build_local_web_self_use_candidate_v2(evidence)
    blockers = pack["local_web_self_use_candidate_v2"]["blockers"]

    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "non-fooddb manager tool contract inventory backed count too low" in blockers
    assert "non-fooddb manager tool contract read-only count too low" in blockers
    assert "non-fooddb manager tool contract direct lane bridge count too low" in blockers


def test_candidate_blocks_missing_browser_activation_appshell_claim_boundary() -> None:
    evidence = _clean_evidence()
    evidence["browser_activation_evidence_gate"].pop("appshell_claim_boundary")

    pack = build_local_web_self_use_candidate_v2(evidence)

    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert (
        "browser activation evidence gate appshell claim boundary missing"
        in pack["local_web_self_use_candidate_v2"]["blockers"]
    )


def test_candidate_blocks_missing_product_pages_appshell_claim_boundary() -> None:
    evidence = _clean_evidence()
    evidence["product_pages_self_use_flow_gate"].pop("appshell_claim_boundary")

    pack = build_local_web_self_use_candidate_v2(evidence)

    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert (
        "product pages self-use flow gate appshell claim boundary missing"
        in pack["local_web_self_use_candidate_v2"]["blockers"]
    )


def test_candidate_blocks_non_ready_appshell_claim_boundaries() -> None:
    evidence = _clean_evidence()
    evidence["browser_activation_evidence_gate"]["appshell_claim_boundary"] = _blocked_claim_boundary()
    evidence["product_pages_self_use_flow_gate"]["appshell_claim_boundary"] = _blocked_claim_boundary()

    pack = build_local_web_self_use_candidate_v2(evidence)
    blockers = pack["local_web_self_use_candidate_v2"]["blockers"]

    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "browser activation evidence gate appshell claim not ready" in blockers
    assert "product pages self-use flow gate appshell claim not ready" in blockers

def test_candidate_blocked_when_context_live_case_matrix_missing() -> None:
    evidence = _clean_evidence()
    del evidence["context_live_diagnostic_case_matrix"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: context_live_diagnostic_case_matrix" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocks_context_live_case_matrix_overclaims() -> None:
    evidence = _clean_evidence()
    evidence["context_live_diagnostic_case_matrix"]["plan_only"] = False
    evidence["context_live_diagnostic_case_matrix"]["live_provider_invoked"] = True
    evidence["context_live_diagnostic_case_matrix"]["fooddb_used"] = True
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "context live case matrix not plan-only" in pack["local_web_self_use_candidate_v2"]["blockers"]
    assert "live provider used" in pack["local_web_self_use_candidate_v2"]["blockers"]
    assert "FoodDB overclaim" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_when_context_live_anti_overfit_guard_missing() -> None:
    evidence = _clean_evidence()
    del evidence["context_live_diagnostic_anti_overfit_guard"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert (
        "missing evidence: context_live_diagnostic_anti_overfit_guard"
        in pack["local_web_self_use_candidate_v2"]["blockers"]
    )

def test_candidate_blocked_when_context_live_holdout_plan_missing() -> None:
    evidence = _clean_evidence()
    del evidence["context_live_diagnostic_holdout_plan"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert (
        "missing evidence: context_live_diagnostic_holdout_plan"
        in pack["local_web_self_use_candidate_v2"]["blockers"]
    )

def test_candidate_blocks_context_live_holdout_plan_overfit_risks() -> None:
    evidence = _clean_evidence()
    evidence["context_live_diagnostic_holdout_plan"].update(
        {
            "plan_only": False,
            "holdout_variants_withheld_from_default_live_prompt": False,
            "ad_hoc_live_case_selection_allowed": True,
            "provider_optimized_case_selection_allowed": True,
            "blocked_if_single_case_only": False,
            "live_provider_invoked": True,
            "fooddb_used": True,
            "fixed_case_matrix_used": False,
            "summary": {
                "case_count": 1,
                "withheld_holdout_variant_count": 0,
                "cases_with_holdouts": 0,
                "compound_cases": 0,
                "ambiguity_cases": 0,
            },
        }
    )
    pack = build_local_web_self_use_candidate_v2(evidence)
    blockers = pack["local_web_self_use_candidate_v2"]["blockers"]
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "context live holdout plan not plan-only" in blockers
    assert "context live holdout variants not withheld" in blockers
    assert "context live holdout plan allowed ad hoc live cases" in blockers
    assert "context live holdout plan allowed provider-optimized cases" in blockers
    assert "context live holdout plan missing single-case blocker" in blockers
    assert "context live holdout plan case count too low" in blockers
    assert "context live holdout plan withheld count too low" in blockers
    assert "context live holdout plan coverage too low" in blockers
    assert "context live holdout plan compound case missing" in blockers
    assert "context live holdout plan ambiguity case missing" in blockers
    assert "live provider used" in blockers
    assert "FoodDB overclaim" in blockers

def test_candidate_blocked_when_context_live_gate_missing() -> None:
    evidence = _clean_evidence()
    del evidence["context_live_diagnostic_gate"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert (
        "missing evidence: context_live_diagnostic_gate"
        in pack["local_web_self_use_candidate_v2"]["blockers"]
    )

def test_candidate_blocks_live_context_gate_overclaims() -> None:
    evidence = _clean_evidence()
    evidence["context_live_diagnostic_gate"].update(
        {
            "status": "context_live_diagnostic_gate_ready_with_live_canary",
            "live_provider_allowed": True,
            "live_llm_invoked": True,
            "live_provider_invoked": True,
            "fooddb_used": True,
            "ad_hoc_live_case_selection_allowed": True,
            "holdout_plan_required": False,
        }
    )
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert (
        "failed evidence: context_live_diagnostic_gate status="
        "context_live_diagnostic_gate_ready_with_live_canary"
        in pack["local_web_self_use_candidate_v2"]["blockers"]
    )
    assert "live provider used" in pack["local_web_self_use_candidate_v2"]["blockers"]
    assert "FoodDB overclaim" in pack["local_web_self_use_candidate_v2"]["blockers"]
    assert "context live diagnostic gate allowed live provider" in pack[
        "local_web_self_use_candidate_v2"
    ]["blockers"]
    assert "context live diagnostic gate allowed ad hoc live cases" in pack[
        "local_web_self_use_candidate_v2"
    ]["blockers"]
    assert "context live diagnostic gate missing holdout plan" in pack[
        "local_web_self_use_candidate_v2"
    ]["blockers"]

def test_candidate_requires_pre_live_pack_to_reference_pl_ce_local_review() -> None:
    evidence = _clean_evidence()
    evidence["pre_live_decision_pack"]["ready_for_pl_ce_local_review"] = False
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "pre-live missing PL+CE local review gate" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocks_pre_live_live_decision_or_canary_approval() -> None:
    for flag in ("ready_for_live_diagnostic_decision", "live_canary_approved"):
        evidence = _clean_evidence()
        evidence["pre_live_decision_pack"][flag] = True
        pack = build_local_web_self_use_candidate_v2(evidence)
        assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
        assert "pre-live overclaim" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocks_pl_ce_decision_pack_overclaims() -> None:
    evidence = _clean_evidence()
    evidence["pl_ce_local_review_decision_pack"].update(
        {
            "ready_for_live_diagnostic_decision": True,
            "ready_for_fdb_integration": True,
            "real_fooddb_pass_claimed": True,
        }
    )
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "PL+CE local review overclaim" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_if_private_self_use_approved_true() -> None:
    evidence = _clean_evidence()
    evidence["some_evil_artifact"] = {"private_self_use_approved": True}
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "private self-use approval attempted" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_if_kimi_activated_or_live_provider_used() -> None:
    evidence = _clean_evidence()
    evidence["some_artifact"] = {"kimi_activated": True}
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "Kimi activated" in pack["local_web_self_use_candidate_v2"]["blockers"]
    
    evidence2 = _clean_evidence()
    evidence2["some_artifact"] = {"live_provider_called": True}
    pack2 = build_local_web_self_use_candidate_v2(evidence2)
    assert pack2["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "live provider used" in pack2["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_if_live_llm_grokfast_or_websearch_used() -> None:
    cases = (
        ("live_llm_invoked", "live provider used"),
        ("web_tavily_used", "websearch used"),
        ("web_tavily_invoked", "websearch used"),
        ("web_tavily", "websearch used"),
        ("websearch_evidence_used", "websearch used"),
        ("WebSearch", "websearch used"),
        ("grokfast_activated", "GrokFast activated"),
        ("GrokFast", "GrokFast activated"),
    )
    for flag, blocker in cases:
        evidence = _clean_evidence()
        evidence["some_artifact"] = {flag: True}
        pack = build_local_web_self_use_candidate_v2(evidence)
        assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
        assert blocker in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_if_any_artifact_claims_fooddb_truth_or_integration() -> None:
    cases = (
        "ready_for_fdb_integration",
        "fooddb_truth_updated",
        "fooddb_evidence_used",
        "fooddb_used",
        "real_fooddb_pass_claimed",
        "fooddb_schema_changed",
        "food_evidence_promotion_policy_changed",
    )
    for flag in cases:
        evidence = _clean_evidence()
        evidence["some_artifact"] = {flag: True}
        pack = build_local_web_self_use_candidate_v2(evidence)
        assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
        assert "FoodDB overclaim" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_never_sets_product_readiness_claimed_true() -> None:
    pack = build_local_web_self_use_candidate_v2(_clean_evidence())
    assert pack["local_web_self_use_candidate_v2"]["product_readiness_claimed"] is False
    assert pack["local_web_self_use_candidate_v2"]["private_self_use_approved"] is False
    assert pack["local_web_self_use_candidate_v2"]["kimi_activated"] is False

def test_candidate_blocked_if_production_selected_or_rollout_approved_or_live_manager_required() -> None:
    for field in ("production_selected", "rollout_approved", "live_manager_required", "web_ready", "product_ready"):
        evidence = _clean_evidence()
        evidence["some_artifact"] = {field: True}
        pack = build_local_web_self_use_candidate_v2(evidence)
        assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
        assert "readiness overclaim" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_if_production_db_touched() -> None:
    evidence = _clean_evidence()
    evidence["some_artifact"] = {"production_db_touched": True}
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "production DB touched" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocks_pre_live_selected_option_or_blockers() -> None:
    evidence = _clean_evidence()
    evidence["pre_live_decision_pack"]["selected_option"] = "stay_local_self_use"
    evidence["pre_live_decision_pack"]["missing_evidence"] = ["phase_c_gate"]
    evidence["pre_live_decision_pack"]["blockers"] = ["local_operator_data_hygiene_bundle_writes_performed"]

    pack = build_local_web_self_use_candidate_v2(evidence)

    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "pre-live selected option: stay_local_self_use" in pack["local_web_self_use_candidate_v2"]["blockers"]
    assert "pre-live missing evidence: phase_c_gate" in pack["local_web_self_use_candidate_v2"]["blockers"]
    assert (
        "pre-live blocker: local_operator_data_hygiene_bundle_writes_performed"
        in pack["local_web_self_use_candidate_v2"]["blockers"]
    )

def test_candidate_blocked_if_shared_contract_runtime_truth_or_mutation_changes() -> None:
    cases = (
        ("manager_context_packet_schema_changed", "shared contract change attempted"),
        ("nutrition_evidence_store_port_changed", "shared contract change attempted"),
        ("food_evidence_record_schema_changed", "shared contract change attempted"),
        ("packet_ready_anchor_schema_changed", "shared contract change attempted"),
        ("packetizer_format_changed", "shared contract change attempted"),
        ("basket_semantics_changed", "shared contract change attempted"),
        ("runtime_truth_changed", "runtime truth change attempted"),
        ("mutation_changed", "mutation change attempted"),
    )
    for flag, blocker in cases:
        evidence = _clean_evidence()
        evidence["some_artifact"] = {flag: True}
        pack = build_local_web_self_use_candidate_v2(evidence)
        assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
        assert blocker in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_if_runner_gate_evidence_is_invalid() -> None:
    evidence = _clean_evidence()
    evidence["local_web_candidate_gate_evidence"] = {
        "status": "blocked_invalid_evidence",
        "local_web_candidate_gate_blocked": True,
    }
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "local web candidate gate evidence blocked" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_present_evidence_with_failed_status_blocks_as_failed_evidence() -> None:
    evidence = _clean_evidence()
    evidence["browser_shell_smoke"]["status"] = "blocked"
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "failed evidence: browser_shell_smoke status=blocked" in pack["local_web_self_use_candidate_v2"]["blockers"]
