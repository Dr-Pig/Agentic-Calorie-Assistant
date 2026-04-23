from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.orm import Session

from ...runtime.application.execution_guard import validate_intake_persistence
from . import manager_tools as tools


COMMITTING_ACTIONS = {"commit", "correction_applied", "overshoot_note", "ask_followup"}


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
    request_id: str,
    record_timing: Callable[[str, int], None],
    now_ms: Callable[[], int],
    state_mutation_summary: dict[str, Any],
) -> Any | None:
    if nutrition_artifact is None or getattr(nutrition_artifact, "payload", None) is None:
        return None
    if final_action not in COMMITTING_ACTIONS:
        return None

    start = now_ms()
    persistence_result = tools.persist_meal_log_tool(db, artifact=nutrition_artifact, request_id=request_id)
    record_timing("tool_persist_meal_log", now_ms() - start)
    db.expire_all()

    guard = validate_intake_persistence(
        action=persistence_result.action,
        canonical_commit_present=persistence_result.canonical_commit is not None,
    )
    if not guard.ok:
        tools.append_trace_event_tool(
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

    tools.append_trace_event_tool(
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
