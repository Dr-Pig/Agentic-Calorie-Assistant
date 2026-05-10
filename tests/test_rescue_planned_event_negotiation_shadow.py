from __future__ import annotations

from app.rescue.application.proposal_shaping_output_validator_shadow import (
    validate_rescue_proposal_shaping_output_shadow,
)


def test_planned_event_rescue_packet_requires_explicit_accept_without_mutation() -> None:
    from app.rescue.application.planned_event_negotiation_shadow import (
        build_planned_event_rescue_negotiation_shadow_packet,
    )

    packet = build_planned_event_rescue_negotiation_shadow_packet(
        planned_event_context=_planned_event_context(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 0},
        proposal_shaping_candidate=_proposal_candidate(),
    )

    assert packet["artifact_type"] == "rescue_planned_event_negotiation_shadow_packet"
    assert packet["status"] == "pass"
    assert packet["planned_event_context"]["event_id"] == "event-buffet-1"
    assert packet["deterministic_allocation"]["reserve_kcal"] == 800
    assert packet["deterministic_allocation"]["daily_kcal_adjustment"] == -200
    assert packet["proposal_candidate"] == {
        "headline": "Keep 800 kcal open for Saturday buffet",
        "summary": "Shift 200 kcal across four days before the event.",
        "primary_actions": ["accept_rescue_plan", "dismiss_rescue_plan"],
        "source_refs": ["planned_event:event-buffet-1"],
    }
    assert packet["explicit_accept_required"] is True
    assert packet["budget_mutation_allowed"] is False
    assert packet["proposal_committed"] is False
    assert packet["rescue_committed"] is False
    assert packet["ledger_entry_created"] is False
    assert packet["day_budget_mutated"] is False
    assert packet["manager_context_packet_changed"] is False
    assert "not_proposal_container_write" in packet["non_claims"]


def test_planned_event_rescue_distinguishes_general_guidance_from_budget_plan() -> None:
    from app.rescue.application.planned_event_negotiation_shadow import (
        build_planned_event_rescue_negotiation_shadow_packet,
    )

    packet = build_planned_event_rescue_negotiation_shadow_packet(
        planned_event_context={
            **_planned_event_context(),
            "intent_kind": "general_event_guidance",
        },
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 0},
        proposal_shaping_candidate=_proposal_candidate(),
    )

    assert packet["status"] == "blocked"
    assert "planned_event_context.not_budget_rescue_intent" in packet["blockers"]
    assert packet["proposal_candidate"] is None
    assert packet["explicit_accept_required"] is True
    assert packet["budget_mutation_allowed"] is False


def test_planned_event_rescue_blocks_open_proposal_and_candidate_authority() -> None:
    from app.rescue.application.planned_event_negotiation_shadow import (
        build_planned_event_rescue_negotiation_shadow_packet,
    )

    candidate = _proposal_candidate()
    candidate["proposal_committed"] = True
    packet = build_planned_event_rescue_negotiation_shadow_packet(
        planned_event_context=_planned_event_context(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 1},
        proposal_shaping_candidate=candidate,
    )

    assert packet["status"] == "blocked"
    assert "open_proposals_view.open_rescue_proposal" in packet["blockers"]
    assert "proposal_shaping_candidate.proposal_committed" in packet["blockers"]
    assert packet["proposal_candidate"] is None
    assert packet["proposal_committed"] is False
    assert packet["day_budget_mutated"] is False


def test_planned_event_rescue_reuses_existing_shaping_output_validator_boundary() -> None:
    from app.rescue.application.planned_event_negotiation_shadow import (
        build_planned_event_rescue_negotiation_shadow_packet,
    )

    packet = build_planned_event_rescue_negotiation_shadow_packet(
        planned_event_context=_planned_event_context(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 0},
        proposal_shaping_candidate=_proposal_candidate(),
    )
    validation = validate_rescue_proposal_shaping_output_shadow(
        proposal_shaping_input_shadow_packet=packet["proposal_shaping_input_shadow"],
        candidate_output={
            "rubric": {
                "future_oriented": True,
                "no_shame": True,
                "not_user_facing": True,
                "fixture_only": True,
            },
        },
    )

    assert validation["status"] == "pass"
    assert validation["runtime_effect_allowed"] is False
    assert validation["proposal_committed"] is False


def _planned_event_context() -> dict[str, object]:
    return {
        "event_id": "event-buffet-1",
        "intent_kind": "planned_event_budget_rescue",
        "event_label": "Saturday buffet",
        "event_local_date": "2026-05-16",
        "reserve_kcal": 800,
        "planning_days_before_event": 4,
        "source_refs": ["planned_event:event-buffet-1"],
    }


def _budget_view() -> dict[str, object]:
    return {
        "current_date": "2026-05-12",
        "remaining_budget_kcal": 500,
        "effective_budget_kcal": 1800,
        "runtime_effect_allowed": False,
        "day_budget_mutated": False,
    }


def _body_plan_view() -> dict[str, object]:
    return {
        "safety_floor_kcal": 1200,
        "target_days": [
            {"local_date": "2026-05-12", "base_budget_kcal": 1800},
            {"local_date": "2026-05-13", "base_budget_kcal": 1800},
            {"local_date": "2026-05-14", "base_budget_kcal": 1800},
            {"local_date": "2026-05-15", "base_budget_kcal": 1800},
        ],
        "body_plan_mutated": False,
    }


def _proposal_candidate() -> dict[str, object]:
    return {
        "headline": "Keep 800 kcal open for Saturday buffet",
        "summary": "Shift 200 kcal across four days before the event.",
        "primary_actions": ["accept_rescue_plan", "dismiss_rescue_plan"],
        "rubric": {"future_oriented": True, "no_shame": True, "fixture_only": True},
        "proposal_committed": False,
        "day_budget_mutated": False,
    }
