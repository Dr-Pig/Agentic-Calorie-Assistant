from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs" / "quality" / "CURRENT_SHELL_SELF_USE_GOLDEN_SET_SPEC.md"
MANIFEST_PATH = ROOT / "docs" / "quality" / "current_shell_self_use_golden_set_manifest.yaml"
DOC_INDEX_PATH = ROOT / "docs" / "DOC_INDEX.md"


def _load_manifest() -> dict:
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8-sig"))


def test_current_shell_self_use_golden_set_is_indexed() -> None:
    doc_index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")

    assert "CURRENT_SHELL_SELF_USE_GOLDEN_SET_SPEC.md" in doc_index
    assert "current_shell_self_use_golden_set_manifest.yaml" in doc_index


def test_golden_set_manifest_declares_scope_non_claims_and_no_fake_pass_policy() -> None:
    manifest = _load_manifest()

    assert manifest["artifact_type"] == "current_shell_self_use_golden_set_manifest"
    assert manifest["version"] == 1
    assert manifest["launch_scope"] == "current_shell_v1_desktop_local_self_use"
    assert manifest["owner_lane"] == "SharedCurrentShell"
    assert manifest["runtime_contract_owner"] == "ManagerRuntime"
    assert manifest["downstream_shell_owner"] == "AppShell"
    assert manifest["case_count"] == 19
    assert manifest["live_model_policy"] == {
        "primary_self_use_gate": "grokfast",
        "kimi_status": "non_blocking_cross_model_diagnostic",
    }
    assert manifest["fixture_policy"] == {
        "fixtures_may_seed_state": True,
        "fixtures_may_decide_intent": False,
        "fixtures_may_decide_action": False,
        "fixtures_may_decide_attach_target": False,
        "fixtures_may_decide_mutation_outcome": False,
        "fixtures_may_decide_response_meaning": False,
    }
    assert manifest["non_claims"] == {
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "whole_product_mvp_ready": False,
        "production_ready": False,
        "fooddb_truth_promoted": False,
    }


def test_golden_set_global_invariants_are_complete_and_enforced_by_cases() -> None:
    manifest = _load_manifest()

    invariant_ids = [entry["invariant_id"] for entry in manifest["global_invariants"]]

    assert invariant_ids == [
        "G0_real_entrypoint_no_fake_pass",
        "G1_semantic_owner",
        "G1A_no_pre_manager_estimability_shortcut",
        "G2_context_engineering",
        "G3_evidence_and_food_truth",
        "G4_manager_react_loop",
        "G5_nutrition_synthesis",
        "G6_state_and_versioning",
        "G7_response_contract",
        "G8_ui_same_truth",
        "G9_pending_and_durability",
        "G10_observability_and_latency",
        "G11_activation_boundary",
    ]

    valid_invariants = set(invariant_ids)
    for case in manifest["cases"]:
        assert set(case["hard_invariants"]).issubset(valid_invariants), case["case_id"]
        assert {"G0_real_entrypoint_no_fake_pass", "G1_semantic_owner"}.issubset(
            case["hard_invariants"]
        ), case["case_id"]


def test_golden_set_cases_cover_locked_self_use_matrix() -> None:
    manifest = _load_manifest()
    cases = {case["case_id"]: case for case in manifest["cases"]}

    assert list(cases) == [f"GS{index}" for index in range(1, 20)]

    gs5 = cases["GS5"]
    assert gs5["title"] == "Patterned breakfast teppan combo without approved anchor"
    assert gs5["expected_runtime"]["workflow_effect"] == "ask_followup"
    assert gs5["expected_runtime"]["mutation_allowed"] is False
    assert gs5["expected_runtime"]["fallback_400_allowed"] is False
    assert gs5["expected_runtime"]["pre_manager_estimability_shortcut_allowed"] is False
    assert gs5["expected_runtime"]["pending_followup_saved"] is True

    gs9 = cases["GS9"]
    assert gs9["expected_runtime"]["workflow_effect"] == "answer_only"
    assert gs9["expected_runtime"]["mutation_allowed"] is False
    assert gs9["expected_runtime"]["inquiry_may_be_treated_as_correction"] is False

    gs16 = cases["GS16"]
    assert gs16["expected_runtime"]["workflow_effect"] == "body_observation_write"
    assert gs16["expected_runtime"]["body_plan_rewrite_allowed"] is False
    assert gs16["ui_assertions"]["body_plan_date_scoped"] is False

    gs17 = cases["GS17"]
    assert gs17["expected_runtime"]["workflow_effect"] == "feedback_capture"
    assert gs17["ui_assertions"]["user_enters_trace_id"] is False
    assert gs17["dogfood_trace"]["feedback_links_to_trace"] is True

    gs19 = cases["GS19"]
    assert gs19["entrypoint"] == "browser_ui"
    assert gs19["expected_runtime"]["workflow_effect"] == "correlated_full_stack_e2e"
    assert gs19["ui_assertions"]["queued_message_survives_navigation"] is True
    assert gs19["dogfood_trace"]["correlates_ui_runtime_read_model_response"] is True


