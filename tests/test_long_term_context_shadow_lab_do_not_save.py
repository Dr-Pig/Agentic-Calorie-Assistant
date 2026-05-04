from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_memory_do_not_save_policy_rejects_low_value_or_sensitive_context() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "memory_do_not_save_policy_shadow_eval"
    ]

    assert artifact["artifact_type"] == "memory_do_not_save_policy_shadow_eval"
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["runtime_filter_installed"] is False
    assert artifact["policy_enforced_in_runtime_now"] is False
    assert artifact["product_capability_filter"] == {
        "must_have_declared_future_consumer": True,
        "must_improve_product_capability": True,
        "consumerless_context_rejected": True,
        "annoyance_or_creepiness_risk_blocks_promotion": True,
    }

    forbidden_ids = {item["class_id"] for item in artifact["forbidden_memory_classes"]}
    assert {
        "raw_secret_or_credential",
        "one_off_low_signal_food_event",
        "transient_mood_without_user_request",
        "unsupported_medical_inference",
        "cross_user_or_cross_project_context",
    }.issubset(forbidden_ids)

    allowed_ids = {item["class_id"] for item in artifact["candidate_allowed_classes"]}
    assert {
        "explicit_user_preference",
        "confirmed_negative_preference",
        "temporary_preference_with_expiry",
        "repeated_behavior_pattern",
        "correction_tendency_with_source_refs",
    }.issubset(allowed_ids)

    assert artifact["deterministic_boundary"] == {
        "may_reject_unqualified_candidate": True,
        "may_require_more_evidence": True,
        "may_create_semantic_user_profile": False,
        "may_override_human_confirmation": False,
    }
    assert artifact["review_examples"][0] == {
        "example_id": "single_ramen_once",
        "save_allowed": False,
        "reason": "one_off_low_signal_food_event",
    }
