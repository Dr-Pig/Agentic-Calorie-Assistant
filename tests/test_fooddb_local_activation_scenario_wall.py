from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_activation_wall import build_fooddb_activation_wall
from app.nutrition.application.fooddb_local_activation_scenario_wall import (
    FOODDB_LOCAL_ACTIVATION_SCENARIO_CASES,
    build_fooddb_local_activation_scenario_wall,
)
from app.nutrition.infrastructure.local_food_evidence_index import LocalSmallAnchorFoodEvidenceIndex


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")
TFDA_SOURCE = Path("app/knowledge/tfda_per100g_source_evidence_tw.json")
EXACT_CARDS = Path("app/knowledge/exact_item_cards_tw.json")
ONE_DAY_REGISTER = Path("docs/quality/accurate_intake_one_day_self_use_cases.json")


def _small_anchor_payload() -> dict:
    return json.loads(SMALL_ANCHOR_STORE.read_text(encoding="utf-8-sig"))


def _tfda_source_payload() -> dict:
    return json.loads(TFDA_SOURCE.read_text(encoding="utf-8-sig"))


def _exact_card_payload() -> dict:
    return json.loads(EXACT_CARDS.read_text(encoding="utf-8-sig"))


def _records():
    return LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE).load_records()


def _activation_wall() -> dict:
    return build_fooddb_activation_wall(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
        retrieval_records=_records(),
    )


def _artifact() -> dict:
    return build_fooddb_local_activation_scenario_wall(
        retrieval_records=_records(),
        activation_wall_artifact=_activation_wall(),
    )


def _case_by_id(artifact: dict, turn_id: str) -> dict:
    return {case["turn_id"]: case for case in artifact["cases"]}[turn_id]


def test_local_activation_scenario_wall_uses_repo_tracked_one_day_turn_ids() -> None:
    register = json.loads(ONE_DAY_REGISTER.read_text(encoding="utf-8"))
    expected_turn_ids = [turn["turn_id"] for turn in register["turns"]]

    assert [case.turn_id for case in FOODDB_LOCAL_ACTIVATION_SCENARIO_CASES] == expected_turn_ids


