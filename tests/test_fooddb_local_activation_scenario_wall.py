from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_activation_wall import (
    build_fooddb_activation_wall,
)
from app.nutrition.application.fooddb_local_activation_scenario_wall import (
    build_fooddb_local_activation_scenario_wall,
)
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")
TFDA_SOURCE = Path("app/knowledge/tfda_per100g_source_evidence_tw.json")
EXACT_CARDS = Path("app/knowledge/exact_item_cards_tw.json")
DEFAULT_ACTIVATION_WALL = object()


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _records(payload: dict | None = None):
    if payload is not None:
        return LocalSmallAnchorFoodEvidenceIndex(payload).load_records()
    return LocalSmallAnchorFoodEvidenceIndex.from_path(
        SMALL_ANCHOR_STORE
    ).load_records()


def _activation_wall(payload: dict | None = None) -> dict:
    payload = payload or _json(SMALL_ANCHOR_STORE)
    return build_fooddb_activation_wall(
        small_anchor_payload=payload,
        tfda_source_payload=_json(TFDA_SOURCE),
        exact_card_payload=_json(EXACT_CARDS),
        retrieval_records=_records(payload),
    )


def _artifact(
    payload: dict | None = None, activation_wall: object = DEFAULT_ACTIVATION_WALL
) -> dict:
    return build_fooddb_local_activation_scenario_wall(
        retrieval_records=_records(payload),
        activation_wall_artifact=_activation_wall(payload)
        if activation_wall is DEFAULT_ACTIVATION_WALL
        else activation_wall,
    )


def _case(artifact: dict, turn_id: str) -> dict:
    return {case["turn_id"]: case for case in artifact["cases"]}[turn_id]


def _anchor_ids(case: dict) -> list[str]:
    return sorted(
        item["anchor_id"]
        for query in case["evidence_queries"]
        for item in query["manager_evidence_packet"]["evidence_items"]
    )


def _modifier_compatibility(case: dict) -> dict[str, str]:
    combined = {}
    for query in case["evidence_queries"]:
        for item in query["manager_evidence_packet"]["evidence_items"]:
            combined.update(item["modifier_compatibility"])
    return combined


def test_local_activation_scenario_wall_passes_without_runtime_or_readiness_claim() -> (
    None
):
    artifact = _artifact()

    assert (
        artifact["artifact_type"]
        == "accurate_intake_fooddb_local_activation_scenario_wall_v1"
    )
    assert artifact["status"] == "pass"
    assert artifact["blockers"] == []
    assert artifact["summary"] == {
        "scenario_turn_count": 9,
        "fooddb_packet_required_turn_count": 6,
        "fooddb_packet_pass_turn_count": 6,
        "no_fooddb_lookup_turn_count": 2,
        "followup_no_mutation_turn_count": 1,
    }
    assert artifact["activation_wall_status"] == "pass"
    assert artifact["next_required_slice"] == "grokfast_fooddb_packet_live_diagnostic"
    assert all(
        artifact[key] is False
        for key in (
            "runtime_truth_changed",
            "mutation_changed",
            "manager_context_changed",
            "packetizer_format_changed",
            "live_provider_used",
            "live_websearch_used",
            "readiness_claimed",
            "runner_inferred_semantics",
        )
    )


def test_local_activation_scenario_wall_covers_packet_and_basket_boundaries() -> None:
    artifact = _artifact()

    for turn_id, expected in {
        "breakfast_tea_egg_latte": ["custom_drink_latte", "single_item_tea_egg"],
        "lunch_chicken_bento": ["generic_meal_chicken_bento"],
    }.items():
        assert _anchor_ids(_case(artifact, turn_id)) == expected
    assert _modifier_compatibility(_case(artifact, "lunch_rice_less_correction")) == {
        "rice_portion": "compatible_via_normalized_equivalent"
    }

    bare = _case(artifact, "dinner_luwei_bare_draft")
    bare_packet = bare["evidence_queries"][0]["manager_evidence_packet"]
    assert (
        bare["evidence_queries"][0]["retrieval_boundary"]
        == "bare_basket_ask_followup_no_estimate"
    )
    assert bare_packet["evidence_items"] == []
    assert bare_packet["runtime_mutation_allowed"] is False
    assert bare_packet["followup_hints"]

    listed = _case(artifact, "dinner_luwei_listed_commit")
    assert _anchor_ids(listed) == [
        "listed_item_kelp",
        "listed_item_meatball",
        "listed_item_tofu_dried",
    ]
    assert _case(artifact, "dinner_remove_gongwan")["evidence_queries"] == []


def test_local_activation_scenario_wall_fails_closed_for_missing_anchor_or_upstream_wall() -> (
    None
):
    payload = _json(SMALL_ANCHOR_STORE)
    for anchor in payload["anchors"]:
        if anchor.get("anchor_id") == "custom_drink_latte":
            anchor["runtime_truth_allowed"] = False

    missing_anchor = _artifact(
        payload,
        activation_wall={
            "artifact_type": "accurate_intake_fooddb_activation_wall_v1",
            "status": "pass",
        },
    )
    assert missing_anchor["status"] == "blocked"
    assert (
        "breakfast_tea_egg_latte:required_runtime_anchor_ids_present"
        in missing_anchor["blockers"]
    )
    assert (
        missing_anchor["next_required_slice"]
        == "inspect_fooddb_local_activation_scenario_wall_blockers"
    )

    missing_wall = _artifact(activation_wall=None)
    assert missing_wall["status"] == "blocked"
    assert "activation_wall_status:not_provided" in missing_wall["blockers"]
    assert missing_wall["upstream_next_required_slices"] == ["not_provided"]
    assert missing_wall["next_required_slice"] == "build_fooddb_activation_wall_first"
