from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_listed_component_expansion_plan import (
    LISTED_COMPONENT_TARGETS,
    build_listed_component_expansion_plan,
)


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def _tfda_source_payload() -> dict:
    return json.loads(
        Path("app/knowledge/tfda_per100g_source_evidence_tw.json").read_text(encoding="utf-8-sig")
    )


def test_listed_component_expansion_plan_reports_runtime_source_backed_and_missing_states() -> None:
    artifact = build_listed_component_expansion_plan(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
    )

    assert artifact["artifact_type"] == "accurate_intake_fooddb_listed_component_expansion_plan"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["packetizer_format_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["summary"] == {
        "target_component_count": len(LISTED_COMPONENT_TARGETS),
        "runtime_visible_count": 16,
        "source_backed_not_runtime_count": 2,
        "source_missing_count": 7,
    }


def test_listed_component_expansion_plan_uses_safe_exact_alias_matching() -> None:
    artifact = build_listed_component_expansion_plan(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
    )
    by_label = {entry["component_label"]: entry for entry in artifact["targets"]}

    assert by_label["豆皮"]["status"] == "runtime_visible_existing_anchor"
    assert by_label["豆皮"]["runtime_anchor_id"] == "listed_item_tofu_skin"
    assert by_label["粉絲"]["status"] == "runtime_visible_existing_anchor"
    assert by_label["粉絲"]["runtime_anchor_id"] == "listed_item_glass_noodles"

    assert by_label["魚板"]["status"] == "source_evidence_match_available_not_runtime"
    assert by_label["魚板"]["source_evidence_match"]["canonical_name"] == "魚板"
    assert by_label["魚板"]["recommended_next_action"] == "add_small_anchor_then_selected_promotion"

    assert by_label["蟹肉棒"]["status"] == "source_evidence_match_available_not_runtime"
    assert by_label["蟹肉棒"]["source_evidence_match"]["alias_matched"] == "蟹肉棒"

    assert by_label["白蘿蔔"]["status"] == "source_evidence_missing"
    assert by_label["白蘿蔔"]["source_evidence_match"] is None
    assert by_label["白蘿蔔"]["recommended_next_action"] == "require_new_source_or_alias_strategy"


def test_listed_component_expansion_plan_next_batch_recommendation_is_narrow() -> None:
    artifact = build_listed_component_expansion_plan(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
    )

    recommendation = artifact["next_batch_recommendation"]
    assert recommendation["max_new_runtime_anchors_before_activation"] == 12
    assert set(recommendation["candidate_labels"]) == {"魚板", "蟹肉棒"}
    assert {"油豆腐", "白蘿蔔", "金針菇", "凍豆腐", "玉米筍", "花椰菜", "魚豆腐"} == set(
        recommendation["blocked_labels"]
    )


def test_listed_component_expansion_plan_non_claims_stay_report_only() -> None:
    artifact = build_listed_component_expansion_plan(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
    )

    assert artifact["match_policy"] == {
        "source_evidence_matching": "normalized_exact_alias_only",
        "substring_matching_allowed": False,
        "false_positive_guard_examples": ["白蘿蔔 != 胡蘿蔔素", "白蘿蔔 != 蘿蔔糕"],
    }
    assert artifact["non_claims"] == [
        "no_runtime_truth_promotion",
        "no_live_provider_call",
        "no_manager_context_change",
        "no_packetizer_format_change",
    ]
