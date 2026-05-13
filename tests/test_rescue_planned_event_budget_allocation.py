from __future__ import annotations

from app.rescue.application.planned_event_budget_allocation import (
    build_planned_event_budget_allocation,
)
from app.rescue.application.read_model_input_packet import (
    build_rescue_read_model_input_packet,
)


def _read_model_packet(*, base_budget: int = 1800, floor: int = 1500) -> dict:
    return build_rescue_read_model_input_packet(
        {
            "artifact_type": "rescue_ingress_event",
            "scope_keys": {
                "user_id": "user-1",
                "workspace_id": "workspace-1",
                "project_id": "project-1",
                "surface": "advanced_lab",
                "run_id": "run-1",
            },
            "current_budget_view": {
                "local_date": "2026-05-13",
                "base_budget_kcal": 1800,
                "effective_budget_kcal": 1800,
                "meal_consumption_total_kcal": 1200,
                "remaining_kcal": 600,
            },
            "recent_committed_meals_view": {"meal_count": 1, "meals": []},
            "active_body_plan_view": {
                "safety_floor_kcal": floor,
                "target_days": [
                    {
                        "local_date": "2026-05-14",
                        "base_budget_kcal": base_budget,
                        "calibration_adjustment_total_kcal": 0,
                    },
                    {
                        "local_date": "2026-05-15",
                        "base_budget_kcal": base_budget,
                        "calibration_adjustment_total_kcal": 0,
                    },
                ],
            },
            "open_proposals_view": {"open_rescue_proposal_count": 0},
        }
    ).model_dump()


def _planned_event() -> dict:
    return {
        "event_id": "event-hotpot-1",
        "event_label": "hotpot dinner",
        "event_local_date": "2026-05-16",
        "reserve_kcal": 400,
        "planning_days_before_event": 2,
        "source_refs": ["planned_event:event-hotpot-1"],
    }


def test_planned_event_allocation_builds_confirmation_required_proposal_seed() -> None:
    result = build_planned_event_budget_allocation(
        planned_event_context=_planned_event(),
        read_model_input_packet=_read_model_packet(),
    )

    assert result["status"] == "pass"
    assert result["proposal_kind"] == "planned_event_budget_allocation"
    assert result["confirmation_required"] is True
    assert result["proposal_commit_allowed"] is False
    assert result["deterministic_allocation"] == {
        "reserve_kcal": 400,
        "planning_days": 2,
        "daily_kcal_adjustment": -200,
        "cap_mode": "planned_event_pre_allocation",
        "target_day_count": 2,
    }
    assert result["proposal_shaping_seed"]["special_posture"] == "planned_event_pre_allocation"
    assert result["ledger_entry_created"] is False


def test_planned_event_allocation_blocks_below_safety_floor() -> None:
    result = build_planned_event_budget_allocation(
        planned_event_context=_planned_event(),
        read_model_input_packet=_read_model_packet(base_budget=1600, floor=1500),
    )

    assert result["status"] == "blocked"
    assert "allocation.below_safety_floor" in result["blockers"]
    assert result["proposal_commit_allowed"] is False
    assert result["target_day_checks"][0]["candidate_effective_budget_kcal"] == 1400


def test_planned_event_allocation_blocks_missing_event_contract() -> None:
    event = _planned_event()
    event["event_id"] = ""

    result = build_planned_event_budget_allocation(
        planned_event_context=event,
        read_model_input_packet=_read_model_packet(),
    )

    assert result["status"] == "blocked"
    assert result["blockers"] == ["planned_event_context.event_id_missing"]
    assert result["deterministic_allocation"]["daily_kcal_adjustment"] == -200


def test_planned_event_allocation_blocks_open_rescue_proposal() -> None:
    packet = _read_model_packet()
    packet["open_proposals_view"]["open_rescue_proposal_count"] = 1

    result = build_planned_event_budget_allocation(
        planned_event_context=_planned_event(),
        read_model_input_packet=packet,
    )

    assert result["status"] == "blocked"
    assert result["blockers"] == ["open_proposals_view.open_rescue_proposal"]
    assert result["runtime_effect_allowed"] is False
