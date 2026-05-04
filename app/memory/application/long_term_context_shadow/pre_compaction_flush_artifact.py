from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact


def _pre_compaction_memory_flush_shadow_artifact(
    fixture: dict[str, Any],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="pre_compaction_memory_flush_shadow_plan",
        fixture=fixture,
        extra={
            "source_specs": [
                "docs/specs/L4A_MEMORY_MODEL_SPEC.md#96-pre-compaction-memory-flush",
                "docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md",
            ],
            "compaction_hook_registered": False,
            "compaction_hook_called": False,
            "runtime_flush_allowed_now": False,
            "shadow_flush_review_generated": True,
            "trigger_policy": _trigger_policy(),
            "candidate_capture_lanes": _candidate_capture_lanes(),
            "semantic_extraction_flags": _semantic_extraction_flags(),
            "flush_state_machine": _flush_state_machine(),
            "blocked_runtime_effects": _blocked_runtime_effects(),
            "product_capability_value": _product_capability_value(),
            "review_output_shape": _review_output_shape(),
        },
    )


def _trigger_policy() -> dict[str, bool]:
    return {
        "runs_before_transcript_compaction": True,
        "requires_scope_keys": True,
        "requires_source_refs": True,
        "candidate_only_before_human_review": True,
        "raw_transcript_summary_only": True,
    }


def _candidate_capture_lanes() -> list[str]:
    return [
        "explicit_user_preference",
        "negative_preference_or_suppression",
        "temporary_preference_with_expiry",
        "important_user_decision",
        "correction_or_deletion_request",
        "conversation_recall_summary",
    ]


def _semantic_extraction_flags() -> dict[str, bool]:
    return {
        "fixture_llm_output_used": True,
        "live_provider_used": False,
        "semantic_extraction_runtime_ready": False,
    }


def _flush_state_machine() -> list[dict[str, Any]]:
    return [
        {
            "state_id": "transcript_signal",
            "meaning_owner": "raw_conversation_trace",
            "runtime_use_allowed": False,
        },
        {
            "state_id": "shadow_candidate",
            "meaning_owner": "shadow_extraction_review",
            "runtime_use_allowed": False,
        },
        {
            "state_id": "human_review",
            "meaning_owner": "future_user_or_operator_confirmation",
            "runtime_use_allowed": False,
        },
        {
            "state_id": "future_confirmed_memory",
            "meaning_owner": "future_confirmed_memory_store",
            "runtime_use_allowed": False,
        },
        {
            "state_id": "future_runtime_injection_gate",
            "meaning_owner": "future_manager_context_policy",
            "runtime_use_allowed": False,
            "requires_future_gate": True,
        },
    ]


def _blocked_runtime_effects() -> list[dict[str, str]]:
    return [
        {
            "effect": "active_compaction_hook",
            "reason": "requires runtime compaction lifecycle integration",
        },
        {
            "effect": "durable_memory_write",
            "reason": "requires reviewed memory store and explicit human approval",
        },
        {
            "effect": "manager_context_packet_injection",
            "reason": "requires future injection gate after confirmed memory exists",
        },
        {
            "effect": "conversation_recall_tool_call",
            "reason": "requires approved manager retrieval tool contract",
        },
        {
            "effect": "provider_semantic_extraction",
            "reason": "requires live extraction eval and provider activation approval",
        },
    ]


def _product_capability_value() -> dict[str, str]:
    return {
        "chat_context": "prevents durable user preferences and decisions from being lost when long conversations compact.",
        "recommendation": "preserves explicit food likes, dislikes, and temporary constraints for future review.",
        "intake_clarification": "preserves user phrase meaning and corrections that would otherwise be buried in transcript summaries.",
        "proactive": "preserves suppression and reminder-style corrections without activating sends.",
        "calibration": "preserves logging-quality corrections as candidate context without changing math.",
    }


def _review_output_shape() -> dict[str, Any]:
    return {
        "candidate_only": True,
        "requires_human_review": True,
        "source_refs_required": True,
        "expiry_required_for_temporary_preference": True,
        "negative_preference_first_class": True,
        "canonical_truth_replaced_by_flush": False,
    }


__all__ = ["_pre_compaction_memory_flush_shadow_artifact"]
