from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def _reviewed_product_fixture() -> dict:
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


def test_recommendation_shadow_eval_uses_reviewed_lab_context_without_serving() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    fixture = _reviewed_product_fixture()
    fixture["candidate_pool"].append(
        {
            "candidate_id": "food-cilantro",
            "name": "cilantro chicken bowl",
            "source": "fixture",
            "estimated_kcal": 690,
        }
    )

    artifact = build_shadow_lab_artifacts(fixture)["recommendation_shadow_eval"]

    assert artifact["recommendation_served"] is False
    assert artifact["reviewed_lab_view_status"] == "generated"
    assert artifact["reviewed_lab_context_source_artifact"] == (
        "memory_lab_review_loop_state"
    )
    assert artifact["used_reviewed_lab_record_ids"] == [
        "lab-shadow-memory-record-golden-order-morning-bar-oatmeal-latte",
        "lab-shadow-memory-record-negative-preference-ingredient-cilantro",
    ]
    assert "lab-shadow-memory-record-app-usage-style-pattern" not in artifact[
        "used_reviewed_lab_record_ids"
    ]

    food = next(
        item
        for item in artifact["candidate_evaluations"]
        if item["candidate"]["candidate_id"] == "food-1"
    )
    assert food["used_reviewed_lab_record_ids"] == artifact[
        "used_reviewed_lab_record_ids"
    ]
    assert any(
        record["record_state"] == "corrected_shadow"
        for record in artifact["reviewed_lab_record_summaries"]
    )
    assert food["runtime_effect_allowed"] is False


def test_proactive_no_send_uses_reviewed_lab_triggers_without_scheduler() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_reviewed_product_fixture())[
        "proactive_no_send_simulation"
    ]

    assert artifact["scheduler_activated"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["reviewed_lab_view_status"] == "generated"
    trigger_ids = {
        trigger["source_candidate_id"]
        for trigger in artifact["reviewed_lab_memory_triggers"]
    }
    assert "pattern-budget-overshoot-frequency" in trigger_ids
    assert "app-usage-style-pattern" not in trigger_ids
    assert all(
        trigger["runtime_effect_allowed"] is False
        for trigger in artifact["reviewed_lab_memory_triggers"]
    )


def test_rescue_shadow_uses_reviewed_lab_packets_without_commit() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_reviewed_product_fixture())[
        "rescue_shadow_candidates"
    ]

    assert artifact["rescue_committed"] is False
    assert artifact["budget_mutation_requested"] is False
    assert artifact["reviewed_lab_view_status"] == "generated"
    assert artifact["reviewed_lab_record_ids"] == [
        "lab-shadow-memory-record-pattern-budget-overshoot-frequency"
    ]
    packets = artifact["reviewed_lab_candidate_packets"]
    assert packets[0]["source_candidate_id"] == "pattern-budget-overshoot-frequency"
    assert "intake-estimation-bias-likely-underestimate" not in {
        packet["source_candidate_id"] for packet in packets
    }
    assert packets[0]["proposal_commit_allowed"] is False
