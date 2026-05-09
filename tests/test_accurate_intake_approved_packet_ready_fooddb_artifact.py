from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from scripts.build_accurate_intake_product_loop_handoff_v3 import (
    build_product_loop_handoff_v3,
)


def _macro_complete_card(**overrides: object) -> dict[str, object]:
    card = {
        "item_id": "exact_test_chocolate_milk_400ml",
        "title": "Test Chocolate Milk 400ml",
        "aliases": ["Test Chocolate Milk 400ml"],
        "brand": "Test Brand",
        "serving_basis": "400ml",
        "kcal": 300,
        "protein_g": 12,
        "carb_g": 48,
        "fat_g": 6,
        "macro_basis": "per_package",
        "macro_confidence": "high",
        "macro_source_strength": "exact_item_seed",
        "kcal_band": "per_package",
    }
    card.update(overrides)
    return card


def _product_loop_evidence() -> dict[str, object]:
    return {
        "browser_shell_smoke": {"status": "pass", "browser_executed": True},
        "local_web_candidate": {
            "local_web_self_use_candidate_v2": {
                "candidate_prepared": True,
                "blockers": [],
                "appshell_browser_evidence_chain": {
                    "browser_artifact_count": 6,
                    "browser_executed_count": 6,
                    "all_required_browser_artifacts_executed": True,
                    "product_pages_self_use_flow_checked": True,
                    "today_macro_runtime_mirror_checked": True,
                    "renderer_source_closure_checked": True,
                    "context_target_browser_closure_checked": True,
                    "body_noplan_degraded_checked": True,
                    "live_llm_invoked": False,
                    "fooddb_evidence_used": False,
                    "websearch_evidence_used": False,
                    "runtime_truth_changed": False,
                    "mutation_changed": False,
                    "frontend_semantic_owner": False,
                },
            }
        },
        "browser_fixture_dogfood": {
            "status": "browser_fixture_pass",
            "fixture_evidence_used": True,
            "real_fooddb_pass_claimed": False,
        },
        "local_dogfood_hygiene": {"status": "pass"},
        "browser_realistic_dogfood": {
            "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
            "fixture_evidence_used": True,
            "real_fooddb_pass_claimed": False,
        },
        "operator_review": {
            "status": "browser_diagnostic_review_with_fixture_evidence_gap",
            "real_fooddb_pass_claimed": False,
        },
        "mvp_gate": {"status": "pass"},
    }


def test_build_approved_packet_ready_artifact_uses_macro_complete_exact_card() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        exact_item_cards=[_macro_complete_card()],
        artifact_path="artifacts/approved_packet_ready_fooddb_min1.json",
    )

    metadata = artifact["approved_packet_ready_evidence_artifact"]
    assert artifact["artifact_type"] == "accurate_intake_approved_packet_ready_fooddb_artifact"
    assert artifact["producer_track"] == "FoodDB"
    assert artifact["fixture_or_real"] == "real"
    assert artifact["ready_for_other_tracks"] is True
    assert metadata["fixture_or_real"] == "real"
    assert metadata["source_quality"] == "packet_ready_approved"
    assert metadata["ready_for_product_loop"] is True
    macro_contract = metadata["macro_contract"]
    assert macro_contract["packet_fields"] == [
        "protein_g",
        "carbs_g",
        "fat_g",
        "macro_visibility_status",
        "macro_source_basis",
        "macro_confidence",
    ]
    assert macro_contract["macro_truth_owner"] == "fooddb_approved_packet"
    assert macro_contract["missing_macro_policy"] == "preserve_null_do_not_invent"
    assert macro_contract["macro_runtime_policy"] == {
        "calorie_first": True,
        "macro_aware": True,
        "missing_macro_blocks_kcal_logging": False,
        "manager_may_infer_macro_from_food_name": False,
    }
    source_policy = macro_contract["source_class_policy"]
    assert source_policy["exact_brand_item"]["macro_truth_allowed"] is True
    assert source_policy["generic_common_serving"]["allowed_macro_values"] == [
        "point",
        "range",
        "null_unknown",
    ]
    assert source_policy["listed_component"]["preferred_macro_granularity"] == "per_unit"
    assert source_policy["basket_family_alias_modifier"]["macro_truth_allowed"] is False
    assert source_policy["source_evidence_candidate"]["macro_truth_allowed"] is False
    assert source_policy["source_evidence_candidate"]["source_classes"] == [
        "TFDA_per_100g",
        "USDA",
        "OpenFoodFacts",
        "WebSearch",
    ]

    item = artifact["packet_ready_items"][0]
    assert item["source_lane"] == "exact_item_card"
    assert item["runtime_truth_allowed"] is True
    assert item["kcal_point"] == 300
    assert item["protein_g"] == 12
    assert item["carbs_g"] == 48
    assert item["fat_g"] == 6
    assert item["macro_visibility_status"] == "visible"
    assert item["macro_source_basis"] == "exact_item_seed_label"
    assert item["macro_confidence"] == "high"


