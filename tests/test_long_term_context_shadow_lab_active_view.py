from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def _reviewed_fixture() -> dict:
    fixture = _fixture_payload()
    fixture["review_actions"] = [
        {
            "action_id": "accept-golden-order",
            "target_candidate_ids": ["golden-order-morning-bar-oatmeal-latte"],
            "action_type": "accept_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Useful repeat order for recommendation shadow tests.",
        },
        {
            "action_id": "correct-golden-order",
            "target_candidate_ids": ["golden-order-morning-bar-oatmeal-latte"],
            "action_type": "correct_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Correction from review feedback.",
            "corrected_memory_text": (
                "User often chooses Morning Bar oatmeal; latte should be optional."
            ),
        },
        {
            "action_id": "accept-negative-preference",
            "target_candidate_ids": ["negative-preference-ingredient-cilantro"],
            "action_type": "accept_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Explicit dislike is useful for recommendation suppression.",
        },
        {
            "action_id": "suppress-style-pattern",
            "target_candidate_ids": ["app-usage-style-pattern"],
            "action_type": "suppress_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Do not let thin app-usage evidence shape context packs.",
        },
        {
            "action_id": "delete-bias-pattern",
            "target_candidate_ids": ["intake-estimation-bias-likely-underestimate"],
            "action_type": "delete_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Reviewer requested lab deletion after poor attribution.",
        },
        {
            "action_id": "expire-temporary-preference",
            "target_candidate_ids": ["temporary-preference-lower-oil-dinner"],
            "action_type": "expire_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Temporary dinner constraint passed its validity window.",
        },
    ]
    return fixture


def test_consumer_substrate_projects_reviewed_active_lab_memory() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_reviewed_fixture())[
        "consumer_memory_substrate_shadow_eval"
    ]
    view = artifact["reviewed_lab_context_view"]

    assert view["source_artifact_type"] == "memory_lab_review_loop_state"
    assert view["status"] == "generated"
    assert view["lab_isolated"] is True
    assert view["runtime_effect_allowed"] is False
    assert view["manager_context_injection_allowed"] is False
    assert view["active_source_candidate_ids"] == [
        "golden-order-morning-bar-oatmeal-latte",
        "negative-preference-ingredient-cilantro",
    ]
    assert set(view["excluded_source_candidate_ids"]) == {
        "app-usage-style-pattern",
        "intake-estimation-bias-likely-underestimate",
        "temporary-preference-lower-oil-dinner",
    }

    recommendation = view["consumer_views"]["recommendation"]
    assert recommendation["source_candidate_ids"] == [
        "golden-order-morning-bar-oatmeal-latte",
        "negative-preference-ingredient-cilantro",
    ]
    corrected = next(
        record
        for record in recommendation["active_records"]
        if record["source_candidate_id"] == "golden-order-morning-bar-oatmeal-latte"
    )
    assert corrected["record_state"] == "corrected_shadow"
    assert corrected["memory_text"] == (
        "User often chooses Morning Bar oatmeal; latte should be optional."
    )

    calibration = view["consumer_views"]["calibration"]
    rescue = view["consumer_views"]["rescue_context"]
    proactive = view["consumer_views"]["proactive_context"]
    assert calibration["source_candidate_ids"] == []
    assert rescue["source_candidate_ids"] == []
    assert "app-usage-style-pattern" not in proactive["source_candidate_ids"]


def test_context_packs_include_reviewed_active_view_without_replacing_candidates() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_reviewed_fixture())[
        "long_term_context_pack_shadow_eval"
    ]
    recommendation = artifact["context_packs"]["recommendation"]

    assert recommendation["reviewed_lab_view_status"] == "generated"
    assert recommendation["reviewed_lab_context_source_artifact"] == (
        "memory_lab_review_loop_state"
    )
    assert recommendation["reviewed_lab_record_ids"] == [
        "lab-shadow-memory-record-golden-order-morning-bar-oatmeal-latte",
        "lab-shadow-memory-record-negative-preference-ingredient-cilantro",
    ]
    assert (
        "golden-order-morning-bar-oatmeal-latte"
        in recommendation["selected_candidate_ids"]
    )
    assert "app-usage-style-pattern" not in recommendation["reviewed_lab_record_ids"]
    assert recommendation["manager_context_injection_allowed"] is False
    assert recommendation["runtime_effect_allowed"] is False


def test_reviewed_active_view_blocks_invalid_review_state_without_partial_context() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    fixture = _fixture_payload()
    fixture["review_actions"] = [
        {
            "action_id": "accept-known",
            "target_candidate_ids": ["negative-preference-ingredient-cilantro"],
            "action_type": "accept_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Would be valid alone.",
        },
        {
            "action_id": "bad-unsupported-action",
            "target_candidate_ids": ["negative-preference-ingredient-cilantro"],
            "action_type": "promote_to_runtime_memory",
            "actor": "fixture_human_reviewer",
            "rationale": "Runtime promotion is not a lab review action.",
        },
    ]

    artifacts = build_shadow_lab_artifacts(fixture)
    view = artifacts["consumer_memory_substrate_shadow_eval"][
        "reviewed_lab_context_view"
    ]
    recommendation = artifacts["long_term_context_pack_shadow_eval"]["context_packs"][
        "recommendation"
    ]

    assert view["status"] == "blocked"
    assert view["active_source_candidate_ids"] == []
    assert view["consumer_views"]["recommendation"]["active_records"] == []
    assert view["blockers"] == [
        "bad-unsupported-action.unsupported_action_type:promote_to_runtime_memory"
    ]
    assert recommendation["reviewed_lab_view_status"] == "blocked"
    assert recommendation["reviewed_lab_record_ids"] == []
