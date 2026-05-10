from __future__ import annotations

from typing import Any


def control_feedback_summary(no_send_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "control_feedback_status_counts": control_feedback_status_counts(
            no_send_artifacts
        ),
        "control_feedback_suppression_reason_counts": (
            control_feedback_suppression_reason_counts(no_send_artifacts)
        ),
    }


def control_feedback_status_counts(
    no_send_artifacts: list[dict[str, Any]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for feedback in control_feedback_rows(no_send_artifacts):
        value = str(feedback.get("status") or "not_evaluated")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def control_feedback_suppression_reason_counts(
    no_send_artifacts: list[dict[str, Any]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for feedback in control_feedback_rows(no_send_artifacts):
        values = feedback.get("suppression_reasons")
        if not isinstance(values, list):
            continue
        for value in values:
            key = str(value)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def control_feedback_rows(
    no_send_artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for artifact in no_send_artifacts:
        trigger_rows = artifact.get("trigger_evaluations")
        if not isinstance(trigger_rows, list):
            continue
        for row in trigger_rows:
            if not isinstance(row, dict):
                continue
            feedback = row.get("control_feedback")
            if isinstance(feedback, dict):
                rows.append(feedback)
    return rows


__all__ = [
    "control_feedback_rows",
    "control_feedback_summary",
    "control_feedback_status_counts",
    "control_feedback_suppression_reason_counts",
]