def test_build_approved_packet_ready_artifact_blocks_without_macro_complete_card() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        exact_item_cards=[_macro_complete_card(protein_g=0, carb_g=0, fat_g=0)],
        artifact_path="artifacts/approved_packet_ready_fooddb_min1.json",
    )

    metadata = artifact["approved_packet_ready_evidence_artifact"]
    assert artifact["status"] == "blocked_no_macro_complete_exact_item"
    assert artifact["ready_for_other_tracks"] is False
    assert metadata["fixture_or_real"] == "real"
    assert metadata["ready_for_product_loop"] is False
    assert artifact["packet_ready_items"] == []
    assert "no_macro_complete_exact_item_card" in artifact["blockers"]


def test_default_repo_artifact_builds_from_tracked_exact_item_seed() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_min1.json",
    )

    assert artifact["status"] == "approved_packet_ready_fooddb_artifact_ready"
    assert artifact["ready_for_other_tracks"] is True
    assert artifact["summary"]["source_file"] == "app/knowledge/exact_item_cards_tw.json"
    assert artifact["summary"]["packet_ready_item_count"] == 1
    assert artifact["packet_ready_items"][0]["macro_visibility_status"] == "visible"


def test_artifact_is_accepted_by_product_loop_handoff_validation_only() -> None:
    fooddb_artifact = build_approved_packet_ready_fooddb_artifact(
        exact_item_cards=[_macro_complete_card()],
        artifact_path="artifacts/approved_packet_ready_fooddb_min1.json",
    )

    handoff = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact=fooddb_artifact,
    )

    assert handoff["status"] == "product_loop_handoff_ready_for_fdb_integration_validation"
    assert handoff["ready_for_fdb_integration"] is True
    assert handoff["fooddb_validation"]["metadata"]["macro_contract"][
        "missing_macro_policy"
    ] == "preserve_null_do_not_invent"
    assert handoff["fooddb_evidence_used"] is False
    assert handoff["real_fooddb_pass_claimed"] is False
    assert handoff["dogfood_pass"] is False


def test_approved_packet_ready_fooddb_artifact_cli_writes_json(tmp_path: Path) -> None:
    cards_path = tmp_path / "exact_item_cards.json"
    output_path = tmp_path / "approved_packet_ready_fooddb.json"
    cards_path.write_text(
        json.dumps({"cards": [_macro_complete_card()]}, ensure_ascii=False),
        encoding="utf-8",
    )

    from scripts.build_accurate_intake_approved_packet_ready_fooddb_artifact import main

    exit_code = main(
        [
            "--exact-item-cards",
            str(cards_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "approved_packet_ready_fooddb_artifact_ready"
    assert artifact["approved_packet_ready_evidence_artifact"]["path"] == str(output_path)


def test_runbook_documents_minimal_fooddb_packet_ready_artifact() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md").read_text(
        encoding="utf-8-sig"
    )

    assert "build_accurate_intake_approved_packet_ready_fooddb_artifact.py" in runbook
    assert "--fooddb-artifact artifacts/accurate_intake_approved_packet_ready_fooddb_artifact.json" in runbook
