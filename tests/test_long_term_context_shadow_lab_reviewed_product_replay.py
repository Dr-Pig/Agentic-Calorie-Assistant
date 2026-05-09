from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def _reviewed_replay_fixture() -> dict:
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
            "action_id": "accept-rescue-pattern",
            "target_candidate_ids": ["pattern-budget-overshoot-frequency"],
            "action_type": "accept_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Useful for rescue viability shadow packets.",
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


def test_reviewed_memory_product_replay_links_feedback_loop_to_all_consumers() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_reviewed_replay_fixture())[
        "shadow_replay_evaluators"
    ]

    assert "reviewed_memory_product_loop_replay" in artifact["replays"]
    assert artifact["replay_count"] == 5
    replay = artifact["replays"]["reviewed_memory_product_loop_replay"]

    assert replay["replay_id"] == "reviewed_memory_product_loop_replay"
    assert replay["source_review_artifact"] == "memory_lab_review_loop_state"
    assert replay["review_surface_status"] == "generated"
    assert replay["review_state_counts"] == {
        "active": 3,
        "suppressed": 1,
        "deleted": 1,
        "expired": 1,
        "rejected": 0,
    }
    assert replay["recommendation_reviewed_record_ids"] == [
        "lab-shadow-memory-record-golden-order-morning-bar-oatmeal-latte",
        "lab-shadow-memory-record-negative-preference-ingredient-cilantro",
    ]
    assert replay["rescue_reviewed_packet_candidate_ids"] == [
        "pattern-budget-overshoot-frequency"
    ]
    assert "pattern-budget-overshoot-frequency" in replay[
        "proactive_reviewed_trigger_candidate_ids"
    ]
    assert "app-usage-style-pattern" not in replay[
        "proactive_reviewed_trigger_candidate_ids"
    ]
    assert replay["excluded_candidate_ids_by_reason"] == {
        "suppressed_by_reviewer": ["app-usage-style-pattern"],
        "deleted_by_reviewer": ["intake-estimation-bias-likely-underestimate"],
        "expired_by_reviewer": ["temporary-preference-lower-oil-dinner"],
    }
    assert replay["recommendation_served"] is False
    assert replay["scheduler_activated"] is False
    assert replay["rescue_committed"] is False
    assert replay["durable_memory_written"] is False
    assert replay["manager_context_packet_written"] is False
    assert replay["runtime_effect_allowed"] is False


def test_reviewed_memory_product_replay_blocks_consumer_outputs_when_review_state_blocks() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    fixture = _fixture_payload()
    fixture["review_actions"] = [
        {
            "action_id": "bad-runtime-promotion",
            "target_candidate_ids": ["negative-preference-ingredient-cilantro"],
            "action_type": "promote_to_runtime_memory",
            "actor": "fixture_human_reviewer",
            "rationale": "Runtime promotion is not a lab review action.",
        }
    ]

    artifact = build_shadow_lab_artifacts(fixture)["shadow_replay_evaluators"]
    replay = artifact["replays"]["reviewed_memory_product_loop_replay"]

    assert replay["status"] == "blocked"
    assert replay["blockers"] == [
        "bad-runtime-promotion.unsupported_action_type:promote_to_runtime_memory"
    ]
    assert replay["recommendation_reviewed_record_ids"] == []
    assert replay["proactive_reviewed_trigger_candidate_ids"] == []
    assert replay["rescue_reviewed_packet_candidate_ids"] == []
    assert replay["runtime_effect_allowed"] is False
    assert replay["durable_memory_written"] is False
