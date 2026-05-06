from __future__ import annotations

from pathlib import Path

from app.nutrition.application.retrieval_eval_wall import build_retrieval_eval_wall
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)

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
    summary = artifact["summary"]
    assert summary["case_count"] >= 19
    assert summary["source_selection_case_count"] >= 7
    assert summary["ranking_case_count"] >= 5
    assert summary["grounding_case_count"] >= 3
    assert summary["negative_case_count"] >= 4
    assert summary["pass_count"] == summary["case_count"]
    assert summary["fail_count"] == 0
    assert summary["websearch_runtime_truth_allowed_count"] == 0
    assert summary["next_required_slice"] == "grokfast_fooddb_packet_live_diagnostic"


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


def test_retrieval_eval_wall_source_selection_blocks_raw_text_hint_execution() -> None:
    artifact = build_retrieval_eval_wall(retrieval_records=_records())

    raw_hint = _case_by_id(
        artifact,
        "source_selection_cases",
        "raw_text_hint_does_not_execute_backend",
    )

    assert raw_hint["status"] == "pass"
    assert raw_hint["primary_backend"] == "blocked_no_execution"
    assert raw_hint["backend_sequence"] == []
    assert raw_hint["retrieval_intent_source"] == "raw_text_hint"
    assert raw_hint["manager_owned_intent_required"] is True
    assert raw_hint["raw_text_hint_executed"] is False
    assert raw_hint["runtime_truth_source"] == "manager_owned_retrieval_intent_required"


def test_retrieval_eval_wall_source_selection_covers_listed_query_and_disabled_websearch() -> None:
    artifact = build_retrieval_eval_wall(retrieval_records=_records())

    listed = _case_by_id(
        artifact,
        "source_selection_cases",
        "listed_basket_components_stay_fooddb_only",
    )
    query = _case_by_id(artifact, "source_selection_cases", "query_only_route_is_read_only")
    exact_disabled = _case_by_id(
        artifact,
        "source_selection_cases",
        "exact_brand_without_websearch_keeps_fooddb_only",
    )

    assert listed["status"] == "pass"
    assert listed["backend_sequence"] == ["sqlite_fts_index", "local_fooddb_index"]
    assert listed["websearch_candidate_enabled"] is False
    assert "listed basket stays on approved FoodDB component anchors only" in listed[
        "routing_reasons"
    ]

    assert query["status"] == "pass"
    assert query["read_only"] is True
    assert query["mutation_allowed"] is False
    assert "query-only lookup remains read-only" in query["routing_reasons"]

    assert exact_disabled["status"] == "pass"
    assert exact_disabled["backend_sequence"] == ["sqlite_fts_index", "local_fooddb_index"]
    assert exact_disabled["websearch_candidate_enabled"] is False
    assert exact_disabled["runtime_truth_source"] == "approved_fooddb_only"


