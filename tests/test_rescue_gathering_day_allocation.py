from __future__ import annotations

from app.rescue.application.gathering_day_allocation import (
    build_gathering_day_allocation_result,
)
from app.rescue.application.read_model_input_packet import (
    build_rescue_read_model_input_packet,
)


def _read_model_packet() -> dict:
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
                "meal_consumption_total_kcal": 900,
                "remaining_kcal": 900,
            },
            "recent_committed_meals_view": {"meal_count": 1, "meals": []},
            "active_body_plan_view": {
                "safety_floor_kcal": 1500,
                "target_days": [
                    {
                        "local_date": "2026-05-14",
                        "base_budget_kcal": 1800,
                        "calibration_adjustment_total_kcal": 0,
                    },
                    {
                        "local_date": "2026-05-15",
                        "base_budget_kcal": 1800,
                        "calibration_adjustment_total_kcal": 0,
                    },
                ],
            },
            "open_proposals_view": {"open_rescue_proposal_count": 0},
        }
    ).model_dump()


def _context(*, request_type: str = "informational") -> dict:
    return {
        "event_id": "gathering-1",
        "event_label": "family dinner",
        "event_local_date": "2026-05-16",
        "request_type": request_type,
        "reserve_kcal": 400,
        "planning_days_before_event": 2,
        "source_refs": ["planned_event:gathering-1"],
    }


def test_gathering_day_informational_request_does_not_create_proposal() -> None:
    result = build_gathering_day_allocation_result(
        gathering_context=_context(request_type="informational"),
        read_model_input_packet=_read_model_packet(),
    )

    assert result["status"] == "pass"
    assert result["mode"] == "informational_allocation"
    assert result["proposal_seed_created"] is False
    assert result["confirmation_required"] is False
    assert result["guidance_packet"]["primary_surface"] == "chat"
    assert result["ledger_entry_created"] is False


def test_gathering_day_explicit_reserve_request_creates_confirmation_seed() -> None:
    result = build_gathering_day_allocation_result(
        gathering_context=_context(request_type="reserve_budget"),
        read_model_input_packet=_read_model_packet(),
    )

    assert result["status"] == "pass"
    assert result["mode"] == "reserve_budget_proposal_seed"
    assert result["proposal_seed_created"] is True
    assert result["confirmation_required"] is True
    assert result["planned_event_allocation"]["deterministic_allocation"][
        "daily_kcal_adjustment"
    ] == -200
    assert result["proposal_commit_allowed"] is False


def test_gathering_day_set_budget_request_uses_same_confirmation_gate() -> None:
    result = build_gathering_day_allocation_result(
        gathering_context=_context(request_type="set_budget"),
        read_model_input_packet=_read_model_packet(),
    )

    assert result["status"] == "pass"
    assert result["mode"] == "reserve_budget_proposal_seed"
    assert result["confirmation_required"] is True
    assert result["proposal_commit_allowed"] is False


def test_gathering_day_unknown_request_asks_clarification_without_proposal() -> None:
    result = build_gathering_day_allocation_result(
        gathering_context=_context(request_type="maybe"),
        read_model_input_packet=_read_model_packet(),
    )

    assert result["status"] == "blocked"
    assert result["mode"] == "needs_clarification"
    assert result["proposal_seed_created"] is False
    assert result["blockers"] == ["gathering_context.request_type_unsupported:maybe"]
