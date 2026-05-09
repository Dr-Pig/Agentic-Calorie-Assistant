from __future__ import annotations


def _rescue_context() -> dict[str, object]:
    return {
        "artifact_type": "rescue_shadow_summary_context_projection",
        "status": "pass",
        "memory_summary_projection_used": True,
        "rescue_committed": False,
        "proposal_committed": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "durable_memory_written": False,
        "manager_context_injected": False,
        "proactive_sent": False,
        "recommendation_served": False,
    }


def _budget(consumed: int = 2100, effective: int = 1800) -> dict[str, int]:
    return {
        "base_budget_kcal": 1800,
        "effective_budget_kcal": effective,
        "meal_consumption_total_kcal": consumed,
    }


def _body_plan(days: int = 3, base: int = 1800, floor: int = 1200) -> dict[str, object]:
    return {
        "safety_floor_kcal": floor,
        "target_days": [
            {
                "local_date": f"2026-05-{10 + index:02d}",
                "base_budget_kcal": base,
                "calibration_adjustment_total_kcal": 0,
            }
            for index in range(days)
        ],
    }


def test_rescue_viability_packet_marks_short_horizon_recovery_viable_without_commit() -> None:
    from app.rescue.application.no_commit_viability import (
        build_rescue_no_commit_viability_shadow_packet,
    )

    packet = build_rescue_no_commit_viability_shadow_packet(
        rescue_context_projection=_rescue_context(),
        current_budget_view=_budget(consumed=2100),
        active_body_plan_view=_body_plan(days=3),
        open_proposals_view={"open_rescue_proposal_count": 0},
    )

    assert packet["artifact_type"] == "rescue_no_commit_viability_shadow_packet"
    assert packet["status"] == "pass"
    assert packet["recovery_viability"] == "viable"
    assert packet["overshoot_summary"] == {
        "meal_consumption_total_kcal": 2100,
        "effective_budget_kcal": 1800,
        "overshoot_kcal": 300,
    }
    assert packet["rescue_horizon_days"] == 3
    assert packet["daily_recovery_kcal"] == 100
    assert packet["blockers"] == []
    assert packet["proposal_card"] is None
    assert packet["candidate_copy"] is None
    assert packet["send_or_skip"] is None
    assert packet["primary_actions"] == []
    assert packet["proposal_committed"] is False
    assert packet["day_budget_mutated"] is False
    assert packet["body_plan_mutated"] is False
    assert packet["recommendation_served"] is False


def test_rescue_viability_packet_marks_strained_when_daily_cut_exceeds_ten_percent() -> None:
    from app.rescue.application.no_commit_viability import (
        build_rescue_no_commit_viability_shadow_packet,
    )

    packet = build_rescue_no_commit_viability_shadow_packet(
        rescue_context_projection=_rescue_context(),
        current_budget_view=_budget(consumed=2520),
        active_body_plan_view=_body_plan(days=3),
        open_proposals_view={"open_rescue_proposal_count": 0},
    )

    assert packet["recovery_viability"] == "strained"
    assert packet["daily_recovery_kcal"] == 240
    assert packet["target_day_checks"][0]["max_10_percent_kcal"] == 180
    assert packet["target_day_checks"][0]["max_15_percent_kcal"] == 270


def test_rescue_viability_packet_marks_non_viable_above_fifteen_percent() -> None:
    from app.rescue.application.no_commit_viability import (
        build_rescue_no_commit_viability_shadow_packet,
    )

    packet = build_rescue_no_commit_viability_shadow_packet(
        rescue_context_projection=_rescue_context(),
        current_budget_view=_budget(consumed=2700),
        active_body_plan_view=_body_plan(days=3),
        open_proposals_view={"open_rescue_proposal_count": 0},
    )

    assert packet["recovery_viability"] == "non_viable"
    assert packet["daily_recovery_kcal"] == 300
    assert "daily_compression_above_15_percent" in packet["blockers"]
    assert packet["proposal_committed"] is False
    assert packet["rescue_committed"] is False


def test_rescue_viability_packet_blocks_missing_inputs_and_open_proposals() -> None:
    from app.rescue.application.no_commit_viability import (
        build_rescue_no_commit_viability_shadow_packet,
    )

    packet = build_rescue_no_commit_viability_shadow_packet(
        rescue_context_projection=_rescue_context(),
        current_budget_view={},
        active_body_plan_view=_body_plan(days=3),
        open_proposals_view={"open_rescue_proposal_count": 1},
    )

    assert packet["status"] == "blocked"
    assert packet["recovery_viability"] == "blocked"
    assert "missing_budget_view" in packet["blockers"]
    assert "open_rescue_proposal" in packet["blockers"]
    assert packet["target_day_checks"] == []
    assert packet["runtime_effect_allowed"] is False


def test_rescue_viability_packet_rejects_context_claim_drift() -> None:
    from app.rescue.application.no_commit_viability import (
        build_rescue_no_commit_viability_shadow_packet,
    )

    context = _rescue_context()
    context["proposal_committed"] = True

    packet = build_rescue_no_commit_viability_shadow_packet(
        rescue_context_projection=context,
        current_budget_view=_budget(),
        active_body_plan_view=_body_plan(days=3),
        open_proposals_view={"open_rescue_proposal_count": 0},
    )

    assert packet["status"] == "blocked"
    assert packet["recovery_viability"] == "blocked"
    assert "rescue_context_projection.proposal_committed" in packet["blockers"]
    assert packet["proposal_committed"] is False
    assert packet["day_budget_mutated"] is False
