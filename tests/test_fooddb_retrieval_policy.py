from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_retrieval_policy import (
    _rank_candidates,
    build_fooddb_retrieval_policy_artifact,
    build_runtime_retrieval_records_from_small_anchor_payload,
    retrieve_fooddb_candidates,
)
from app.nutrition.application.fooddb_retrieval_artifact_parts import (
    approved_fooddb_trace,
    candidate_component,
    component_breakdown_item,
)
from app.nutrition.application.retrieval_semantic_decision import B2ManagerSemanticDecision
from app.composition.intake_estimation_tools import _manager_owned_retrieval_query
from app.nutrition.infrastructure.small_anchor_store_loader import load_small_anchor_seed_records


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def test_retrieval_policy_resolves_common_aliases_and_modifiers_without_truth_selection() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(_small_anchor_payload())
    result = retrieve_fooddb_candidates(
        "大杯半糖珍奶",
        retrieval_records=records,
    )

    assert result["retrieval_scope"] == "candidate_recall_only"
    assert result["truth_selection_forbidden"] is True
    assert result["runtime_mutation_allowed"] is False
    assert result["normalized_query"]["modifier_hints"] == {
        "cup_size": "large",
        "sugar_level": "half_sugar",
    }
    assert result["accepted_candidates"][0]["anchor_id"] == "custom_drink_boba_milk_tea"
    assert result["accepted_candidates"][0]["match_path"] == "alias_expansion_exact"
    assert result["accepted_candidates"][0]["confidence"] == "high"
    assert result["accepted_candidates"][0]["runtime_truth_allowed"] is True


def test_retrieval_policy_uses_fuzzy_lexical_for_typos_not_vector_truth() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(_small_anchor_payload())
    result = retrieve_fooddb_candidates(
        "珍珠乃茶",
        retrieval_records=records,
    )

    assert result["vector_search_policy"]["allowed_for"] == "candidate_recall_later_only"
    assert result["vector_search_policy"]["forbidden_for"] == [
        "truth_selection",
        "kcal_decision",
        "runtime_mutation",
    ]
    assert result["accepted_candidates"][0]["anchor_id"] == "custom_drink_boba_milk_tea"
    assert result["accepted_candidates"][0]["match_path"] == "fuzzy_alias"
    assert result["accepted_candidates"][0]["confidence"] == "medium_high"
    assert result["accepted_candidates"][0]["requires_manager_disambiguation"] is True


def test_retrieval_policy_preserves_bare_and_listed_basket_boundary() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(_small_anchor_payload())
    bare = retrieve_fooddb_candidates(
        "我吃滷味",
        retrieval_records=records,
    )
    listed = retrieve_fooddb_candidates(
        "滷味有豆干、海帶、貢丸",
        retrieval_records=records,
        listed_components=["豆干", "海帶", "貢丸"],
    )

    assert bare["retrieval_boundary"] == "bare_basket_ask_followup_no_estimate"
    assert bare["accepted_candidates"] == []
    assert bare["followup_hints"]

    assert listed["retrieval_boundary"] == "listed_basket_component_recall"
    assert [item["anchor_id"] for item in listed["accepted_candidates"]] == [
        "listed_item_kelp",
        "listed_item_meatball",
        "listed_item_tofu_dried",
    ]
    assert all(item["runtime_truth_allowed"] is True for item in listed["accepted_candidates"])


def test_retrieval_policy_artifact_is_report_only_and_manager_packet_is_compact() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(_small_anchor_payload())
    artifact = build_fooddb_retrieval_policy_artifact(
        retrieval_records=records,
    )

    assert artifact["artifact_type"] == "accurate_intake_fooddb_retrieval_policy"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["packetizer_format_changed"] is False
    assert artifact["summary"]["runtime_anchor_indexed_count"] == 88
    assert artifact["summary"]["source_lane_counts"] == {
        "exact_item_card": 0,
        "generic_common_serving": 44,
        "listed_component": 44,
        "basket_family_semantic_only": 4,
    }
    assert artifact["manager_retrieval_catalog"]["raw_source_rows_included"] is False
    assert artifact["manager_retrieval_catalog"]["candidate_only_records_included"] is False
    assert artifact["manager_retrieval_catalog"]["full_fooddb_included"] is False


