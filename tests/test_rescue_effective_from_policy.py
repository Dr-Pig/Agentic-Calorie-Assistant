from __future__ import annotations

from datetime import datetime, timezone

from app.rescue.application.effective_from_policy import (
    build_rescue_effective_from_policy,
)


def _option_result() -> dict:
    return {
        "artifact_type": "rescue_option_generation_result",
        "status": "pass",
        "rescue_needed": True,
        "selected_option": {
            "rescue_family": "short_horizon_spread",
            "recommended_days": 2,
            "daily_kcal_adjustment": -225,
            "cap_mode": "standard_15_percent",
            "recovery_viability": "strained",
            "special_posture": "strained_standard_spread",
        },
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
    }


def test_effective_from_today_before_11_local_for_short_horizon_spread() -> None:
    policy = build_rescue_effective_from_policy(
        option_generation_result=_option_result(),
        accepted_at_local=datetime(2026, 5, 13, 10, 59, tzinfo=timezone.utc),
        local_date="2026-05-13",
    )

    assert policy["status"] == "pass"
    assert policy["rescue_family"] == "short_horizon_spread"
    assert policy["effective_from_posture"] == "today"
    assert policy["effective_from_local_date"] == "2026-05-13"
    assert policy["effective_start_local_time"] == "after_lunch"
    assert policy["boundary_local_time"] == "11:00"


def test_effective_from_tomorrow_at_11_local_boundary() -> None:
    policy = build_rescue_effective_from_policy(
        option_generation_result=_option_result(),
        accepted_at_local=datetime(2026, 5, 13, 11, 0, tzinfo=timezone.utc),
        local_date="2026-05-13",
    )

    assert policy["status"] == "pass"
    assert policy["effective_from_posture"] == "tomorrow"
    assert policy["effective_from_local_date"] == "2026-05-14"
    assert policy["effective_start_local_time"] == "00:00"


def test_effective_from_tomorrow_after_11_local_boundary() -> None:
    policy = build_rescue_effective_from_policy(
        option_generation_result=_option_result(),
        accepted_at_local=datetime(2026, 5, 13, 15, 30, tzinfo=timezone.utc),
        local_date="2026-05-13",
    )

    assert policy["effective_from_posture"] == "tomorrow"
    assert policy["effective_from_local_date"] == "2026-05-14"


def test_effective_from_policy_blocks_without_selected_option() -> None:
    option = _option_result()
    option["selected_option"] = None

    policy = build_rescue_effective_from_policy(
        option_generation_result=option,
        accepted_at_local=datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc),
        local_date="2026-05-13",
    )

    assert policy["status"] == "blocked"
    assert policy["blockers"] == ["option_generation_result.missing_selected_option"]
    assert policy["effective_from_local_date"] is None
    assert policy["runtime_effect_allowed"] is False


def test_effective_from_policy_never_commits_or_mutates() -> None:
    policy = build_rescue_effective_from_policy(
        option_generation_result=_option_result(),
        accepted_at_local=datetime(2026, 5, 13, 9, 30, tzinfo=timezone.utc),
        local_date="2026-05-13",
    )

    assert policy["proposal_committed"] is False
    assert policy["ledger_entry_created"] is False
    assert policy["canonical_mutation_changed"] is False
    assert policy["production_scheduler_delivery_allowed"] is False
