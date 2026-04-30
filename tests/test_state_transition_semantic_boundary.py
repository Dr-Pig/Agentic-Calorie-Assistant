from __future__ import annotations

from app.intake.application.state_transition import determine_meal_status


def test_route_target_clarify_is_not_a_standalone_commit_gate() -> None:
    status = determine_meal_status(
        payload_action_taken="direct_answer",
        payload_route_target="clarify_user_private",
        estimated_kcal=420,
        trace_contract={},
        quality_signals={},
    )

    assert status == "completed_meal"