def test_retrieval_eval_wall_ranking_checks_lexical_runtime_and_modifier_features() -> None:
    artifact = build_retrieval_eval_wall(retrieval_records=_records())

    exact = _case_by_id(artifact, "ranking_cases", "alias_exact_ranking_prefers_runtime_anchor")
    fuzzy = _case_by_id(artifact, "ranking_cases", "fuzzy_candidate_requires_manager_disambiguation")
    tea_egg = _case_by_id(
        artifact,
        "ranking_cases",
        "stable_generic_anchor_uses_approved_common_serving",
    )
    kelp = _case_by_id(
        artifact,
        "ranking_cases",
        "listed_component_ranking_prefers_approved_anchor",
    )
    bento = _case_by_id(
        artifact,
        "ranking_cases",
        "generic_meal_modifier_keeps_range_and_followup",
    )

    assert exact["status"] == "pass"
    assert exact["top_candidate"]["anchor_id"] == "custom_drink_boba_milk_tea"
    assert "runtime_truth_allowed" in exact["top_candidate"]["ranking_reasons"]
    assert "modifier_compatible:cup_size" in exact["top_candidate"]["ranking_reasons"]

    assert fuzzy["status"] == "pass"
    assert fuzzy["top_candidate"]["anchor_id"] == "custom_drink_boba_milk_tea"
    assert fuzzy["top_candidate"]["match_path"] == "fuzzy_alias_expansion"
    assert fuzzy["top_candidate"]["requires_manager_disambiguation"] is True

    assert tea_egg["status"] == "pass"
    assert tea_egg["top_candidate"]["anchor_id"] == "single_item_tea_egg"
    assert tea_egg["top_candidate"]["serving_basis"] == "common_serving"
    assert tea_egg["top_candidate"]["requires_manager_disambiguation"] is False

    assert kelp["status"] == "pass"
    assert kelp["top_candidate"]["anchor_id"] == "listed_item_kelp"
    assert kelp["top_candidate"]["runtime_usage_boundary"] == "listed_component_only"

    assert bento["status"] == "pass"
    assert bento["top_candidate"]["anchor_id"] == "generic_meal_chicken_bento"
    assert bento["top_candidate"]["runtime_usage_boundary"] == "generic_range_estimate_only_not_exact"
    assert bento["top_candidate"]["modifier_compatibility"]["rice_portion"] == (
        "compatible_via_normalized_equivalent"
    )
    assert bento["top_candidate"]["followup_hints"]


def test_retrieval_eval_wall_grounding_packets_are_compact_and_read_only() -> None:
    artifact = build_retrieval_eval_wall(retrieval_records=_records())

    fooddb = _case_by_id(artifact, "grounding_cases", "fooddb_packet_is_compact_and_read_only")
    websearch = _case_by_id(artifact, "grounding_cases", "websearch_candidates_remain_candidate_only")
    listed = _case_by_id(
        artifact,
        "grounding_cases",
        "listed_component_packet_keeps_component_boundary",
    )

    assert fooddb["status"] == "pass"
    assert fooddb["packet_projection"]["evidence_item_count"] >= 1
    assert "runtime_mutation" in fooddb["packet_projection"]["manager_must_not_use_for"]

    assert websearch["status"] == "pass"
    assert websearch["classification_counts"]["exact_candidate_for_extract_review"] >= 1
    assert artifact["summary"]["websearch_runtime_truth_allowed_count"] == 0

    assert listed["status"] == "pass"
    assert listed["packet_projection"]["evidence_item_count"] == 3
    assert listed["packet_projection"]["runtime_usage_boundaries"] == ["listed_component_only"]
    assert "runtime_mutation" in listed["packet_projection"]["manager_must_not_use_for"]


def test_retrieval_eval_wall_negative_cases_block_basket_and_exact_candidate_mutation() -> None:
    artifact = build_retrieval_eval_wall(retrieval_records=_records())

    basket = _case_by_id(artifact, "negative_cases", "bare_basket_does_not_estimate")
    exact = _case_by_id(artifact, "negative_cases", "exact_candidates_do_not_mutate")
    listed_unknown = _case_by_id(
        artifact,
        "negative_cases",
        "listed_unknown_component_stays_partial_gap",
    )
    websearch_mismatch = _case_by_id(
        artifact,
        "negative_cases",
        "websearch_mismatch_candidates_do_not_ground_truth",
    )

    assert basket["status"] == "pass"
    assert basket["retrieval_boundary"] == "bare_basket_ask_followup_no_estimate"
    assert exact["status"] == "pass"
    assert exact["exact_card_staging_candidate_count"] == 4
    assert listed_unknown["status"] == "pass"
    assert listed_unknown["accepted_anchor_ids"] == ["listed_item_tofu_dried"]
    assert listed_unknown["rejected_candidates"]
    assert websearch_mismatch["status"] == "pass"
    assert websearch_mismatch["risky_class_counts"]["near_exact_wrong_size_candidate"] >= 1


def test_retrieval_eval_wall_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_retrieval_eval_wall import main

    output = tmp_path / "retrieval_eval_wall.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_retrieval_eval_wall_v1"
    assert artifact["summary"]["fail_count"] == 0
