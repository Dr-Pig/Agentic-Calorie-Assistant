from __future__ import annotations

import json
from pathlib import Path

from scripts.run_v2_benchmark_shadow_eval import _parse_replay_cases


ROOT = Path(__file__).resolve().parents[1]
TURN2_FIXTURE = ROOT / "docs" / "quality" / "turn2_hybrid_replay_pack_v1.json"
COVERAGE_MAP = ROOT / "docs" / "quality" / "turn2_mvp_ux_coverage_map.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_turn2_fixture_is_reconstructed_as_regression_coverage_not_product_truth() -> None:
    payload = _load(TURN2_FIXTURE)

    assert payload["suite_id"] == "turn2_hybrid_replay_pack_v1"
    assert payload["role"] == "regression_coverage"
    assert payload["truth_source_role"] == "validator_not_product_architecture"
    assert payload["live_llm_required"] is False
    assert payload["mutation_authority"] is False
    assert len(payload["cases"]) == 9

    case_ids = {case["case_id"] for case in payload["cases"]}
    assert case_ids == {f"turn2-{index:03d}" for index in range(1, 10)}
    assert {
        "ask_followup_only_to_completion",
        "estimate_with_followup_to_refinement",
    } <= {case["lane_family"] for case in payload["cases"]}


def test_turn2_fixture_cases_have_mvp_context_and_state_effect_metadata() -> None:
    payload = _load(TURN2_FIXTURE)

    for case in payload["cases"]:
        assert case["input_shape"] == "multi_turn_text_pair"
        assert case["capability_layer"] in {"L1_L3_L5_L6_L7", "L1_L3_L8"}
        assert case["expected_attachment"]["target_object_type"] == "meal_thread"
        assert case["expected_attachment"]["mutation_authority"] is False
        assert case["expected_persistence"]["role"] == "expected_state_effect"
        assert case["expected_persistence"]["requires_phase_c_uow"] is True
        assert case["mvp_ux_moment"] in {
            "followup_completion",
            "estimate_refinement",
        }
        assert case["forbidden_outcomes"]


def test_turn2_coverage_map_declares_mvp_gaps_requiring_new_regression_wall() -> None:
    payload = _load(COVERAGE_MAP)

    assert payload["map_id"] == "turn2_mvp_ux_coverage_map_v1"
    assert payload["source_suite_id"] == "turn2_hybrid_replay_pack_v1"
    assert payload["fixture_role"] == "regression_coverage_only"
    assert payload["mvp_gap_status"] == "requires_new_regression_wall"
    assert {entry["case_id"] for entry in payload["case_coverage"]} == {
        f"turn2-{index:03d}" for index in range(1, 10)
    }
    missing = {gap["gap_id"] for gap in payload["mvp_ux_gaps"]}
    assert {
        "stable_correction_target_ref",
        "multi_item_ambiguity_no_autoselect",
        "no_plan_budget_honesty",
        "active_version_vs_superseded_truth",
        "ledger_audit_not_current_truth",
        "context_promotion_trace",
        "session_block_loses_to_canonical_state",
        "read_model_same_truth",
        "persistence_reload_same_truth",
        "negative_authority_assertions",
    } <= missing


def test_shadow_registry_parser_reads_reconstructed_turn2_fixture() -> None:
    cases = _parse_replay_cases()

    assert len(cases) == 9
    assert all(case["source_suite"] == "turn2_hybrid_replay_pack_v1" for case in cases)
    assert all(case["input_shape"] == "multi_turn_text_pair" for case in cases)
