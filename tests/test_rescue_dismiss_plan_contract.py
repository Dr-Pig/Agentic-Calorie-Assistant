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
            "primary_actions": [
                {"action_id": "accept_rescue_plan", "label": "接受這個方案"},
                {"action_id": "dismiss_rescue_plan", "label": "先不要"},
            ],
        },
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "mainline_activation_enabled": False,
        "production_scheduler_delivery_allowed": False,
        "proposal_committed": False,
        "ledger_entry_created": False,
    }


def _dismiss_request(**overrides: object) -> dict:
    request = {
        "action_id": "dismiss_rescue_plan",
        "proposal_id": "rescue-proposal-1",
        "user_id": "user-1",
        "dismissed_at": "2026-05-13T10:35:00+00:00",
        "dismiss_source": "chat",
        "source_audit": {
            "surface": "chat",
            "source_event_id": "msg-dismiss-1",
            "run_id": "run-1",
        },
    }
    request.update(overrides)
    return request


def test_dismiss_contract_closes_active_proposal_without_canonical_mutation() -> None:
    from app.rescue.application.dismiss_rescue_plan_contract import (
        build_dismiss_rescue_plan_lab_contract,
    )

    artifact = build_dismiss_rescue_plan_lab_contract(
        rescue_response_card_packet=_card_packet(),
        dismiss_request=_dismiss_request(),
    )

    assert artifact["artifact_type"] == "dismiss_rescue_plan_lab_contract"
    assert artifact["status"] == "pass"
    assert artifact["dismissed_projection"] == {
        "proposal_id": "rescue-proposal-1",
        "proposal_status": "dismissed",
        "user_id": "user-1",
        "dismissed_at": "2026-05-13T10:35:00+00:00",
        "dismiss_source": "chat",
        "dismiss_reason": None,
        "source_audit": {
            "surface": "chat",
            "source_event_id": "msg-dismiss-1",
            "run_id": "run-1",
        },
    }
    assert artifact["required_next_effects"] == [
        "update_proposal_container_status",
        "remove_from_active_proposal_inbox",
        "append_history_audit_entry",
        "suppress_same_proposal_redelivery",
    ]
    assert artifact["same_proposal_redelivery_allowed"] is False
    assert artifact["canonical_mutation_changed"] is False
    assert artifact["production_db_mutation_allowed"] is False
    assert artifact["mainline_activation_enabled"] is False


def test_dismiss_reason_is_optional_and_preserved_when_present() -> None:
    from app.rescue.application.dismiss_rescue_plan_contract import (
        build_dismiss_rescue_plan_lab_contract,
    )

    artifact = build_dismiss_rescue_plan_lab_contract(
        rescue_response_card_packet=_card_packet(),
        dismiss_request=_dismiss_request(dismiss_reason="today feels too strict"),
    )

    assert artifact["status"] == "pass"
    assert artifact["dismiss_reason_required"] is False
    assert artifact["dismissed_projection"]["dismiss_reason"] == "today feels too strict"


def test_dismiss_contract_supports_chat_ui_and_smart_chip_sources() -> None:
    from app.rescue.application.dismiss_rescue_plan_contract import (
        build_dismiss_rescue_plan_lab_contract,
    )

    for source in ("chat", "ui", "smart_chip"):
        artifact = build_dismiss_rescue_plan_lab_contract(
            rescue_response_card_packet=_card_packet(),
            dismiss_request=_dismiss_request(dismiss_source=source),
        )
        assert artifact["status"] == "pass"
        assert artifact["dismissed_projection"]["dismiss_source"] == source


def test_dismiss_contract_rejects_missing_scope_time_and_source_audit() -> None:
    from app.rescue.application.dismiss_rescue_plan_contract import (
        build_dismiss_rescue_plan_lab_contract,
    )

    artifact = build_dismiss_rescue_plan_lab_contract(
        rescue_response_card_packet=_card_packet(),
        dismiss_request=_dismiss_request(
            user_id="",
            dismissed_at="2026-05-13",
            source_audit={"surface": "chat"},
        ),
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "dismiss_request.user_id_missing",
        "dismiss_request.dismissed_at_not_iso_datetime",
        "dismiss_request.source_audit.source_event_id_missing",
        "dismiss_request.source_audit.run_id_missing",
    ]
    assert artifact["dismissed_projection"] is None


def test_dismiss_contract_rejects_wrong_action_card_drift_and_side_effects() -> None:
    from app.rescue.application.dismiss_rescue_plan_contract import (
        build_dismiss_rescue_plan_lab_contract,
    )

    artifact = build_dismiss_rescue_plan_lab_contract(
        rescue_response_card_packet=_card_packet(),
        dismiss_request=_dismiss_request(
            action_id="accept_rescue_plan",
            proposal_id="other-proposal",
            dismiss_source="email",
            switch_to_backup_proposal_id="backup-2",
            permanent_rescue_suppression=True,
            snooze_until="2026-05-14T10:00:00+00:00",
            dismiss_reason_required=True,
        ),
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "dismiss_request.action_id_not_dismiss_rescue_plan",
        "dismiss_request.proposal_id_mismatch",
        "dismiss_request.dismiss_source_unsupported:email",
        "dismiss_request.backup_switching_forbidden",
        "dismiss_request.permanent_rescue_suppression_forbidden",
        "dismiss_request.snooze_forbidden",
        "dismiss_request.dismiss_reason_required_forbidden",
    ]
    assert artifact["backup_switching_allowed"] is False
    assert artifact["permanent_rescue_suppression"] is False
    assert artifact["snooze_created"] is False
