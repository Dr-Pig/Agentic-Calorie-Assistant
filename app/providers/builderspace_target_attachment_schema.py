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
            "operation='attach_to_pending_followup' and target_resolution_source='pending_followup_state', plus "
            "meal_id or source_meal_id when context provides one."
        )
    semantic = semantic_properties.get("target_attachment")
    if isinstance(semantic, dict):
        semantic["description"] = (
            "Manager-owned attach decision. For pending follow-up answers that commit or correct after evidence, "
            "this must not be empty: use operation='attach_to_pending_followup' and "
            "target_resolution_source='pending_followup_state', carrying meal_id/source_meal_id when available."
        )


__all__ = ["apply_target_attachment_schema_guidance"]
