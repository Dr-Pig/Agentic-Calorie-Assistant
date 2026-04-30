from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.orm import Session

from app.composition.intake_persistence_tools import persist_meal_log_tool
from app.intake.application.final_action_mutation_classifier import final_action_has_persistence_effect
from app.intake.application.intake_trace_tools import append_trace_event_tool
from app.runtime.application.execution_guard import validate_intake_persistence


def initial_state_mutation_summary() -> dict[str, bool]:
    return {
        "body_plan_seeded": False,
        "meal_logged": False,
        "canonical_commit": False,
        "draft_saved": False,
        "new_meal_version_created": False,
        "old_version_superseded": False,
        "ledger_updated": False,
    }


def persist_bundle2_artifact(
    db: Session,
    *,
    nutrition_artifact: Any | None,
    final_action: str,
    manager_semantic_decision: dict[str, Any] | None,
    request_id: str,
    record_timing: Callable[[str, int], None],
    now_ms: Callable[[], int],
    state_mutation_summary: dict[str, Any],
) -> Any | None:
    if nutrition_artifact is None or getattr(nutrition_artifact, "payload", None) is None:
        return None
    if not final_action_has_persistence_effect(final_action):
        return None

    start = now_ms()
    persistence_result = persist_meal_log_tool(
        db,
        artifact=nutrition_artifact,
        request_id=request_id,
        final_action=final_action,
        manager_semantic_decision=manager_semantic_decision,
    )
    record_timing("tool_persist_meal_log", now_ms() - start)
    db.expire_all()

    guard = validate_intake_persistence(
        action=persistence_result.action,
        canonical_commit_present=persistence_result.canonical_commit is not None,
    )
    if not guard.ok:
        append_trace_event_tool(
            request_id=request_id,
            stage="v2_persist_meal_log",
            status="guard_failed",
            summary={
                "action": persistence_result.action,
                "status": persistence_result.status,
                "persisted_log_id": persistence_result.persisted_log_id,
                "canonical_commit_present": persistence_result.canonical_commit is not None,
                "violations": list(guard.violations),
            },
        )
        raise ValueError(
            "Bundle 2 persistence guard failed: "
            f"{', '.join(guard.violations)} "
            f"(action={persistence_result.action}, status={persistence_result.status}, "
            f"canonical_commit_present={persistence_result.canonical_commit is not None})"
        )

    state_mutation_summary["draft_saved"] = persistence_result.persisted_log_id is not None and persistence_result.canonical_commit is None
    state_mutation_summary["meal_logged"] = persistence_result.canonical_commit is not None
    state_mutation_summary["canonical_commit"] = persistence_result.canonical_commit is not None
    state_mutation_summary["ledger_updated"] = persistence_result.canonical_commit is not None
    canonical_commit = persistence_result.canonical_commit or {}
    state_mutation_summary["new_meal_version_created"] = canonical_commit.get("meal_version_id") is not None
    state_mutation_summary["old_version_superseded"] = canonical_commit.get("superseded_version_id") is not None

    append_trace_event_tool(
        request_id=request_id,
        stage="v2_persist_meal_log",
        status="ok",
        summary={
            "action": persistence_result.action,
            "status": persistence_result.status,
            "persisted_log_id": persistence_result.persisted_log_id,
            "canonical_commit": persistence_result.canonical_commit,
        },
    )
    return persistence_result
