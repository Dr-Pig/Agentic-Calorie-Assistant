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
            "continue_without_gate_after_batch2": False,
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
