from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_recommendation_proactive_feedback_e2e import (
    build_recommendation_proactive_feedback_e2e_report,
)
from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from tests.test_advanced_product_lab_runtime import _fixture_inputs


def test_recommendation_to_proactive_to_feedback_e2e_suppresses_next_prompt(
    tmp_path: Path,
) -> None:
    session = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="recommendation-proactive-feedback-e2e",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "rec-proactive-feedback-1",
                "lab_now_minute": 10,
                "post_turn_chat_actions": [
                    {
                        "event_id": "dismiss-rec-e2e",
                        "target_candidate_id": "recommendation_prompt:0",
                        "action": "dismiss",
                        "dismiss_reason": "too_frequent",
                        "next_signal_required": "user_reopens_recommendation_prompts",
                    }
                ],
            },
            {"turn_id": "rec-proactive-feedback-2", "lab_now_minute": 20},
        ],
    )

    report = build_recommendation_proactive_feedback_e2e_report(session)

    assert report["artifact_type"] == (
        "advanced_product_lab_recommendation_proactive_feedback_e2e_report"
    )
    assert report["status"] == "pass"
    assert report["journey_summary"] == {
        "recommendation_selected_primary_id": "golden-1",
        "recommendation_proactive_candidate_visible_turn_1": True,
        "feedback_event_projected": True,
        "recommendation_proactive_candidate_suppressed_turn_2": True,
        "dashboard_mirror_suppressed_card_visible_turn_2": True,
    }
    assert report["visible_candidate_ids_by_turn"] == {
        "rec-proactive-feedback-1": ["recommendation_prompt:0", "rescue_nudge:1"],
        "rec-proactive-feedback-2": ["rescue_nudge:1"],
    }
    assert report["feedback_projection_types"] == ["user_control_suppression"]
    assert report["mainline_activation_enabled"] is False
    assert report["canonical_product_mutation_allowed"] is False
    assert report["blockers"] == []