def test_retrieval_policy_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    output = tmp_path / "retrieval_policy.json"

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_retrieval_policy import main

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_fooddb_retrieval_policy"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["retrieval_architecture"]["dependency_inversion"][
        "future_adapter_shape"
    ] == "local_json_or_sqlite_or_supabase_can_supply_same_records"


def test_retrieval_policy_exposes_ranking_features_and_modifier_compatibility() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(_small_anchor_payload())
    result = retrieve_fooddb_candidates(
        "large boba",
        retrieval_records=records,
    )

    assert result["normalized_query"]["candidate_terms"] == ["large boba", "boba"]
    assert result["ranking_policy"]["features"] == [
        "lexical_match",
        "source_lane",
        "runtime_truth_allowed",
        "source_quality",
        "serving_basis",
        "portion_basis",
        "modifier_compatibility",
        "ambiguity_risk",
    ]

    candidate = result["accepted_candidates"][0]
    assert candidate["anchor_id"] == "custom_drink_boba_milk_tea"
    assert candidate["ranking_reasons"] == [
        "alias_expansion_exact",
        "runtime_truth_allowed",
        "source_lane:generic_common_serving",
        "kcal_range_present",
        "serving_basis_present",
        "portion_basis_present",
        "modifier_compatible:cup_size",
    ]
    assert candidate["modifier_compatibility"] == {"cup_size": "compatible"}


def test_retrieval_policy_marks_normalized_rice_modifier_as_equivalent_not_semantic_truth() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(_small_anchor_payload())
    result = retrieve_fooddb_candidates(
        "雞腿便當少飯",
        retrieval_records=records,
    )

    candidate = result["accepted_candidates"][0]
    assert candidate["anchor_id"] == "generic_meal_chicken_bento"
    assert candidate["modifier_compatibility"] == {
        "rice_portion": "compatible_via_normalized_equivalent"
    }
    assert "modifier_compatible:rice_portion" not in candidate["ranking_reasons"]


def test_retrieval_policy_recalls_chicken_rice_as_generic_common_serving() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(
        {"anchors": load_small_anchor_seed_records()}
    )
    result = retrieve_fooddb_candidates(
        "午餐吃了一碗雞肉飯",
        retrieval_records=records,
    )

    assert result["retrieval_boundary"] == "single_or_composite_candidate_recall"
    assert [item["anchor_id"] for item in result["accepted_candidates"]] == [
        "rice_bowl_chicken_rice"
    ]
    assert result["ambiguity_reason"] is None
    candidate = result["accepted_candidates"][0]
    assert candidate["anchor_id"] == "rice_bowl_chicken_rice"
    assert candidate["source_lane"] == "generic_common_serving"
    assert candidate["runtime_truth_allowed"] is True
    assert candidate["requires_manager_disambiguation"] is False
    assert candidate["kcal_range"] == [450, 700]
    assert "runtime_truth_allowed" in candidate["ranking_reasons"]

    component = candidate_component(candidate, source_lane_value="generic_common_serving")
    breakdown = component_breakdown_item(
        component,
        candidate=candidate,
        source_lane_value="generic_common_serving",
    )
    trace = approved_fooddb_trace(
        source_lane_value="generic_common_serving",
        retrieval_boundary=result["retrieval_boundary"],
        evidence_ids=["rice_bowl_chicken_rice"],
        macro_visible=False,
        runtime_truth_allowed=True,
        kcal_range=candidate["kcal_range"],
    )

    assert breakdown["kcal_range"] == [450, 700]
    assert trace["kcal_range"] == [450, 700]


def test_retrieval_policy_does_not_parse_listed_basket_components_from_raw_text() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(
        {"anchors": load_small_anchor_seed_records()}
    )
    result = retrieve_fooddb_candidates(
        "\u6211\u5403\u6ef7\u5473 \u767d\u98ef\u534a\u7897 \u96de\u817f\u4e00\u652f \u9752\u83dc\u5169\u6a23 \u6ef7\u86cb\u4e00\u9846",
        retrieval_records=records,
    )

    assert result["retrieval_boundary"] == "bare_basket_ask_followup_no_estimate"
    assert result["accepted_candidates"] == []


