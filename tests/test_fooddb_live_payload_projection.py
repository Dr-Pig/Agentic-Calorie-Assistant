from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.application.fooddb_live_payload_projection import (
    build_compact_fooddb_live_projection,
)
from app.nutrition.application.fooddb_manager_packet_smoke import (
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.application.fooddb_real_manager_e2e import (
    build_fooddb_real_manager_e2e,
)
from app.nutrition.application.fooddb_retrieval_policy import (
    build_runtime_retrieval_records_from_small_anchor_payload,
)
from app.nutrition.application.grokfast_fooddb_packet_smoke import build_live_manager_payload


def _packet_case(case_id: str) -> dict:
    payload = json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))
    records = build_runtime_retrieval_records_from_small_anchor_payload(payload)
    packet_artifact = build_fooddb_manager_packet_smoke(retrieval_records=records)
    return next(case for case in packet_artifact["cases"] if case["case_id"] == case_id)


def _real_manager_e2e_case(case_id: str) -> dict:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    real_manager_e2e = build_fooddb_real_manager_e2e(approved_packet_ready_artifact=artifact)
    return next(case for case in real_manager_e2e["cases"] if case["case_id"] == case_id)


def test_fooddb_live_payload_projection_compacts_modifier_case_packet() -> None:
    projection = build_compact_fooddb_live_projection(packet_case=_packet_case("chicken_bento_less_rice"))
    packet = projection["fooddb_evidence_packet"]
    evidence_item = packet["evidence_items"][0]

    assert "candidate_terms" not in packet
    assert "ranking_policy" not in packet
    assert "vector_search_policy" not in packet
    assert packet["retrieval_scope"] == "candidate_recall_only"
    assert packet["retrieval_boundary"] == "single_or_composite_candidate_recall"
    assert packet["manager_may_use_for"] == [
        "grounded_food_evidence",
        "macro_visibility_honesty",
        "followup_or_uncertainty_decision",
        "disambiguation",
    ]
    assert packet["manager_must_not_use_for"] == [
        "runtime_mutation",
        "creating_fooddb_truth",
        "inventing_source",
        "inventing_macro",
    ]
    assert evidence_item["anchor_id"] == "generic_meal_chicken_bento"
    assert evidence_item["canonical_name"] == "雞腿便當"
    assert evidence_item["source_provenance"] == {"source_id": "existing_small_anchor_store_tw"}
    assert evidence_item["approval_metadata"] == {"runtime_truth_allowed": True}
    assert evidence_item["modifier_compatibility"] == {
        "rice_portion": "compatible_via_normalized_equivalent"
    }
    assert evidence_item["packet_adjustment_available"] is False
    assert "modifier_adjustment_authority" not in evidence_item
    assert evidence_item["portion_basis"] == {
        "portion_unit": "box",
        "portion_quantity": 1,
        "label": "one generic chicken bento",
    }
    assert "derived_from" not in json.dumps(packet, ensure_ascii=False)
    assert "source_file" not in json.dumps(packet, ensure_ascii=False)
    assert "policy_version" not in json.dumps(packet, ensure_ascii=False)


def test_fooddb_live_payload_projection_uses_minimal_allowed_refs() -> None:
    projection = build_compact_fooddb_live_projection(packet_case=_packet_case("chicken_bento_less_rice"))

    assert projection["allowed_evidence_refs"] == [
        "chicken_bento_less_rice",
        "fooddb_packet case_id chicken_bento_less_rice",
        "generic_meal_chicken_bento",
        "雞腿便當",
    ]


