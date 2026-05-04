from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_pre_compaction_memory_flush_shadow_plan_preserves_signals_without_hooks() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "pre_compaction_memory_flush_shadow_plan"
    ]

    assert artifact["artifact_type"] == "pre_compaction_memory_flush_shadow_plan"
    assert artifact["compaction_hook_registered"] is False
    assert artifact["compaction_hook_called"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["runtime_flush_allowed_now"] is False
    assert artifact["shadow_flush_review_generated"] is True
    assert artifact["trigger_policy"] == {
        "runs_before_transcript_compaction": True,
        "requires_scope_keys": True,
        "requires_source_refs": True,
        "candidate_only_before_human_review": True,
        "raw_transcript_summary_only": True,
    }

    assert artifact["candidate_capture_lanes"] == [
        "explicit_user_preference",
        "negative_preference_or_suppression",
        "temporary_preference_with_expiry",
        "important_user_decision",
        "correction_or_deletion_request",
        "conversation_recall_summary",
    ]
    assert artifact["semantic_extraction_flags"] == {
        "fixture_llm_output_used": True,
        "live_provider_used": False,
        "semantic_extraction_runtime_ready": False,
    }

    state_ids = [state["state_id"] for state in artifact["flush_state_machine"]]
    assert state_ids == [
        "transcript_signal",
        "shadow_candidate",
        "human_review",
        "future_confirmed_memory",
        "future_runtime_injection_gate",
    ]
    assert artifact["flush_state_machine"][1]["runtime_use_allowed"] is False
    assert artifact["flush_state_machine"][3]["runtime_use_allowed"] is False
    assert artifact["flush_state_machine"][4]["requires_future_gate"] is True

    blocked = {item["effect"] for item in artifact["blocked_runtime_effects"]}
    assert {
        "active_compaction_hook",
        "durable_memory_write",
        "manager_context_packet_injection",
        "conversation_recall_tool_call",
    }.issubset(blocked)
