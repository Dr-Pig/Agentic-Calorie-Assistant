from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_activation_wall import build_fooddb_activation_wall
from app.nutrition.infrastructure.local_food_evidence_index import LocalSmallAnchorFoodEvidenceIndex


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")
TFDA_SOURCE = Path("app/knowledge/tfda_per100g_source_evidence_tw.json")
EXACT_CARDS = Path("app/knowledge/exact_item_cards_tw.json")


def _small_anchor_payload() -> dict:
    return json.loads(SMALL_ANCHOR_STORE.read_text(encoding="utf-8-sig"))


def _tfda_source_payload() -> dict:
    return json.loads(TFDA_SOURCE.read_text(encoding="utf-8-sig"))


def _exact_card_payload() -> dict:
    return json.loads(EXACT_CARDS.read_text(encoding="utf-8-sig"))


def _retrieval_records():
    return LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE).load_records()


def _artifact() -> dict:
    return build_fooddb_activation_wall(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
        retrieval_records=_retrieval_records(),
    )


def _check_by_id(artifact: dict, check_id: str) -> dict:
    return {check["check_id"]: check for check in artifact["checks"]}[check_id]


def test_fooddb_activation_wall_passes_current_minimum_without_runtime_change() -> None:
    artifact = _artifact()

    assert artifact["artifact_type"] == "accurate_intake_fooddb_activation_wall_v1"
    assert artifact["classification"] == "deterministic_fooddb_activation_wall_only"
    assert artifact["status"] == "pass"
    assert artifact["blockers"] == []
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["packetizer_format_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["next_required_slice"] == "grokfast_fooddb_packet_live_diagnostic"

    assert artifact["summary"] == {
        "runtime_common_serving_anchor_count": 51,
        "listed_component_anchor_count": 30,
        "p0_modifier_count": 3,
        "p0_supported_modifier_count": 3,
        "packet_case_count": 5,
        "manager_packet_check_pass_count": 6,
        "upstream_next_required_slice_count": 1,
    }
    assert artifact["upstream_next_required_slices"] == ["grokfast_fooddb_packet_live_diagnostic"]
    assert artifact["next_required_slice"] == "grokfast_fooddb_packet_live_diagnostic"


def test_fooddb_activation_wall_checks_p0_modifier_and_packet_boundaries() -> None:
    artifact = _artifact()

    for check in artifact["checks"]:
        assert check["status"] == "pass"

    assert _check_by_id(artifact, "p0_modifier_supported:cup_size")["details"]["anchor_count"] == 6
    assert _check_by_id(artifact, "p0_modifier_supported:rice_portion")["details"]["anchor_count"] == 2
    assert _check_by_id(artifact, "p0_modifier_supported:sugar_level")["details"]["anchor_count"] == 3

    boba = _check_by_id(artifact, "boba_packet_has_p0_modifier_compatibility")
    assert boba["details"]["modifier_hints"] == {
        "cup_size": "large",
        "sugar_level": "half_sugar",
    }
    assert boba["details"]["evidence_modifier_compatibility"] == [
        {"cup_size": "compatible", "sugar_level": "compatible"}
    ]

    bento = _check_by_id(artifact, "bento_packet_has_rice_modifier_compatibility")
    assert bento["details"]["modifier_hints"] == {"rice_portion": "less_rice"}
    assert bento["details"]["evidence_modifier_compatibility"] == [
        {"rice_portion": "compatible_via_normalized_equivalent"}
    ]


def test_fooddb_activation_wall_preserves_basket_and_typo_manager_boundaries() -> None:
    artifact = _artifact()

    bare = _check_by_id(artifact, "bare_basket_packet_asks_followup_without_evidence")
    assert bare["details"]["retrieval_boundary"] == "bare_basket_ask_followup_no_estimate"
    assert bare["details"]["runtime_mutation_allowed"] is False
    assert bare["details"]["evidence_item_count"] == 0
    assert bare["details"]["followup_hints"]

    listed = _check_by_id(artifact, "listed_basket_packet_uses_approved_components_only")
    assert listed["details"]["retrieval_boundary"] == "listed_basket_component_recall"
    assert listed["details"]["evidence_anchor_ids"] == [
        "listed_item_kelp",
        "listed_item_meatball",
        "listed_item_tofu_dried",
    ]

    typo = _check_by_id(artifact, "typo_packet_requires_manager_disambiguation")
    assert typo["details"]["retrieval_boundary"] == "single_or_composite_candidate_recall"
    assert typo["details"]["truth_selection_forbidden"] is True


def test_fooddb_activation_wall_fails_closed_when_p0_modifier_packet_is_not_supported() -> None:
    payload = _small_anchor_payload()
    for anchor in payload["anchors"]:
        if anchor.get("anchor_id") == "generic_meal_chicken_bento":
            anchor["major_modifiers"] = [
                modifier
                for modifier in anchor.get("major_modifiers") or []
                if modifier.get("name") != "rice_portion"
            ]

    artifact = build_fooddb_activation_wall(
        small_anchor_payload=payload,
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
        retrieval_records=LocalSmallAnchorFoodEvidenceIndex(payload).load_records(),
    )

    assert artifact["status"] == "blocked"
    assert "bento_packet_has_rice_modifier_compatibility" in artifact["blockers"]
    assert artifact["next_required_slice"] == "inspect_fooddb_activation_wall_blockers"


def test_fooddb_activation_wall_preserves_upstream_status_packet_next_step_without_local_blocker() -> None:
    payload = _small_anchor_payload()

    artifact = build_fooddb_activation_wall(
        small_anchor_payload=payload,
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
        retrieval_records=LocalSmallAnchorFoodEvidenceIndex(payload).load_records(),
    )

    assert artifact["status"] == "pass"
    assert artifact["blockers"] == []
    assert artifact["upstream_next_required_slices"] == ["grokfast_fooddb_packet_live_diagnostic"]
    assert artifact["next_required_slice"] == "grokfast_fooddb_packet_live_diagnostic"


def test_fooddb_activation_wall_preserves_websearch_upstream_next_step_without_over_advance(
    monkeypatch,
) -> None:
    from app.nutrition.application import fooddb_activation_wall

    def fake_status_packet(**_kwargs):
        return {
            "summary": {
                "runtime_common_serving_anchor_count": 51,
                "listed_component_anchor_count": 30,
                "source_evidence_only_count": 848,
            },
            "activation_thresholds": {
                "minimum_common_serving_anchors": 40,
                "minimum_listed_component_anchors": 30,
                "meets_common_serving_anchor_minimum": True,
                "meets_listed_component_minimum": True,
            },
            "fooddb_status": {"runtime_anchor_catalog_included": False},
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        }

    monkeypatch.setattr(fooddb_activation_wall, "build_fooddb_evidence_status_packet", fake_status_packet)
    artifact = build_fooddb_activation_wall(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
        retrieval_records=_retrieval_records(),
    )

    assert artifact["status"] == "pass"
    assert artifact["upstream_next_required_slices"] == ["grokfast_websearch_packet_live_diagnostic"]
    assert artifact["next_required_slice"] == "grokfast_websearch_packet_live_diagnostic"


def test_fooddb_activation_wall_allows_sanitized_modifier_catalog_without_structural_leak() -> None:
    payload = _small_anchor_payload()
    for anchor in payload["anchors"]:
        if anchor.get("anchor_id") == "custom_drink_boba_milk_tea":
            anchor["major_modifiers"][0]["raw_source_rows"] = [{"leak": True}]
            anchor["major_modifiers"][0]["candidate_records"] = [{"leak": True}]

    artifact = build_fooddb_activation_wall(
        small_anchor_payload=payload,
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
        retrieval_records=LocalSmallAnchorFoodEvidenceIndex(payload).load_records(),
    )

    assert artifact["status"] == "pass"
    assert "modifier_catalog_compact_runtime_only" not in artifact["blockers"]
    modifier_check = _check_by_id(artifact, "modifier_catalog_compact_runtime_only")
    assert "raw_source_rows" not in json.dumps(modifier_check["details"]["anchors"])
    assert "candidate_records" not in json.dumps(modifier_check["details"]["anchors"])


def test_fooddb_activation_wall_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_activation_wall import main

    output = tmp_path / "activation_wall.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_fooddb_activation_wall_v1"
    assert artifact["status"] == "pass"
