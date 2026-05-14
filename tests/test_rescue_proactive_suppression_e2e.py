from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_rescue_proactive_suppression_e2e import (
    build_rescue_proactive_suppression_e2e_report,
)
from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from tests.test_advanced_product_lab_runtime import _fixture_inputs


def test_rescue_to_proactive_snooze_e2e_suppresses_without_mutating_rescue(
    tmp_path: Path,
) -> None:
    session = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="rescue-proactive-suppression-e2e",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "rescue-proactive-1",
                "lab_now_minute": 10,
                "post_turn_chat_actions": [
                    {
                        "event_id": "snooze-rescue-e2e",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": "snooze",
                        "snooze_minutes": 30,
                    }
                ],
            },
            {"turn_id": "rescue-proactive-2", "lab_now_minute": 20},
        ],
    )

    report = build_rescue_proactive_suppression_e2e_report(session)

    assert report["artifact_type"] == (
        "advanced_product_lab_rescue_proactive_suppression_e2e_report"
    )
    assert report["status"] == "pass"
    assert report["journey_summary"] == {
        "rescue_proposal_presented_turn_1": True,
        "rescue_proactive_candidate_visible_turn_1": True,
        "feedback_event_projected": True,
        "rescue_proactive_candidate_suppressed_turn_2": True,
        "rescue_proposal_not_committed_by_feedback": True,
        "dashboard_mirror_suppressed_card_visible_turn_2": True,
    }
    assert report["visible_candidate_ids_by_turn"] == {
        "rescue-proactive-1": ["recommendation_prompt:0", "rescue_nudge:1"],
        "rescue-proactive-2": ["recommendation_prompt:0"],
    }
    assert report["feedback_projection_types"] == ["user_control_snooze"]
    assert report["canonical_product_mutation_allowed"] is False
    assert report["blockers"] == []
