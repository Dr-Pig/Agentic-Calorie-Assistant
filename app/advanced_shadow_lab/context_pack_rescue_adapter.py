from __future__ import annotations

from typing import Any, Mapping


def build_rescue_context_pack_adapter(
    *,
    current_budget_view: Mapping[str, Any],
    active_body_plan_view: Mapping[str, Any],
    open_proposals_view: Mapping[str, Any],
    rescue_history_summary: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_rescue_context_pack_adapter",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "current_budget_view": dict(current_budget_view),
        "active_body_plan_view": dict(active_body_plan_view),
        "open_proposals_view": dict(open_proposals_view),
        "rescue_history_summary": dict(rescue_history_summary),
        "raw_transcript_included": False,
        "blockers": [],
    }


__all__ = ["build_rescue_context_pack_adapter"]