def test_fooddb_live_payload_projection_preserves_packet_authorized_adjustment() -> None:
    packet_case = _packet_case("boba_large_half_sugar")
    packet_case = {
        **packet_case,
        "manager_evidence_packet": {
            **packet_case["manager_evidence_packet"],
            "evidence_items": [
                {
                    **packet_case["manager_evidence_packet"]["evidence_items"][0],
                    "adjusted_kcal_range": [400, 520],
                    "adjusted_kcal_point": 460,
                    "modifier_adjustment_authority": "packet_authorized",
                }
            ],
        },
    }

    projection = build_compact_fooddb_live_projection(packet_case=packet_case)
    evidence_item = projection["fooddb_evidence_packet"]["evidence_items"][0]

    assert evidence_item["modifier_compatibility"] == {
        "cup_size": "compatible",
        "sugar_level": "compatible",
    }
    assert evidence_item["packet_adjustment_available"] is True
    assert evidence_item["modifier_adjustment_authority"] == "packet_authorized"
    assert evidence_item["adjusted_kcal_point"] == 460
    assert evidence_item["adjusted_kcal_range"] == [400, 520]


def test_fooddb_live_payload_projection_reduces_live_payload_size() -> None:
    payload = build_live_manager_payload(packet_case=_packet_case("chicken_bento_less_rice"))

    assert payload["expected_output_contract"]["max_unique_evidence_refs"] == 3
    assert payload["expected_output_contract"]["preserve_packet_kcal_without_adjusted_values"] is True
    assert len(json.dumps(payload, ensure_ascii=False)) < 9000
    assert any("Use no more than 3 unique evidence_used refs total." in line for line in payload["instructions"])
    assert any(
        "keep kcal_point and kcal_range unchanged from the packet" in line
        for line in payload["instructions"]
    )


def test_fooddb_live_payload_projection_keeps_tool_results_read_only() -> None:
    projection = build_compact_fooddb_live_projection(packet_case=_packet_case("listed_luwei_components"))
    tool_result = projection["tool_evidence_result"]

    assert tool_result["result_type"] == "tool_evidence_result_v1"
    assert tool_result["runtime_mutation_allowed"] is False
    assert tool_result["runtime_truth_changed"] is False
    assert tool_result["read_model_only"] is True
    assert tool_result["source_implementation_visible"] is False
    assert len(tool_result["evidence_packets"]) == 1
    assert tool_result["evidence_packets"][0]["retrieval_scope"] == "candidate_recall_only"
    assert tool_result["evidence_packets"][0]["retrieval_boundary"] == "listed_basket_component_recall"
    assert tool_result["manager_must_not_use_for"] == [
        "runtime_mutation",
        "creating_fooddb_truth",
        "inventing_source",
        "inventing_macro",
        "inferring_source_implementation",
    ]
    assert projection["tool_results"] == [
        {
            "tool_name": "lookup_food_evidence",
            "tool_call_id": "fooddb-packet-listed_luwei_components",
            "result_boundary": "read_only_evidence_packet_result",
            "runtime_mutation_allowed": False,
            "truth_level": "read_only_food_evidence_result",
            "output_ref": "tool_evidence_result",
        }
    ]
    assert "adapter_diagnostics" not in str(tool_result)


def test_fooddb_live_payload_projection_preserves_exact_macro_visible_fields() -> None:
    projection = build_compact_fooddb_live_projection(
        packet_case=_real_manager_e2e_case("exact_macro_visible_chocolate_milk")
    )

    evidence_item = projection["fooddb_evidence_packet"]["evidence_items"][0]

    assert evidence_item["source_lane"] == "exact_item_card"
    assert evidence_item["macro_visibility_status"] == "visible"
    assert evidence_item["protein_g"] == 12
    assert evidence_item["carbs_g"] == 48
    assert evidence_item["fat_g"] == 6


def test_fooddb_live_payload_projection_preserves_macro_hidden_without_macro_values() -> None:
    payload = build_live_manager_payload(
        packet_case=_real_manager_e2e_case("generic_macro_hidden_boba")
    )

    evidence_item = payload["fooddb_evidence_packet"]["evidence_items"][0]

    assert evidence_item["source_lane"] == "generic_common_serving"
    assert evidence_item["macro_visibility_status"] == "hidden_missing_source"
    assert "protein_g" not in evidence_item
    assert "carbs_g" not in evidence_item
    assert "fat_g" not in evidence_item
