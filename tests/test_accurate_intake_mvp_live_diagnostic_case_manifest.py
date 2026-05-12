from __future__ import annotations

import json
from pathlib import Path


MANIFEST_PATH = Path("docs/quality/accurate_intake_mvp_live_diagnostic_case_manifest.json")


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_live_diagnostic_manifest_freezes_18_cases_without_readiness_claims() -> None:
    manifest = _manifest()
    cases = list(manifest["cases"])

    assert manifest["manifest_id"] == "accurate_intake_mvp_live_diagnostic_18_case_manifest_v1"
    assert manifest["case_count"] == 18
    assert len(cases) == 18
    assert len({case["case_id"] for case in cases}) == 18
    assert manifest["live_invocation_allowed_by_manifest"] is False
    assert manifest["readiness_claimed"] is False
    assert manifest["private_self_use_approved"] is False
    assert manifest["fooddb_expansion_approved"] is False
    assert manifest["whole_product_mvp_claimed"] is False


def test_live_diagnostic_manifest_covers_current_shell_case_families() -> None:
    cases = list(_manifest()["cases"])
    families = {str(case["case_family"]) for case in cases}

    assert {
        "no_plan_degraded",
        "active_plan_read",
        "body_observation_write",
        "exact_item_macro_present",
        "generic_food_range",
        "optional_refinement_first_turn",
        "optional_refinement_attach",
        "blocking_clarify_bare_basket",
        "blocking_clarify_answer_attach",
        "overshoot_same_truth",
        "correction_unique_target",
        "removal_unique_target",
        "ambiguous_target_clarify",
        "query_only_no_mutation",
        "unsupported_target_update",
        "websearch_candidate_boundary",
        "macro_missing_hidden",
        "long_session_context_targeting",
    } == families


def test_live_diagnostic_manifest_trace_rubric_matches_manager_react_loop_layers() -> None:
    manifest = _manifest()
    trace_layers = {item["layer_id"]: item for item in manifest["trace_layers"]}

    assert set(trace_layers) == {
        "provider_profile_and_prompt_versions",
        "current_turn_context_packet",
        "manager_pass_1_decision",
        "requested_tools",
        "filtered_tool_plan",
        "executed_tools",
        "compact_packets",
        "manager_pass_2_synthesis",
        "guard_result",
        "mutation_result",
        "renderer_input_basis",
        "final_response_basis",
        "latency_cost_cache_usage",
    }
    for layer_id, layer in trace_layers.items():
        if layer_id == "latency_cost_cache_usage":
            assert layer["blocking"] is False
        else:
            assert layer["blocking"] is True


def test_live_diagnostic_manifest_preserves_semantic_owner_and_deterministic_boundary() -> None:
    manifest = _manifest()
    semantic_owner = dict(manifest["semantic_owner"])
    deterministic_boundary = dict(manifest["deterministic_boundary"])

    assert semantic_owner["user_intent"] == "Manager pass 1 structured decision"
    assert semantic_owner["food_semantics"] == "Manager synthesis over FoodDB/WebSearch packet evidence"
    assert semantic_owner["mutation_legality"] == "deterministic guard"
    assert semantic_owner["app_shell_role"] == "downstream render/browser verifier only"
    assert "infer user intent from keywords" in deterministic_boundary["forbidden"]
    assert "choose target attachment from raw text" in deterministic_boundary["forbidden"]
    assert "invent macro facts" in deterministic_boundary["forbidden"]
    assert "treat WebSearch snippets as truth" in deterministic_boundary["forbidden"]


def test_live_diagnostic_manifest_uses_fixed_cases_and_single_initial_live_probe_policy() -> None:
    manifest = _manifest()
    policy = dict(manifest["case_selection_policy"])

    assert policy["offline_replay_first"] is True
    assert policy["single_live_probe_before_full_matrix"] is True
    assert policy["initial_live_repetitions_per_case"] == 1
    assert policy["case_generation_at_live_time_allowed"] is False
    assert policy["prompt_or_contract_change_requires_replay"] is True


def test_live_diagnostic_cases_have_trace_focus_and_no_exact_response_templates() -> None:
    cases = list(_manifest()["cases"])

    for case in cases:
        assert case["case_id"].startswith("MVP-LIVE-")
        assert case["turns"]
        assert case["expected_trace_focus"]
        assert case["expected_outcome"]
        assert "expected_response_text" not in case
        assert "golden_final_answer" not in case
        assert "utterance_zh_tw" in case["turns"][0]


def test_live_runbook_points_to_fixed_case_manifest() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_LIVE_DIAGNOSTIC_RUNBOOK.md").read_text(
        encoding="utf-8-sig"
    )

    assert "accurate_intake_mvp_live_diagnostic_case_manifest.json" in runbook
    assert "ad hoc cases" in runbook
