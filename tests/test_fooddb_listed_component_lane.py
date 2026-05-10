from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_retrieval_policy import retrieve_fooddb_candidates
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def _payload() -> dict:
    return json.loads(SMALL_ANCHOR_STORE.read_text(encoding="utf-8-sig"))


def _anchors() -> dict[str, dict]:
    return {
        str(anchor["anchor_id"]): dict(anchor)
        for anchor in _payload()["anchors"]
        if isinstance(anchor, dict) and anchor.get("anchor_id")
    }


def test_listed_component_lane_adds_tfda_backed_runtime_components() -> None:
    anchors = _anchors()
    expected = {
        "listed_item_soft_tofu": ("\u5ae9\u8c46\u8150", 51, [39, 64], "tfda_per100g_e9a255815e92"),
        "listed_item_ningbo_rice_cake": ("\u5e74\u7cd5", 131, [98, 164], "tfda_per100g_1980179ff36e"),
        "listed_item_corn_kernels": ("\u7389\u7c73\u7c92", 41, [31, 52], "tfda_per100g_f7d6cdc32ed1"),
        "listed_item_milkfish_ball": ("\u8671\u76ee\u9b5a\u4e38", 61, [46, 76], "tfda_per100g_a721bd05495e"),
    }

    for anchor_id, (canonical_name, kcal_point, kcal_range, source_evidence_id) in expected.items():
        anchor = anchors[anchor_id]
        assert anchor["canonical_name"] == canonical_name
        assert anchor["composition_posture"] == "listed_item_component"
        assert anchor["runtime_role"] == "common_serving_anchor"
        assert anchor["runtime_truth_allowed"] is True
        assert anchor["runtime_usage_boundary"] == "listed_component_only"
        assert anchor["kcal_point"] == kcal_point
        assert anchor["kcal_range"] == kcal_range
        assert anchor["source_class"] == "taiwan_tfda_open_data"
        assert anchor["source_refs"][0]["runtime_role"] == "source_evidence_only"
        assert anchor["source_refs"][0]["source_evidence_id"] == source_evidence_id
        assert anchor["kcal_basis"]["external_source_role"] == (
            "source_evidence_only_not_common_serving"
        )


def test_listed_component_lane_new_components_are_retrievable_without_bare_basket_truth() -> None:
    records = LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE).load_records()

    for query, expected_anchor_id in {
        "\u5ae9\u8c46\u8150": "listed_item_soft_tofu",
        "\u5e74\u7cd5": "listed_item_ningbo_rice_cake",
        "\u7389\u7c73\u7c92": "listed_item_corn_kernels",
        "\u8671\u76ee\u9b5a\u4e38": "listed_item_milkfish_ball",
    }.items():
        result = retrieve_fooddb_candidates(query, retrieval_records=records, limit=3)

        assert result["truth_selection_forbidden"] is True
        assert result["runtime_mutation_allowed"] is False
        assert result["accepted_candidates"]
        assert result["accepted_candidates"][0]["anchor_id"] == expected_anchor_id
        assert result["accepted_candidates"][0]["runtime_usage_boundary"] == (
            "listed_component_only"
        )
