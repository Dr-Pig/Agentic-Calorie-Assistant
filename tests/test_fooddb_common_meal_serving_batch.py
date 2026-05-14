from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.application.fooddb_tfda_anchor_integrity import (
    build_tfda_anchor_integrity_report,
)


COMMON_MEAL_SERVING_NAMES = {
    "staple_fried_rice": "\u7092\u98ef",
    "snack_shuijianbao": "\u6c34\u714e\u5305",
    "snack_pork_bun": "\u8089\u5305",
    "stable_base_cantonese_congee": "\u5ee3\u6771\u7ca5",
}


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def _tfda_source_payload() -> dict:
    return json.loads(Path("app/knowledge/tfda_per100g_source_evidence_tw.json").read_text(encoding="utf-8"))


def test_common_meal_batch_is_packet_ready_and_integrity_checked() -> None:
    payload = _small_anchor_payload()
    anchors = {
        anchor.get("anchor_id"): anchor
        for anchor in payload["anchors"]
        if isinstance(anchor, dict) and anchor.get("anchor_id")
    }

    assert set(COMMON_MEAL_SERVING_NAMES).issubset(anchors)
    for anchor_id, name in COMMON_MEAL_SERVING_NAMES.items():
        anchor = anchors[anchor_id]
        assert anchor["canonical_name"] == name
        assert "?" not in anchor["canonical_name"]
        assert anchor["runtime_role"] == "common_serving_anchor"
        assert anchor["runtime_truth_allowed"] is True
        assert anchor["runtime_usage_boundary"] == "generic_range_estimate_with_refinement_not_exact"
        assert anchor["source_refs"][0]["runtime_role"] == "source_evidence_only"
        assert anchor["source_refs"][0]["serving_basis"] == "per_100g"
        assert anchor["kcal_basis"]["external_source_role"] == (
            "source_evidence_only_not_common_serving"
        )

    packet_ready = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/accurate_intake_approved_packet_ready_fooddb_artifact.json",
        selection_profile="full_current_shell",
    )
    assert packet_ready["summary"]["source_anchor_count"] == 754
    assert packet_ready["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 400

    integrity = build_tfda_anchor_integrity_report(
        small_anchor_payload=payload,
        tfda_source_payload=_tfda_source_payload(),
    )
    assert integrity["status"] == "pass"
    assert integrity["summary"]["tfda_runtime_anchor_count"] == 44
