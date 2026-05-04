from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact


def _pr_review_autopilot_closeout_artifact(fixture: dict[str, Any]) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="pr_review_autopilot_closeout",
        fixture=fixture,
        extra={
            "draft_pr_only": True,
            "auto_merge_allowed": False,
            "human_approval_required_for_merge": True,
            "continue_same_draft_pr_after_ci_green": True,
            "stop_after_pr_push": False,
            "merge_still_requires_human_approval": True,
            "offline_shadow_completion_audit": {
                "completion_status": "complete_for_no_runtime_scope",
                "remaining_buildable_without_runtime_dependencies": [],
                "runtime_or_storage_dependency_required_for_next_stage": True,
            },
            "blocked_future_runtime_slices": [
                "durable_memory_write_service",
                "memory_correction_delete_suppression_surface",
                "manager_context_retrieval_tool",
                "active_context_pack_injection",
                "semantic_llm_extraction_runtime",
                "live_menu_scan_recommendation_runtime",
            ],
            "review_loop_allowed_actions": [
                "push_offline_shadow_fixes",
                "update_draft_pr_body",
                "inspect_ci",
                "inspect_review_comments",
            ],
            "review_loop_forbidden_actions": [
                "merge_main",
                "mark_ready_for_review",
                "register_runtime_tool",
                "add_startup_or_scheduler_hook",
                "write_durable_memory",
            ],
        },
    )