def test_retrieval_policy_recalls_manager_owned_listed_basket_components() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(
        {"anchors": load_small_anchor_seed_records()}
    )
    result = retrieve_fooddb_candidates(
        "raw text should not decide listed components",
        retrieval_records=records,
        listed_components=[
            "\u767d\u98ef\u534a\u7897",
            "\u96de\u817f\u4e00\u652f",
            "\u9752\u83dc\u5169\u6a23",
            "\u6ef7\u86cb\u4e00\u9846",
        ],
        limit=8,
    )

    assert result["retrieval_boundary"] == "listed_basket_component_recall"
    assert [item["anchor_id"] for item in result["accepted_candidates"]] == [
        "listed_component_braised_egg_one",
        "listed_component_chicken_leg_one",
        "listed_component_greens_two_servings",
        "listed_component_white_rice_half_bowl",
    ]
    assert result["rejected_candidates"] == []
    assert all(item["runtime_truth_allowed"] is True for item in result["accepted_candidates"])
    assert all(
        item["requires_manager_disambiguation"] is False
        for item in result["accepted_candidates"]
    )


def test_manager_owned_refinement_query_combines_target_and_user_modifier_text() -> None:
    decision = B2ManagerSemanticDecision(
        base_dish="\u73cd\u73e0\u5976\u8336",
        aliases=[],
        brand_hint=None,
        size_hint="\u4e2d\u676f",
        modifier_hints=["\u534a\u7cd6"],
        listed_items=[],
        retrieval_goal="generic_anchor_lookup",
        semantic_authority_source="live_manager_structured_output",
    )

    assert _manager_owned_retrieval_query(
        decision,
        raw_user_input="\u4e2d\u676f\u534a\u7cd6",
    ) == "\u73cd\u73e0\u5976\u8336 \u4e2d\u676f \u534a\u7cd6"


def test_manager_owned_base_query_does_not_append_raw_utterance_as_modifier_text() -> None:
    decision = B2ManagerSemanticDecision(
        base_dish="\u73cd\u5976",
        aliases=[],
        brand_hint=None,
        size_hint=None,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="generic_anchor_lookup",
        semantic_authority_source="live_manager_structured_output",
    )

    assert _manager_owned_retrieval_query(
        decision,
        raw_user_input="\u559d\u4e86\u4e00\u676f\u73cd\u5976",
    ) == "\u73cd\u5976"


def test_semantic_schema_distinguishes_drink_modifiers_from_listed_components() -> None:
    from app.runtime.agent.manager_branch_shapes import manager_semantic_decision_schema

    schema = manager_semantic_decision_schema()
    listed_description = schema["properties"]["listed_items"]["description"]
    retrieval_description = schema["properties"]["retrieval_goal"]["description"]

    assert "Active drink size/sugar/ice/topping refinements are modifiers" in listed_description
    assert "keep listed_items empty" in listed_description
    assert "generic_anchor_lookup with base_dish plus modifier_hints" in retrieval_description


def test_retrieval_policy_fuzzy_matches_alias_expansion_keys_without_vector_truth() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(_small_anchor_payload())
    result = retrieve_fooddb_candidates(
        "boba milk teaa",
        retrieval_records=records,
    )

    assert result["vector_search_policy"]["allowed_for"] == "candidate_recall_later_only"
    assert result["truth_selection_forbidden"] is True
    candidate = result["accepted_candidates"][0]
    assert candidate["anchor_id"] == "custom_drink_boba_milk_tea"
    assert candidate["match_path"] == "alias_expansion_contained_in_query"
    assert candidate["confidence"] == "medium_high"
    assert candidate["requires_manager_disambiguation"] is True


def test_retrieval_ranking_prefers_runtime_truth_when_other_signals_tie() -> None:
    base = {
        "match_path": "canonical_or_alias_exact",
        "match_score": 100,
        "modifier_compatibility": {},
        "source_provenance": {"source_id": "test"},
        "serving_basis": "common_serving",
        "portion_basis": {"portion_quantity": 1},
        "requires_manager_disambiguation": False,
    }

    ranked = _rank_candidates(
        [
            {**base, "anchor_id": "a_false", "runtime_truth_allowed": False},
            {**base, "anchor_id": "b_true", "runtime_truth_allowed": True},
        ]
    )

    assert [candidate["anchor_id"] for candidate in ranked] == ["b_true", "a_false"]
