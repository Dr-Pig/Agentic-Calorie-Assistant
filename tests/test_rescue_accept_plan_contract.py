from __future__ import annotations


def _card_packet() -> dict:
    return {
        "artifact_type": "rescue_response_card_packet",
        "status": "pass",
        "rescue_response_card": {
            "card_id": "rescue-proposal-1",
            "proposal_id": "rescue-proposal-1",
            "recommended_days": 2,
            "daily_kcal_adjustment": -225,
            "cap_mode": "standard_15_percent",
            "effective_from": "today",
            "primary_actions": [
                {"action_id": "accept_rescue_plan", "label": "接受這個方案"},
                {"action_id": "dismiss_rescue_plan", "label": "先不要"},
            ],
        },
        "proposal_container_ref": {
            "proposal_id": "rescue-proposal-1",
            "proposal_type": "rescue",
            "status": "presented_contract_only",
            "mutation_authority": False,
        },
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "mainline_activation_enabled": False,
        "production_scheduler_delivery_allowed": False,
        "proposal_committed": False,
        "ledger_entry_created": False,
    }


def _accept_request(**overrides: object) -> dict:
    request = {
        "action_id": "accept_rescue_plan",
        "proposal_id": "rescue-proposal-1",
        "user_id": "user-1",
        "accepted_at": "2026-05-13T10:30:00+00:00",
        "cap_mode": "standard_15_percent",
        "commit_source": "chat",
        "source_audit": {
            "surface": "chat",
            "source_event_id": "msg-accept-1",
            "run_id": "run-1",
        },
    }
    request.update(overrides)
    return request


def test_accept_contract_projects_accepted_proposal_without_canonical_mutation() -> None:
    from app.rescue.application.accept_rescue_plan_contract import (
        build_accept_rescue_plan_lab_contract,
    )

    artifact = build_accept_rescue_plan_lab_contract(
        rescue_response_card_packet=_card_packet(),
        accept_request=_accept_request(),
    )

    assert artifact["artifact_type"] == "accept_rescue_plan_lab_contract"
    assert artifact["status"] == "pass"
    assert artifact["accepted_projection"] == {
        "proposal_id": "rescue-proposal-1",
        "proposal_status": "accepted",
        "user_id": "user-1",
        "accepted_at": "2026-05-13T10:30:00+00:00",
        "cap_mode": "standard_15_percent",
        "commit_source": "chat",
        "source_audit": {
            "surface": "chat",
            "source_event_id": "msg-accept-1",
            "run_id": "run-1",
        },
    }
    assert artifact["required_next_effects"] == [
        "update_proposal_container_status",
        "create_rescue_overlay_ledger_entries",
        "refresh_current_budget_view",
        "request_recommendation_posture_refresh",
    ]
    assert artifact["ledger_entry_creation_deferred_to_pr19"] is True
    assert artifact["canonical_mutation_changed"] is False
    assert artifact["production_db_mutation_allowed"] is False
    assert artifact["mainline_activation_enabled"] is False


def test_accept_contract_supports_chat_ui_and_smart_chip_sources() -> None:
    from app.rescue.application.accept_rescue_plan_contract import (
        build_accept_rescue_plan_lab_contract,
    )

    for source in ("chat", "ui", "smart_chip"):
        artifact = build_accept_rescue_plan_lab_contract(
            rescue_response_card_packet=_card_packet(),
            accept_request=_accept_request(commit_source=source),
        )
        assert artifact["status"] == "pass"
        assert artifact["accepted_projection"]["commit_source"] == source


def test_accept_contract_rejects_missing_scope_time_and_source_audit() -> None:
    from app.rescue.application.accept_rescue_plan_contract import (
        build_accept_rescue_plan_lab_contract,
    )

    artifact = build_accept_rescue_plan_lab_contract(
        rescue_response_card_packet=_card_packet(),
        accept_request=_accept_request(
            user_id="",
            accepted_at="2026-05-13",
            source_audit={"surface": "chat"},
        ),
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "accept_request.user_id_missing",
        "accept_request.accepted_at_not_iso_datetime",
        "accept_request.source_audit.source_event_id_missing",
        "accept_request.source_audit.run_id_missing",
    ]
    assert artifact["accepted_projection"] is None
    assert artifact["canonical_mutation_changed"] is False


def test_accept_contract_rejects_wrong_action_or_card_drift() -> None:
    from app.rescue.application.accept_rescue_plan_contract import (
        build_accept_rescue_plan_lab_contract,
    )

    artifact = build_accept_rescue_plan_lab_contract(
        rescue_response_card_packet=_card_packet(),
        accept_request=_accept_request(
            action_id="dismiss_rescue_plan",
            proposal_id="other-proposal",
            cap_mode="aggressive_20_percent",
            commit_source="email",
        ),
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "accept_request.action_id_not_accept_rescue_plan",
        "accept_request.proposal_id_mismatch",
        "accept_request.cap_mode_mismatch",
        "accept_request.commit_source_unsupported:email",
    ]
    assert artifact["lab_isolated_mutation_allowed"] is False
