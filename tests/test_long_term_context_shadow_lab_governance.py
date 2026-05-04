from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_memory_promotion_demotion_declares_correction_deletion_suppression_policy() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "memory_promotion_demotion_shadow_eval"
    ]

    policy = artifact["correction_deletion_suppression_policy"]
    assert policy["policy_status"] == "shadow_policy_only"
    assert policy["runtime_memory_mutation_allowed"] is False
    assert policy["durable_delete_allowed"] is False
    assert policy["manager_context_injection_allowed"] is False
    assert policy["source_trace_retained_for_audit"] is True
    assert policy["supported_shadow_actions"] == [
        "correct_candidate",
        "suppress_candidate",
        "delete_candidate",
        "expire_candidate",
    ]
    assert policy["future_runtime_requirements"] == [
        "human_confirmed_memory_store",
        "user_visible_correction_surface",
        "delete_or_suppress_audit_log",
        "context_pack_exclusion_filter",
    ]