def test_local_activation_scenario_wall_passes_with_real_fooddb_packets_without_readiness_claim() -> None:
    artifact = _artifact()

    assert artifact["artifact_type"] == "accurate_intake_fooddb_local_activation_scenario_wall_v1"
    assert artifact["classification"] == "deterministic_fooddb_local_activation_scenario_wall_only"
    assert artifact["status"] == "pass"
    assert artifact["blockers"] == []
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["packetizer_format_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["runner_inferred_semantics"] is False
    assert artifact["activation_wall_status"] == "pass"
    assert artifact["upstream_next_required_slices"] == ["grokfast_fooddb_packet_live_diagnostic"]
    assert artifact["next_required_slice"] == "grokfast_fooddb_packet_live_diagnostic"
    assert artifact["summary"] == {
        "scenario_turn_count": 9,
        "fooddb_packet_required_turn_count": 6,
        "fooddb_packet_pass_turn_count": 6,
        "no_fooddb_lookup_turn_count": 2,
        "followup_no_mutation_turn_count": 1,
    }


def test_local_activation_scenario_wall_covers_runtime_packet_turns() -> None:
    artifact = _artifact()

    breakfast = _case_by_id(artifact, "breakfast_tea_egg_latte")
    assert breakfast["status"] == "pass"
    assert breakfast["packet_posture"] == "fooddb_packet_required"
    assert _actual_anchor_ids(breakfast) == ["custom_drink_latte", "single_item_tea_egg"]

    bento = _case_by_id(artifact, "lunch_chicken_bento")
    assert _actual_anchor_ids(bento) == ["generic_meal_chicken_bento"]

    boba = _case_by_id(artifact, "bubble_tea_half_sugar_large_refinement")
    assert _actual_anchor_ids(boba) == ["custom_drink_boba_milk_tea"]
    assert _modifier_compatibility(boba) == {
        "cup_size": "compatible",
        "sugar_level": "compatible",
    }

    rice = _case_by_id(artifact, "lunch_rice_less_correction")
    assert _actual_anchor_ids(rice) == ["generic_meal_chicken_bento"]
    assert _modifier_compatibility(rice) == {
        "rice_portion": "compatible_via_normalized_equivalent"
    }


def test_local_activation_scenario_wall_preserves_basket_target_and_query_boundaries() -> None:
    artifact = _artifact()

    bare = _case_by_id(artifact, "dinner_luwei_bare_draft")
    assert bare["packet_posture"] == "followup_no_mutation_no_fooddb_estimate"
    assert bare["evidence_queries"][0]["retrieval_boundary"] == "bare_basket_ask_followup_no_estimate"
    packet = bare["evidence_queries"][0]["manager_evidence_packet"]
    assert packet["evidence_items"] == []
    assert packet["runtime_mutation_allowed"] is False
    assert packet["followup_hints"]

    listed = _case_by_id(artifact, "dinner_luwei_listed_commit")
    assert listed["evidence_queries"][0]["retrieval_boundary"] == "listed_basket_component_recall"
    assert _actual_anchor_ids(listed) == [
        "listed_item_kelp",
        "listed_item_meatball",
        "listed_item_tofu_dried",
    ]

    removal = _case_by_id(artifact, "dinner_remove_gongwan")
    assert removal["packet_posture"] == "target_evidence_only_no_fooddb_lookup"
    assert removal["evidence_queries"] == []

    query = _case_by_id(artifact, "today_consumed_remaining_query")
    assert query["packet_posture"] == "read_only_query_no_fooddb_lookup"
    assert query["evidence_queries"] == []


def test_local_activation_scenario_wall_fails_closed_when_required_runtime_anchor_missing() -> None:
    payload = _small_anchor_payload()
    for anchor in payload["anchors"]:
        if anchor.get("anchor_id") == "custom_drink_latte":
            anchor["runtime_truth_allowed"] = False

    artifact = build_fooddb_local_activation_scenario_wall(
        retrieval_records=LocalSmallAnchorFoodEvidenceIndex(payload).load_records(),
        activation_wall_artifact={"artifact_type": "accurate_intake_fooddb_activation_wall_v1", "status": "pass"},
    )

    assert artifact["status"] == "blocked"
    assert "breakfast_tea_egg_latte:required_runtime_anchor_ids_present" in artifact["blockers"]
    assert artifact["next_required_slice"] == "inspect_fooddb_local_activation_scenario_wall_blockers"


def test_local_activation_scenario_wall_requires_upstream_activation_wall_artifact() -> None:
    artifact = build_fooddb_local_activation_scenario_wall(
        retrieval_records=_records(),
        activation_wall_artifact=None,
    )

    assert artifact["status"] == "blocked"
    assert "activation_wall_status:not_provided" in artifact["blockers"]
    assert artifact["upstream_next_required_slices"] == ["not_provided"]
    assert artifact["next_required_slice"] == "build_fooddb_activation_wall_first"


def test_local_activation_scenario_wall_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_fooddb_local_activation_scenario_wall import main

    activation_wall_path = tmp_path / "activation_wall.json"
    output = tmp_path / "scenario_wall.json"
    write_json_artifact(activation_wall_path, _activation_wall())

    assert main(["--activation-wall", str(activation_wall_path), "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_fooddb_local_activation_scenario_wall_v1"
    assert artifact["status"] == "pass"


def _actual_anchor_ids(case: dict) -> list[str]:
    return sorted(
        {
            item["anchor_id"]
            for query in case["evidence_queries"]
            for item in query["manager_evidence_packet"]["evidence_items"]
        }
    )


def _modifier_compatibility(case: dict) -> dict[str, str]:
    combined = {}
    for query in case["evidence_queries"]:
        for item in query["manager_evidence_packet"]["evidence_items"]:
            combined.update(item["modifier_compatibility"])
    return combined
