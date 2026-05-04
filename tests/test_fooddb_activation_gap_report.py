from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_modifier_priority import (
    build_modifier_activation_posture,
    build_modifier_limitation_labels,
)
from app.nutrition.application.fooddb_activation_gap_report import (
    build_fooddb_activation_gap_report,
)


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def _tfda_source_payload() -> dict:
    return json.loads(
        Path("app/knowledge/tfda_per100g_source_evidence_tw.json").read_text(encoding="utf-8-sig")
    )


def _exact_card_payload() -> dict:
    return json.loads(Path("app/knowledge/exact_item_cards_tw.json").read_text(encoding="utf-8-sig"))


def test_fooddb_activation_gap_report_reports_repo_truth_controls_without_runtime_change() -> None:
    report = build_fooddb_activation_gap_report(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
    )

    assert report["artifact_type"] == "accurate_intake_fooddb_activation_gap_report"
    assert report["generated_at_utc"] is None
    assert report["runtime_truth_changed"] is False
    assert report["claim_scope"] == "fooddb_activation_gap_report_only"
    assert report["summary"] == {
        "runtime_visible_common_serving_anchor_count": 40,
        "source_evidence_only_count": 848,
        "semantic_only_basket_family_count": 4,
        "listed_component_anchor_count": 19,
        "exact_candidate_only_posture": "candidate_only",
    }

    gap = report["activation_gap_report"]
    assert sorted(gap["known_unsupported_food_families"]) == sorted(
        [
        "\u6ef7\u5473",
        "\u9ebb\u8fa3\u71d9",
        "\u9e7d\u9165\u96de",
        "\u5bb6\u5e38\u83dc",
        ]
    )
    assert gap["known_ask_followup_cases"] == [
        "bare_basket_followup",
        "listed_basket_component_followup",
        "portion_refinement",
    ]
    assert sorted(gap["known_candidate_only_exact_cases"]) == sorted(
        [
        "exact_unified_chocolate_milk_400ml",
        "exact_starbucks_latte_iced_large",
        "exact_starbucks_latte_hot_medium",
        "exact_sushiro_caramel_fish_two_piece",
        "exact_matsuya_tokumori_gyudon",
        ]
    )
    assert gap["known_modifier_limitations"] == build_modifier_limitation_labels()
    assert gap["modifier_activation_posture"] == build_modifier_activation_posture()
    assert gap["known_basket_limitations"] == [
        "bare_basket:ask_followup_no_estimate",
        "listed_basket:estimate_component_anchors_only",
    ]
    assert report["activation_can_proceed_with_known_bounded_gaps"] is True
    assert "known bounded gaps" in report["activation_gap_note"]
    assert report["non_claims"] == [
        "no_product_loop_integration",
        "no_manager_context_change",
        "no_packetizer_format_change",
        "no_live_provider_call",
        "no_readiness_claim",
    ]


def test_fooddb_activation_gap_report_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    output = tmp_path / "activation_gap_report.json"

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_activation_gap_report import main

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["summary"]["listed_component_anchor_count"] == 19
    assert artifact["activation_can_proceed_with_known_bounded_gaps"] is True
