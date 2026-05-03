from __future__ import annotations

from typing import Any

from ...runtime.contracts.phase_a import (
    ContextInjectionPolicy,
    CurrentTurnContextV1,
    ManagerContextPack,
)

PromotionMode = str | None


def default_context_injection_policy() -> ContextInjectionPolicy:
    return ContextInjectionPolicy(
        must_inject=[
            "interaction_event",
            "active_meal_thread_ref",
            "pending_followup",
            "candidate_attachment_targets",
            "current_budget_snapshot",
            "recent_chat_turns",
        ],
        available_if_needed=[
            "recent_committed_meal_refs",
            "active_body_plan_snapshot",
            "recent_item_targets",
            "target_resolution_posture",
            "context_freshness",
            "session_atomic_blocks",
            "last_system_question",
            "open_workflow_type",
        ],
        trace_only=[
            "raw_transcript",
            "verbose_resolver_diagnostics",
        ],
        not_for_manager=[
            "full_ledger_history",
            "long_term_memory_blobs",
            "archive_conversation_residue",
        ],
    )


def build_manager_context_pack(
    *,
    current_turn_context: CurrentTurnContextV1,
    include_available_if_needed: bool = False,
    promotion_mode: PromotionMode = None,
    recent_transcript_tail: list[str] | None = None,
    verbose_resolver_diagnostics: dict[str, Any] | None = None,
    full_ledger_history: Any | None = None,
    long_term_memory_blobs: Any | None = None,
    archive_conversation_residue: Any | None = None,
) -> ManagerContextPack:
    policy = default_context_injection_policy()
    manager_context = {
        "interaction_event": current_turn_context.current_interaction_event.model_dump(mode="json"),
        "active_meal_thread_ref": current_turn_context.active_meal_thread_ref,
        "pending_followup": current_turn_context.pending_followup,
        "candidate_attachment_targets": current_turn_context.candidate_attachment_targets,
        "current_budget_snapshot": current_turn_context.current_budget_snapshot,
        "recent_chat_turns": current_turn_context.recent_chat_turns,
    }
    available_if_needed = {
        "recent_committed_meal_refs": current_turn_context.recent_committed_meal_refs,
        "active_body_plan_snapshot": current_turn_context.active_body_plan_snapshot,
        "recent_item_targets": current_turn_context.recent_item_targets,
        "target_resolution_posture": current_turn_context.target_resolution_posture,
        "context_freshness": current_turn_context.context_freshness,
        "session_atomic_blocks": current_turn_context.session_atomic_blocks,
        "last_system_question": current_turn_context.last_system_question,
        "open_workflow_type": current_turn_context.open_workflow_type,
    }
    promotion_reasons: list[str] = []
    if current_turn_context.open_workflow_type in {"meal_followup", "meal_correction"}:
        manager_context.update(
            {
                "recent_item_targets": current_turn_context.recent_item_targets,
                "target_resolution_posture": current_turn_context.target_resolution_posture,
                "context_freshness": current_turn_context.context_freshness,
                "session_atomic_blocks": current_turn_context.session_atomic_blocks,
            }
        )
        promotion_reasons.append("followup_or_correction_context")
    if promotion_mode == "budget_query":
        manager_context.update(
            {
                "active_body_plan_snapshot": current_turn_context.active_body_plan_snapshot,
                "context_freshness": current_turn_context.context_freshness,
                "session_atomic_blocks": current_turn_context.session_atomic_blocks,
            }
        )
        promotion_reasons.append("budget_query_context")
    if include_available_if_needed:
        manager_context.update(available_if_needed)
    return ManagerContextPack(
        policy=policy,
        manager_context=manager_context,
        available_if_needed=available_if_needed,
        trace_only={
            "raw_transcript": list(recent_transcript_tail or []),
            "verbose_resolver_diagnostics": dict(verbose_resolver_diagnostics or {}),
        },
        not_for_manager={
            "full_ledger_history": full_ledger_history,
            "long_term_memory_blobs": long_term_memory_blobs,
            "archive_conversation_residue": archive_conversation_residue,
        },
        promotion_reasons=promotion_reasons,
    )
