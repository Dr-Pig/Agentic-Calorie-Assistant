from __future__ import annotations

from pathlib import Path

from app.nutrition.application.retrieval_eval_wall import build_retrieval_eval_wall
from app.nutrition.infrastructure.local_food_evidence_index import LocalSmallAnchorFoodEvidenceIndex


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def _records():
    return LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE).load_records()


def _case_by_id(artifact: dict, section: str, case_id: str) -> dict:
    return {case["case_id"]: case for case in artifact[section]}[case_id]


def test_retrieval_eval_wall_splits_source_ranking_grounding_and_negative_cases() -> None:
    artifact = build_retrieval_eval_wall(retrieval_records=_records())

    assert artifact["artifact_type"] == "accurate_intake_retrieval_eval_wall_v1"
    assert artifact["classification"] == "deterministic_retrieval_eval_wall_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["packetizer_format_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"] == {
        "case_count": 9,
        "source_selection_case_count": 3,
        "ranking_case_count": 2,
        "grounding_case_count": 2,
        "negative_case_count": 2,
        "pass_count": 9,
        "fail_count": 0,
        "websearch_runtime_truth_allowed_count": 0,
        "next_required_slice": "grokfast_fooddb_packet_live_diagnostic",
    }


def test_retrieval_eval_wall_blocks_next_step_when_cases_fail() -> None:
    artifact = build_retrieval_eval_wall(retrieval_records=())

    assert artifact["summary"]["fail_count"] > 0
    assert artifact["summary"]["next_required_slice"] == "inspect_retrieval_eval_wall_failures"


def test_retrieval_eval_wall_source_selection_keeps_websearch_candidate_only() -> None:
    artifact = build_retrieval_eval_wall(retrieval_records=_records())

    exact = _case_by_id(
        artifact,
        "source_selection_cases",
        "exact_brand_keeps_websearch_candidate_only",
    )

    assert exact["status"] == "pass"
    assert exact["backend_sequence"] == [
        "sqlite_fts_index",
        "local_fooddb_index",
        "websearch_candidate_lane",
    ]
    assert exact["runtime_truth_source"] == "approved_fooddb_only"
    assert "no direct runtime truth from websearch" in exact["routing_reasons"]


def test_retrieval_eval_wall_ranking_checks_lexical_runtime_and_modifier_features() -> None:
    artifact = build_retrieval_eval_wall(retrieval_records=_records())

    exact = _case_by_id(artifact, "ranking_cases", "alias_exact_ranking_prefers_runtime_anchor")
    fuzzy = _case_by_id(artifact, "ranking_cases", "fuzzy_candidate_requires_manager_disambiguation")

    assert exact["status"] == "pass"
    assert exact["top_candidate"]["anchor_id"] == "custom_drink_boba_milk_tea"
    assert "runtime_truth_allowed" in exact["top_candidate"]["ranking_reasons"]
    assert "modifier_compatible:cup_size" in exact["top_candidate"]["ranking_reasons"]

    assert fuzzy["status"] == "pass"
    assert fuzzy["top_candidate"]["anchor_id"] == "custom_drink_boba_milk_tea"
    assert fuzzy["top_candidate"]["match_path"] == "fuzzy_alias_expansion"
    assert fuzzy["top_candidate"]["requires_manager_disambiguation"] is True


def test_retrieval_eval_wall_grounding_packets_are_compact_and_read_only() -> None:
    artifact = build_retrieval_eval_wall(retrieval_records=_records())

    fooddb = _case_by_id(artifact, "grounding_cases", "fooddb_packet_is_compact_and_read_only")
    websearch = _case_by_id(artifact, "grounding_cases", "websearch_candidates_remain_candidate_only")

    assert fooddb["status"] == "pass"
    assert fooddb["packet_projection"]["evidence_item_count"] >= 1
    assert "runtime_mutation" in fooddb["packet_projection"]["manager_must_not_use_for"]

    assert websearch["status"] == "pass"
    assert websearch["classification_counts"]["exact_candidate_for_extract_review"] == 1
    assert artifact["summary"]["websearch_runtime_truth_allowed_count"] == 0


def test_retrieval_eval_wall_negative_cases_block_basket_and_exact_candidate_mutation() -> None:
    artifact = build_retrieval_eval_wall(retrieval_records=_records())

    basket = _case_by_id(artifact, "negative_cases", "bare_basket_does_not_estimate")
    exact = _case_by_id(artifact, "negative_cases", "exact_candidates_do_not_mutate")

    assert basket["status"] == "pass"
    assert basket["retrieval_boundary"] == "bare_basket_ask_followup_no_estimate"
    assert exact["status"] == "pass"
    assert exact["exact_card_staging_candidate_count"] == 1


def test_retrieval_eval_wall_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_retrieval_eval_wall import main

    output = tmp_path / "retrieval_eval_wall.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_retrieval_eval_wall_v1"
    assert artifact["summary"]["fail_count"] == 0
