from __future__ import annotations


def _card_packet(**card_overrides: object) -> dict:
    card = {
        "card_id": "rescue-proposal-1",
        "proposal_id": "rescue-proposal-1",
        "proposal_option_id": "option-primary",
        "recommended_days": 2,
        "daily_kcal_adjustment": -225,
        "cap_mode": "standard_15_percent",
    }
    card.update(card_overrides)
    return {
        "artifact_type": "rescue_response_card_packet",
        "status": "pass",
        "rescue_response_card": card,
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "mainline_activation_enabled": False,
        "production_scheduler_delivery_allowed": False,
    }


def _accept_contract(card_packet: dict | None = None) -> dict:
    from app.rescue.application.accept_rescue_plan_contract import (
        build_accept_rescue_plan_lab_contract,
    )

    return build_accept_rescue_plan_lab_contract(
        rescue_response_card_packet=card_packet or _card_packet(),
        accept_request={
            "action_id": "accept_rescue_plan",
            "proposal_id": "rescue-proposal-1",
            "user_id": "user-1",
            "accepted_at": "2026-05-13T10:30:00+08:00",
            "cap_mode": "standard_15_percent",
            "commit_source": "chat",
            "source_audit": {
                "surface": "chat",
                "source_event_id": "msg-accept-1",
                "run_id": "run-1",
            },
        },
    )


def _effective_policy(**overrides: object) -> dict:
    policy = {
        "artifact_type": "rescue_effective_from_policy",
        "status": "pass",
        "effective_from_posture": "today",
        "effective_from_local_date": "2026-05-13",
        "effective_start_local_time": "after_lunch",
    }
    policy.update(overrides)
    return policy


def _current_budget(**overrides: object) -> dict:
    view = {
        "user_id": "user-1",
        "local_date": "2026-05-13",
        "budget_kcal": 1800,
        "consumed_kcal": 600,
        "adjustment_kcal": 200,
        "remaining_kcal": 1000,
    }
    view.update(overrides)
    return view


def _commit_effect(
    *,
    accept_contract: dict | None = None,
    card_packet: dict | None = None,
    policy: dict | None = None,
    budget: dict | None = None,
) -> dict:
    from app.rescue.application.isolated_lab_commit_effect import (
        build_isolated_lab_rescue_commit_effect,
    )

    resolved_card = card_packet or _card_packet()
    return build_isolated_lab_rescue_commit_effect(
        accept_contract=accept_contract or _accept_contract(resolved_card),
        rescue_response_card_packet=resolved_card,
        effective_from_policy=policy or _effective_policy(),
        current_budget_view=budget or _current_budget(),
    )


def test_isolated_lab_commit_creates_daily_rescue_overlay_entries_and_refreshes_budget() -> None:
    artifact = _commit_effect()

    assert artifact["status"] == "pass"
    assert artifact["lab_enabled"] is True
    assert artifact["lab_isolated_mutation_changed"] is True
    assert artifact["lab_ledger_entry_created"] is True
    assert artifact["canonical_mutation_changed"] is False
    assert artifact["production_db_mutation_allowed"] is False

    assert artifact["proposal_status_overlay"] == {
        "proposal_id": "rescue-proposal-1",
        "proposal_status": "accepted",
        "accepted_at": "2026-05-13T10:30:00+08:00",
        "accepted_option_id": "option-primary",
        "cap_mode": "standard_15_percent",
    }
    entries = artifact["lab_ledger_entries"]
    assert [entry["local_date"] for entry in entries] == ["2026-05-13", "2026-05-14"]
    assert [entry["delta_kcal"] for entry in entries] == [-225, -225]
    assert entries[0]["effective_from"] == "2026-05-13Tafter_lunch"
    assert entries[1]["effective_from"] == "2026-05-14T00:00"

    refreshed = artifact["refreshed_current_budget_view"]
    assert refreshed["adjustment_kcal"] == 425
    assert refreshed["remaining_kcal"] == 775
    assert refreshed["rescue_overlay_runtime_adjustment_kcal"] == 225

    effect = artifact["rescue_commit_effect"]
    assert effect["ledger_entries_created"] == [entry["entry_id"] for entry in entries]
    assert effect["budget_view_refreshed"] is True
    assert effect["recommendation_posture_update_deferred_to_pr21"] is True


def test_tomorrow_effect_keeps_today_budget_numbers_when_overlay_starts_tomorrow() -> None:
    artifact = _commit_effect(
        policy=_effective_policy(
            effective_from_posture="tomorrow",
            effective_from_local_date="2026-05-14",
            effective_start_local_time="00:00",
        )
    )

    assert artifact["status"] == "pass"
    assert [entry["local_date"] for entry in artifact["lab_ledger_entries"]] == [
        "2026-05-14",
        "2026-05-15",
    ]
    refreshed = artifact["refreshed_current_budget_view"]
    assert refreshed["adjustment_kcal"] == 200
    assert refreshed["remaining_kcal"] == 1000
    assert refreshed["rescue_overlay_runtime_adjustment_kcal"] == 0


def test_commit_effect_blocks_card_drift_and_missing_budget_shape() -> None:
    card = _card_packet(proposal_id="other-proposal", recommended_days=0)
    budget = _current_budget()
    budget.pop("remaining_kcal")

    artifact = _commit_effect(card_packet=card, budget=budget)

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "accept_contract.status_not_pass",
        "accept_contract.accepted_projection_missing",
        "rescue_response_card.recommended_days_invalid",
        "current_budget_view.remaining_kcal_missing",
    ]
    assert artifact["lab_isolated_mutation_changed"] is False
    assert artifact["lab_ledger_entries"] == []


def test_commit_effect_blocks_non_pass_effective_policy() -> None:
    artifact = _commit_effect(
        policy=_effective_policy(
            status="blocked",
            effective_from_local_date="",
            effective_start_local_time="",
        )
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "effective_from_policy.status_not_pass",
        "effective_from_policy.effective_from_local_date_missing",
        "effective_from_policy.effective_start_local_time_missing",
    ]
    assert artifact["lab_runtime_effect_allowed"] is False
