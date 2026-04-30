from __future__ import annotations

from typing import Any

from ...runtime.contracts.phase_a import CurrentTurnContextV1, HistoryExpansionResult


def enrich_current_turn_context(
    *,
    current_turn_context: CurrentTurnContextV1,
    selected_candidate: dict[str, Any] | None,
    activation_result: HistoryExpansionResult | None,
    attachment_disposition_hint: str | None = None,
) -> CurrentTurnContextV1:
    target_candidates = [dict(item) for item in current_turn_context.candidate_attachment_targets]
    if selected_candidate is not None:
        selected_target_id = str(selected_candidate.get("meal_thread_id") or "")
        selected_entry = {
            "target_object_type": "meal_thread",
            "target_object_id": selected_target_id,
            "source": str(selected_candidate.get("source") or "history_expansion"),
            "confidence": "high",
        }
        if attachment_disposition_hint:
            selected_entry["attachment_disposition_hint"] = attachment_disposition_hint
        target_candidates = [
            selected_entry,
            *[item for item in target_candidates if str(item.get("target_object_id") or "") != selected_target_id],
        ]
    source_views = dict(current_turn_context.source_views)
    source_view = source_views.get("candidate_attachment_targets")
    if source_view is not None:
        source_views["candidate_attachment_targets"] = source_view.model_copy(
            update={
                "availability": "present" if target_candidates else "none",
                "summary": {
                    "count": len(target_candidates),
                    "history_expansion_meal_candidates": len(activation_result.meal_candidates)
                    if activation_result is not None
                    else 0,
                },
            }
        )
    runtime_summary = dict(current_turn_context.current_turn_runtime_summary)
    runtime_summary.update(
        {
            "history_expansion_applied": activation_result is not None,
            "history_expansion_candidate_count": len(activation_result.meal_candidates)
            if activation_result is not None
            else 0,
        }
    )
    return current_turn_context.model_copy(
        update={
            "candidate_attachment_targets": target_candidates,
            "source_views": source_views,
            "current_turn_runtime_summary": runtime_summary,
        }
    )


__all__ = ["enrich_current_turn_context"]