def test_golden_set_declares_websearch_extension_cases() -> None:
    manifest = _load_manifest()

    extension = manifest["websearch_extension"]
    assert extension["case_count"] == 4
    assert extension["status"] == "paused_pending_stage2_calibration"
    assert extension["core_closeout_blocking"] is False
    assert (
        extension["source_truth_role"]
        == "search_candidate_only_until_selected_extract_admissibility_creates_turn_web_evidence"
    )
    assert extension["manager_decides_search_need"] is True
    assert extension["deterministic_search_routing_allowed"] is False
    assert extension["no_snippet_as_truth"] is True
    assert extension["raw_candidate_to_runtime_mutation_allowed"] is False
    assert extension["turn_web_evidence_may_support_same_turn_after_admissibility"] is True
    assert extension["permanent_fooddb_promotion_allowed"] is False

    cases = {case["case_id"]: case for case in extension["cases"]}
    assert list(cases) == ["GSW1", "GSW2", "GSW3", "GSW4"]

    gsw1 = cases["GSW1"]
    assert gsw1["seed_state"]["fooddb_packets"] == "exact_matsuya_tokumori_gyudon_available"
    assert gsw1["seed_state"]["websearch_candidate_sources"] == "not_needed"
    assert gsw1["expected_runtime"]["workflow_effect"] == "commit"
    assert gsw1["expected_runtime"]["websearch_tool_call_expected"] is False
    assert gsw1["expected_runtime"]["exact_fooddb_packet_used"] is True
    assert gsw1["expected_runtime"]["websearch_snippet_as_truth_allowed"] is False
    assert gsw1["expected_runtime"]["runtime_mutation_allowed"] is True
    assert gsw1["expected_runtime"]["pre_manager_websearch_routing_allowed"] is False

    gsw2 = cases["GSW2"]
    assert gsw2["seed_state"]["fooddb_packets"] == "matsuya_gyu_yakiniku_teishoku_exact_missing"
    assert gsw2["expected_runtime"]["websearch_tool_call_expected"] is True
    assert gsw2["expected_runtime"]["search_candidate_packet_truth_allowed"] is False
    assert gsw2["expected_runtime"]["selected_extract_required"] is True
    assert gsw2["expected_runtime"]["source_admissibility_required"] is True
    assert gsw2["expected_runtime"]["turn_web_evidence_packet_allowed"] is True
    assert gsw2["expected_runtime"]["turn_web_evidence_may_support_commit"] is True
    assert gsw2["expected_runtime"]["permanent_fooddb_promotion_allowed"] is False
    assert gsw2["expected_runtime"]["runtime_mutation_allowed"] is True

    gsw3 = cases["GSW3"]
    assert gsw3["seed_state"]["websearch_candidate_sources"] == "frozen_package_or_ecommerce_candidate"
    assert gsw3["expected_runtime"]["websearch_tool_call_expected"] is True
    assert gsw3["expected_runtime"]["wrong_context_source_rejected"] is True
    assert gsw3["expected_runtime"]["turn_web_evidence_packet_allowed"] is False
    assert gsw3["expected_runtime"]["runtime_mutation_allowed"] is False

    gsw4 = cases["GSW4"]
    assert gsw4["seed_state"]["fooddb_packets"] == "mcdonalds_combo_black_box_missing"
    assert gsw4["expected_runtime"]["component_level_evidence_required"] is True
    assert gsw4["expected_runtime"]["generic_combo_black_box_allowed"] is False
    assert gsw4["expected_runtime"]["each_component_source_required"] is True
    assert gsw4["expected_runtime"]["turn_web_evidence_packet_allowed"] is True
    assert gsw4["expected_runtime"]["permanent_fooddb_promotion_allowed"] is False


def test_each_golden_case_has_trace_budget_judge_and_ui_contract_fields() -> None:
    manifest = _load_manifest()
    required_trace_layers = set(manifest["trace_layers"]["blocking"]) | set(
        manifest["trace_layers"]["diagnostic"]
    )

    for case in manifest["cases"]:
        assert case["script"], case["case_id"]
        assert case["seed_state"], case["case_id"]
        assert set(case["required_trace_layers"]).issubset(required_trace_layers), case["case_id"]
        assert case["expected_runtime"], case["case_id"]
        assert case["ui_assertions"], case["case_id"]
        assert case["response_rubric"], case["case_id"]
        assert case["latency_call_budget"]["timeout_is_product_target"] is False, case["case_id"]
        assert "max_llm_calls" in case["latency_call_budget"], case["case_id"]
        assert case["dogfood_trace"]["trace_id_required"] is True, case["case_id"]

    for case in manifest["websearch_extension"]["cases"]:
        assert case["script"], case["case_id"]
        assert case["seed_state"], case["case_id"]
        assert set(case["required_trace_layers"]).issubset(required_trace_layers), case["case_id"]
        assert case["expected_runtime"], case["case_id"]
        assert case["ui_assertions"], case["case_id"]
        assert case["response_rubric"], case["case_id"]
        assert case["latency_call_budget"]["timeout_is_product_target"] is False, case["case_id"]
        assert "max_llm_calls" in case["latency_call_budget"], case["case_id"]
        assert case["dogfood_trace"]["trace_id_required"] is True, case["case_id"]


def test_golden_set_spec_records_hard_boundaries_and_fooddb_posture() -> None:
    text = SPEC_PATH.read_text(encoding="utf-8-sig")

    required_fragments = [
        "Current Shell Self-Use Golden Set",
        "No fake pass",
        "Manager owns semantic intent",
        "Composition sufficiency, estimability, and follow-up necessity are Manager semantic decisions",
        "Deterministic runtime must not inspect raw user text",
        "Active runtime must not produce fallback/shadow 400 nutrition packets",
        "missing evidence into a default 400 kcal estimate",
        "BodyPlan remains a persistent profile and goal surface",
        "Feedback is captured through inline entry points",
        "Structured trace is the primary review surface",
        "Patterned combo anchors are posture-driven",
        "WebSearch Stage 2 Addendum",
        "WebSearch is not part of the core GS1-GS19 closeout gate",
        "Manager decides whether a turn needs external search",
        "Wrong-brand or near-match WebSearch candidates must not be promoted",
        "Grokfast is the primary self-use live gate",
        "Kimi remains a non-blocking cross-model diagnostic",
    ]
    for fragment in required_fragments:
        assert fragment in text
