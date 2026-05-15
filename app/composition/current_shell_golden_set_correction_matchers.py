from __future__ import annotations

from typing import Any


def matches_remove_meal_workflow(actual: dict[str, Any], actual_item: Any) -> bool:
    return (
        actual_item in {"correction", "correction_write", "correction_applied", "remove_meal"}
        and actual.get("final_action") == "correction_applied"
        and actual.get("canonical_commit_status") == "committed"
        and actual.get("old_version_superseded") is True
        and actual.get("removed_versions_excluded_from_ledger") is True
    )


def matches_unique_recent_or_named_slot_attachment(actual_item: Any) -> bool:
    if not isinstance(actual_item, dict):
        return False
    source = str(actual_item.get("target_resolution_source") or "").strip()
    operation = str(actual_item.get("operation") or actual_item.get("correction_operation") or "").strip()
    return bool(actual_item.get("meal_thread_id")) and operation == "remove_meal" and source in {
        "recent_committed_meal",
        "resolve_correction_target",
        "tool_result_validated",
        "manager_target_proposal_validated",
    }
