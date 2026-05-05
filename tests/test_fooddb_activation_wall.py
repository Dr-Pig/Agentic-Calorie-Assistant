from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_activation_wall import build_fooddb_activation_wall
from app.nutrition.infrastructure.local_food_evidence_index import LocalSmallAnchorFoodEvidenceIndex


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")
TFDA_SOURCE = Path("app/knowledge/tfda_per100g_source_evidence_tw.json")
EXACT_CARDS = Path("app/knowledge/exact_item_cards_tw.json")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _records(payload: dict | None = None):
    if payload is not None:
        return LocalSmallAnchorFoodEvidenceIndex(payload).load_records()
    return LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE).load_records()


def _artifact(small_anchor_payload: dict | None = None, **status_patch) -> dict:
    payload = small_anchor_payload or _json(SMALL_ANCHOR_STORE)
    return build_fooddb_activation_wall(
        small_anchor_payload=payload,
        tfda_source_payload=_json(TFDA_SOURCE),
        exact_card_payload=_json(EXACT_CARDS),
        retrieval_records=_records(payload),
        **status_patch,
    )


def _checks(artifact: dict) -> dict[str, dict]:
    return {check["check_id"]: check for check in artifact["checks"]}


def test_fooddb_activation_wall_passes_without_runtime_or_readiness_claim() -> None:
    artifact = _artifact()
    checks = _checks(artifact)

    assert artifact["artifact_type"] == "accurate_intake_fooddb_activation_wall_v1"
    assert artifact["classification"] == "deterministic_fooddb_activation_wall_only"
    assert artifact["status"] == "pass"
    assert artifact["blockers"] == []
    assert artifact["next_required_slice"] == "grokfast_fooddb_packet_live_diagnostic"
    assert artifact["upstream_next_required_slices"] == ["grokfast_fooddb_packet_live_diagnostic"]
    assert all(artifact[key] is False for key in (
        "runtime_truth_changed",
        "mutation_changed",
        "manager_context_changed",
        "packetizer_format_changed",
        "live_provider_used",
        "live_websearch_used",
        "readiness_claimed",
    ))
    assert artifact["summary"] == {
        "runtime_common_serving_anchor_count": 51,
        "listed_component_anchor_count": 30,
        "p0_modifier_count": 3,
        "p0_supported_modifier_count": 3,
        "packet_case_count": 5,
        "manager_packet_check_pass_count": 6,
        "upstream_next_required_slice_count": 1,
    }
    assert all(check["status"] == "pass" for check in checks.values())


def test_fooddb_activation_wall_checks_packet_boundaries_and_modifiers() -> None:
    checks = _checks(_artifact())

    assert checks["p0_modifier_supported:cup_size"]["details"]["anchor_count"] == 6
    assert checks["p0_modifier_supported:rice_portion"]["details"]["anchor_count"] == 2
    assert checks["p0_modifier_supported:sugar_level"]["details"]["anchor_count"] == 3
    assert checks["boba_packet_has_p0_modifier_compatibility"]["details"][
        "evidence_modifier_compatibility"
    ] == [{"cup_size": "compatible", "sugar_level": "compatible"}]
    assert checks["bento_packet_has_rice_modifier_compatibility"]["details"][
        "evidence_modifier_compatibility"
    ] == [{"rice_portion": "compatible_via_normalized_equivalent"}]
    assert checks["bare_basket_packet_asks_followup_without_evidence"]["details"][
        "retrieval_boundary"
    ] == "bare_basket_ask_followup_no_estimate"
    assert checks["bare_basket_packet_asks_followup_without_evidence"]["details"][
        "evidence_item_count"
    ] == 0
    assert checks["listed_basket_packet_uses_approved_components_only"]["details"][
        "evidence_anchor_ids"
    ] == ["listed_item_kelp", "listed_item_meatball", "listed_item_tofu_dried"]
    assert checks["typo_packet_requires_manager_disambiguation"]["details"][
        "truth_selection_forbidden"
    ] is True


def test_fooddb_activation_wall_fails_closed_when_p0_modifier_packet_is_not_supported() -> None:
    payload = _json(SMALL_ANCHOR_STORE)
    for anchor in payload["anchors"]:
        if anchor.get("anchor_id") == "generic_meal_chicken_bento":
            anchor["major_modifiers"] = [
                modifier
                for modifier in anchor.get("major_modifiers") or []
                if modifier.get("name") != "rice_portion"
            ]

    artifact = _artifact(payload)

    assert artifact["status"] == "blocked"
    assert "bento_packet_has_rice_modifier_compatibility" in artifact["blockers"]
    assert artifact["next_required_slice"] == "inspect_fooddb_activation_wall_blockers"


def test_fooddb_activation_wall_preserves_websearch_upstream_next_step(monkeypatch) -> None:
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
    artifact = _artifact()

    assert artifact["status"] == "pass"
    assert artifact["next_required_slice"] == "grokfast_websearch_packet_live_diagnostic"


def test_fooddb_activation_wall_blocks_structural_modifier_catalog_leak() -> None:
    payload = _json(SMALL_ANCHOR_STORE)
    for anchor in payload["anchors"]:
        if anchor.get("anchor_id") == "custom_drink_boba_milk_tea":
            anchor["major_modifiers"][0]["raw_source_rows"] = [{"leak": True}]
            anchor["major_modifiers"][0]["candidate_records"] = [{"leak": True}]

    modifier_check = _checks(_artifact(payload))["modifier_catalog_compact_runtime_only"]

    assert "raw_source_rows" not in json.dumps(modifier_check["details"]["anchors"])
    assert "candidate_records" not in json.dumps(modifier_check["details"]["anchors"])
