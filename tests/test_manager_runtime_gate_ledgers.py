from __future__ import annotations

from pathlib import Path

import yaml


SYNC_CONTRACT_PATH = Path("docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml")
GATE_LEDGER_PATH = Path("docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml")


def test_current_shell_sync_contract_records_launch_scope_and_claim_rules() -> None:
    contract = yaml.safe_load(SYNC_CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["artifact_type"] == "current_shell_sync_contract"
    assert contract["launch_scope"] == "current_shell_v1"
    assert contract["runtime_contract_owner"] == "ManagerRuntime"
    assert contract["downstream_shell_owner"] == "AppShell"
    assert contract["in_scope_journeys"] == ["A", "B", "C", "D", "E", "G", "H", "J", "K"]
    assert contract["read_only_seams"] == ["I"]
    assert "U" in contract["deferred_journeys"]
    assert contract["pass_taxonomy"] == [
        "static",
        "contract",
        "fixture",
        "runtime_backed",
        "browser_executed",
    ]
    assert contract["appshell_rules"] == {
        "static_contract_fixture_may_queue_without_runtime_gate": True,
        "runtime_backed_requires_upstream_gate_green": True,
        "browser_executed_requires_upstream_gate_green": True,
        "may_not_invent_runtime_semantics": True,
    }
    assert contract["runtime_architecture_rules"] == {
        "dependency_inversion_required_across_db_websearch_and_provider_adapters": True,
        "system_prompt_and_model_profile_overlays_versioned_separately": True,
        "provider_or_model_specific_prompt_policy_must_not_own_runtime_truth": True,
    }
    assert contract["non_claims"]["private_self_use_approved"] is False


def test_manager_runtime_gate_ledger_records_small_slice_gate_order() -> None:
    ledger = yaml.safe_load(GATE_LEDGER_PATH.read_text(encoding="utf-8"))

    assert ledger["artifact_type"] == "manager_runtime_gate_ledger"
    assert ledger["launch_scope"] == "current_shell_v1"
    assert ledger["owner"] == "ManagerRuntime"

    gates = {entry["gate_id"]: entry for entry in ledger["gates"]}

    assert gates["rt0_sync_contract"]["status"] == "green"
    assert gates["rt1a_prompt_registry_and_trace_versioning"]["status"] == "green"
    assert gates["rt1a_prompt_registry_and_trace_versioning"]["title"] == (
        "Prompt registry, system/model split, and trace version IDs"
    )
    assert gates["rt1b_stable_prefix_dynamic_suffix_contract"]["depends_on"] == [
        "rt1a_prompt_registry_and_trace_versioning"
    ]
    assert gates["rt1b_stable_prefix_dynamic_suffix_contract"]["title"] == (
        "Stable prefix, dynamic suffix, and provider-neutral prompt contract"
    )
    assert gates["rt1b_stable_prefix_dynamic_suffix_contract"]["status"] == "green"
    assert gates["rt1b_stable_prefix_dynamic_suffix_contract"]["pass_type"] == "contract"
    assert gates["rt1c_cache_metrics_observability"]["depends_on"] == [
        "rt1b_stable_prefix_dynamic_suffix_contract"
    ]
    assert gates["rt1c_cache_metrics_observability"]["status"] == "green"
    assert gates["rt1c_cache_metrics_observability"]["pass_type"] == "contract"
    assert gates["rt2_coarse_tool_surface_convergence"]["status"] == "green"
    assert gates["rt2a_public_tool_name_normalization"]["status"] == "green"
    assert gates["rt2a_public_tool_name_normalization"]["title"] == (
        "Public tool name normalization at manager boundary"
    )
    assert gates["rt2b_entry_fallback_public_tool_surface"]["status"] == "green"
    assert gates["rt2b_entry_fallback_public_tool_surface"]["title"] == (
        "Entry and fallback public tool-surface normalization"
    )
    assert gates["rt2_coarse_tool_surface_convergence"]["depends_on"] == [
        "rt2a_public_tool_name_normalization",
        "rt2b_entry_fallback_public_tool_surface",
        "rt2c_read_only_public_tool_runtime_smoke",
    ]
    assert gates["rt2c_read_only_public_tool_runtime_smoke"]["status"] == "green"
    assert gates["rt2c_read_only_public_tool_runtime_smoke"]["depends_on"] == [
        "rt2a_public_tool_name_normalization",
        "rt2b_entry_fallback_public_tool_surface",
    ]
    assert gates["rt3_react_trace_contract"]["status"] == "green"
    assert gates["rt3a_react_trace_observable_skeleton"]["status"] == "green"
    assert gates["rt3a_react_trace_observable_skeleton"]["title"] == "ReAct trace observable skeleton"
    assert gates["rt3b_multi_pass_react_trace_summary"]["status"] == "green"
    assert gates["rt3b_multi_pass_react_trace_summary"]["title"] == "Compact multi-pass ReAct trace summary"
    assert gates["rt3_react_trace_contract"]["depends_on"] == [
        "rt3a_react_trace_observable_skeleton",
        "rt3b_multi_pass_react_trace_summary",
    ]
    assert gates["rt4_context_packet_acceptance"]["status"] == "green"
    assert gates["rt4a_runtime_context_packet_acceptance"]["status"] == "green"
    assert gates["rt4a_runtime_context_packet_acceptance"]["title"] == "Runtime context packet acceptance smoke"
    assert gates["rt4_context_packet_acceptance"]["depends_on"] == [
        "rt3_react_trace_contract",
        "rt4a_runtime_context_packet_acceptance",
    ]
    assert gates["rt5_intent_tool_argument_walls"]["status"] == "green"
    assert gates["rt5_intent_tool_argument_walls"]["depends_on"] == [
        "rt2_coarse_tool_surface_convergence",
        "rt4_context_packet_acceptance",
    ]
    assert gates["rt6_bootstrap_no_plan_body_closure"]["status"] == "green"
    assert gates["rt7a_correction_removal_runtime_boundary"]["status"] == "green"
    assert gates["rt7a_correction_removal_runtime_boundary"]["depends_on"] == [
        "rt4_context_packet_acceptance",
        "rt5_intent_tool_argument_walls",
        "rt6_bootstrap_no_plan_body_closure",
    ]
    assert gates["rt7b_blocking_clarify_pending_followup_boundary"]["status"] == "green"
    assert gates["rt7b_blocking_clarify_pending_followup_boundary"]["depends_on"] == [
        "rt4_context_packet_acceptance",
        "rt5_intent_tool_argument_walls",
        "rt6_bootstrap_no_plan_body_closure",
    ]
    assert gates["rt7c_single_turn_commit_boundary"]["status"] == "green"
    assert gates["rt7c_single_turn_commit_boundary"]["depends_on"] == [
        "rt3_react_trace_contract",
        "rt5_intent_tool_argument_walls",
        "rt6_bootstrap_no_plan_body_closure",
    ]
    assert gates["rt7d_optional_refinement_attach_boundary"]["status"] == "green"
    assert gates["rt7d_optional_refinement_attach_boundary"]["depends_on"] == [
        "rt3_react_trace_contract",
        "rt4_context_packet_acceptance",
        "rt5_intent_tool_argument_walls",
        "rt6_bootstrap_no_plan_body_closure",
        "rt7c_single_turn_commit_boundary",
    ]
    assert gates["rt7_clarify_commit_correction_closure"]["status"] == "green"
    assert gates["rt7_clarify_commit_correction_closure"]["depends_on"] == [
        "rt5_intent_tool_argument_walls",
        "rt6_bootstrap_no_plan_body_closure",
        "rt7a_correction_removal_runtime_boundary",
        "rt7b_blocking_clarify_pending_followup_boundary",
        "rt7c_single_turn_commit_boundary",
        "rt7d_optional_refinement_attach_boundary",
    ]
    assert gates["rt8_overshoot_runtime_truth"]["status"] == "green"
    assert gates["rt8_overshoot_runtime_truth"]["depends_on"] == ["rt7_clarify_commit_correction_closure"]
    assert gates["rt9_packet_consumption_seam"]["status"] == "green"
    assert gates["rt9_packet_consumption_seam"]["depends_on"] == [
        "rt7_clarify_commit_correction_closure",
        "rt8_overshoot_runtime_truth",
    ]
    assert gates["rt10a_nutrition_estimate_quality_deterministic"]["status"] == "green"
    assert gates["rt10a_nutrition_estimate_quality_deterministic"]["pass_type"] == "fixture"
    assert gates["rt10a_nutrition_estimate_quality_deterministic"]["depends_on"] == [
        "rt9_packet_consumption_seam"
    ]
    assert gates["rt10b_nutrition_estimate_quality_fake_provider"]["depends_on"] == [
        "rt10a_nutrition_estimate_quality_deterministic"
    ]
    assert gates["rt10b_nutrition_estimate_quality_fake_provider"]["status"] == "green"
    assert gates["rt10b_nutrition_estimate_quality_fake_provider"]["pass_type"] == "fixture"
    assert gates["rt11_final_response_quality"]["status"] == "green"
    assert gates["rt11_final_response_quality"]["pass_type"] == "fixture"
    assert gates["rt11_final_response_quality"]["depends_on"] == [
        "rt7_clarify_commit_correction_closure",
        "rt10a_nutrition_estimate_quality_deterministic",
    ]
    assert gates["rt12_trace_grading_v1"]["status"] == "green"
    assert gates["rt12_trace_grading_v1"]["pass_type"] == "fixture"
    assert gates["rt12_trace_grading_v1"]["depends_on"] == [
        "rt3_react_trace_contract",
        "rt5_intent_tool_argument_walls",
        "rt11_final_response_quality",
    ]
    assert gates["rt13_observability_pack"]["status"] == "green"
    assert gates["rt13_observability_pack"]["pass_type"] == "contract"
    assert gates["rt13_observability_pack"]["depends_on"] == [
        "rt1a_prompt_registry_and_trace_versioning",
        "rt3_react_trace_contract",
    ]
    assert gates["rt14a_provider_health_schema_live_foundation"]["status"] == "green"
    assert gates["rt14a_provider_health_schema_live_foundation"]["pass_type"] == "contract"
    assert gates["rt14a_provider_health_schema_live_foundation"]["depends_on"] == [
        "rt1c_cache_metrics_observability",
        "rt13_observability_pack",
    ]
    assert gates["rt14b_provider_health_live_canary"]["status"] == "green"
    assert gates["rt14b_provider_health_live_canary"]["pass_type"] == "runtime_backed"
    assert gates["rt14b_provider_health_live_canary"]["depends_on"] == [
        "rt14a_provider_health_schema_live_foundation",
    ]
    assert gates["rt14c_schema_contract_live_canary"]["status"] == "green"
    assert gates["rt14c_schema_contract_live_canary"]["pass_type"] == "runtime_backed"
    assert gates["rt14c_schema_contract_live_canary"]["depends_on"] == [
        "rt14b_provider_health_live_canary",
    ]
    assert gates["rt14_limited_live_ladder"]["depends_on"] == [
        "rt14c_schema_contract_live_canary",
        "rt14b_provider_health_live_canary",
        "rt14a_provider_health_schema_live_foundation",
        "rt1c_cache_metrics_observability",
        "rt10b_nutrition_estimate_quality_fake_provider",
        "rt11_final_response_quality",
        "rt12_trace_grading_v1",
        "rt13_observability_pack",
    ]


def test_manager_runtime_gate_ledger_maps_current_shell_journeys_to_runtime_gates() -> None:
    ledger = yaml.safe_load(GATE_LEDGER_PATH.read_text(encoding="utf-8"))

    assert ledger["journey_gate_map"]["A"] == ["rt6_bootstrap_no_plan_body_closure"]
    assert ledger["journey_gate_map"]["B"] == [
        "rt3_react_trace_contract",
        "rt5_intent_tool_argument_walls",
        "rt7_clarify_commit_correction_closure",
    ]
    assert ledger["journey_gate_map"]["E"] == ["rt8_overshoot_runtime_truth"]
    assert ledger["journey_gate_map"]["K"] == [
        "rt4_context_packet_acceptance",
        "rt7_clarify_commit_correction_closure",
    ]


def test_manager_runtime_gate_artifacts_are_structurally_consistent() -> None:
    contract = yaml.safe_load(SYNC_CONTRACT_PATH.read_text(encoding="utf-8"))
    ledger = yaml.safe_load(GATE_LEDGER_PATH.read_text(encoding="utf-8"))

    gates = {entry["gate_id"]: entry for entry in ledger["gates"]}
    in_scope_journeys = set(contract["in_scope_journeys"])
    read_only_seams = set(contract["read_only_seams"])
    deferred_journeys = set(contract["deferred_journeys"])
    journey_gate_map = ledger["journey_gate_map"]

    assert in_scope_journeys == set(journey_gate_map)
    assert in_scope_journeys.isdisjoint(read_only_seams)
    assert in_scope_journeys.isdisjoint(deferred_journeys)
    assert read_only_seams.isdisjoint(deferred_journeys)

    for gate in ledger["gates"]:
        for dependency in gate["depends_on"]:
            assert dependency in gates

    for journey_gates in journey_gate_map.values():
        for gate_id in journey_gates:
            assert gate_id in gates
