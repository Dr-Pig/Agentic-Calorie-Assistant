from __future__ import annotations

from typing import Any


def apply_target_attachment_schema_guidance(
    properties: dict[str, Any],
    semantic_properties: dict[str, Any],
) -> None:
    top_level = properties.get("target_attachment")
    if isinstance(top_level, dict):
        top_level["description"] = (
            "Manager-owned attach decision for the current final action. If the current turn answers an open "
            "pending follow-up and the final action commits or corrects that meal, do not leave this empty: include "
            "operation='attach_to_pending_followup' and target_resolution_source='pending_followup_state'. Use the "
            "canonical meal_thread_id/meal_version_id from active_workflow or target_candidates when available; "
            "legacy meal_id/source_meal_id are log-link refs and must not be copied into meal_thread_id."
        )
    semantic = semantic_properties.get("target_attachment")
    if isinstance(semantic, dict):
        semantic["description"] = (
            "Manager-owned attach decision. For pending follow-up answers that commit or correct after evidence, "
            "this must not be empty: use operation='attach_to_pending_followup' and "
            "target_resolution_source='pending_followup_state'. Carry canonical meal_thread_id/meal_version_id from "
            "active_workflow or target_candidates when available. legacy meal_id/source_meal_id may be copied only "
            "as legacy refs, never as meal_thread_id."
        )


__all__ = ["apply_target_attachment_schema_guidance"]
