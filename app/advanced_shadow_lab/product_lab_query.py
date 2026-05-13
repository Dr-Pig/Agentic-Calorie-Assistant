from __future__ import annotations

from typing import Any, Mapping


def run_product_lab_query(
    *,
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    current_budget_view = _mapping(fixture_inputs.get("current_budget_view"))
    active_body_plan_view = _mapping(fixture_inputs.get("active_body_plan_view"))
    open_proposals_view = _mapping(fixture_inputs.get("open_proposals_view"))
    blockers: list[str] = []
    if not current_budget_view:
        blockers.append("current_budget_view.missing")
    if not active_body_plan_view:
        blockers.append("active_body_plan_view.missing")
    source_refs = [
        "read_model:current_budget_view",
        "read_model:active_body_plan_view",
        *(
            ["read_model:open_proposals_view"]
            if open_proposals_view
            else []
        ),
    ]
    return {
        "artifact_type": "advanced_product_lab_query_runtime_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "current_budget_view": dict(current_budget_view),
        "active_body_plan_view": dict(active_body_plan_view),
        "open_proposals_view": dict(open_proposals_view),
        "source_refs": source_refs,
        "raw_transcript_included": False,
        "blockers": blockers,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["run_product_lab_query"]
