from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def _feedback_fixture() -> dict:
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


def test_lab_review_loop_materializes_feedback_state_without_runtime_effect() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_feedback_fixture())[
        "memory_lab_review_loop_state"
    ]

    assert artifact["artifact_type"] == "memory_lab_review_loop_state"
    assert artifact["status"] == "generated"
    assert artifact["lab_isolated"] is True
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["user_facing_behavior_changed_in_mainline"] is False
    assert artifact["canonical_mutation_changed_in_mainline"] is False
    assert artifact["durable_product_memory_written_in_mainline"] is False
    assert artifact["manager_context_packet_changed_in_mainline"] is False
    assert artifact["real_scheduler_or_notification_delivery"] is False
    assert artifact["lab_artifacts_may_include_complete_ux"] is True
    assert artifact["summary"] == {
        "action_count": 6,
        "applied_action_count": 6,
        "active_record_count": 2,
        "suppressed_record_count": 1,
        "deleted_record_count": 1,
        "expired_record_count": 1,
        "blocker_count": 0,
    }

    records = {
        record["source_candidate_id"]: record
        for record in artifact["lab_memory_records"]
    }
    corrected = records["golden-order-morning-bar-oatmeal-latte"]
    assert corrected["record_state"] == "corrected_shadow"
    assert corrected["revision"] == 2
    assert corrected["active_in_lab_context"] is True
    assert corrected["memory_text"] == (
        "User often chooses Morning Bar oatmeal; latte should be optional."
    )
    assert [event["action_id"] for event in corrected["audit_log"]] == [
        "accept-golden-order",
        "correct-golden-order",
    ]
    assert corrected["audit_log"][0]["record_state_after"] == "accepted_shadow"
    assert corrected["audit_log"][1]["record_state_after"] == "corrected_shadow"

    accepted_negative = records["negative-preference-ingredient-cilantro"]
    assert accepted_negative["record_state"] == "accepted_shadow"
    assert accepted_negative["active_in_lab_context"] is True
    assert accepted_negative["can_be_runtime_loaded"] is False
    assert accepted_negative["durable_memory_written"] is False

    suppressed = records["app-usage-style-pattern"]
    assert suppressed["record_state"] == "suppressed_shadow"
    assert suppressed["active_in_lab_context"] is False
    assert suppressed["excluded_from_lab_context_reason"] == "suppressed_by_reviewer"

    deleted = records["intake-estimation-bias-likely-underestimate"]
    assert deleted["record_state"] == "deleted_shadow"
    assert deleted["active_in_lab_context"] is False
    assert deleted["memory_text"] is None
    assert deleted["audit_provenance_retained"] is True

    expired = records["temporary-preference-lower-oil-dinner"]
    assert expired["record_state"] == "expired_shadow"
    assert expired["active_in_lab_context"] is False
    assert expired["excluded_from_lab_context_reason"] == "expired_by_reviewer"

    assert artifact["active_context_candidate_ids"] == [
        "golden-order-morning-bar-oatmeal-latte",
        "negative-preference-ingredient-cilantro",
    ]
    assert set(artifact["excluded_context_candidate_ids"]) == {
        "app-usage-style-pattern",
        "intake-estimation-bias-likely-underestimate",
        "temporary-preference-lower-oil-dinner",
    }


def test_lab_review_loop_blocks_unknown_action_without_partial_state() -> None:
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
            "action_id": "bad-missing-target",
            "target_candidate_ids": ["missing-candidate"],
            "action_type": "delete_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Should block the whole reducer.",
        },
        {
            "action_id": "bad-unsupported-action",
            "target_candidate_ids": ["negative-preference-ingredient-cilantro"],
            "action_type": "promote_to_runtime_memory",
            "actor": "fixture_human_reviewer",
            "rationale": "Runtime promotion is not a lab review action.",
        },
    ]

    artifact = build_shadow_lab_artifacts(fixture)["memory_lab_review_loop_state"]

    assert artifact["status"] == "blocked"
    assert artifact["summary"]["applied_action_count"] == 0
    assert artifact["lab_memory_records"] == []
    assert artifact["active_context_candidate_ids"] == []
    assert artifact["blockers"] == [
        "bad-missing-target.unknown_target_candidate:missing-candidate",
        "bad-unsupported-action.unsupported_action_type:promote_to_runtime_memory",
    ]
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["runtime_effect_allowed"] is False
