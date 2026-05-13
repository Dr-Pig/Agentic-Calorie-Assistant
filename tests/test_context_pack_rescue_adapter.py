from __future__ import annotations

from app.advanced_shadow_lab.context_pack_rescue_adapter import (
    build_rescue_context_pack_adapter,
)


def test_rescue_context_pack_adapter_projects_structured_rescue_inputs() -> None:
    artifact = build_rescue_context_pack_adapter(
        current_budget_view={"remaining_kcal": 320},
        active_body_plan_view={"daily_target_kcal": 1800},
        open_proposals_view={"active_proposal_ids": ["rp-1"]},
        rescue_history_summary={"accepted_count_30d": 2},
    )

    assert artifact["artifact_type"] == "advanced_product_lab_rescue_context_pack_adapter"
    assert artifact["status"] == "pass"
    assert artifact["current_budget_view"]["remaining_kcal"] == 320
    assert artifact["open_proposals_view"]["active_proposal_ids"] == ["rp-1"]
    assert artifact["rescue_history_summary"]["accepted_count_30d"] == 2
    assert artifact["raw_transcript_included"] is False
