from __future__ import annotations

import json


def _card_packet() -> dict:
    return {
        "artifact_type": "rescue_response_card_packet",
        "status": "pass",
        "rescue_response_card": {
            "proposal_id": "rescue-proposal-1",
            "recommended_days": 2,
            "daily_kcal_adjustment": -225,
            "cap_mode": "standard_15_percent",
        },
        "raw_trace": {"secret": "raw_secret_should_not_render"},
    }


def _accept_contract() -> dict:
    return {
        "artifact_type": "accept_rescue_plan_lab_contract",
        "status": "pass",
        "accepted_projection": {
            "proposal_id": "rescue-proposal-1",
            "proposal_status": "accepted",
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
    }


def _commit_effect() -> dict:
    return {
        "artifact_type": "isolated_lab_rescue_commit_effect",
        "status": "pass",
        "proposal_status_overlay": {
            "proposal_id": "rescue-proposal-1",
            "proposal_status": "accepted",
            "accepted_at": "2026-05-13T10:30:00+08:00",
        },
        "rescue_commit_effect": {
            "proposal_id": "rescue-proposal-1",
            "recommended_days": 2,
            "daily_kcal_adjustment": -225,
            "refreshed_remaining_kcal": 775,
        },
        "sidecar_diagnostic": {"internal": "sidecar_payload_should_not_render"},
    }


def _dismiss_contract() -> dict:
    return {
        "artifact_type": "dismiss_rescue_plan_lab_contract",
        "status": "pass",
        "dismissed_projection": {
            "proposal_id": "rescue-proposal-2",
            "proposal_status": "dismissed",
            "user_id": "user-1",
            "dismissed_at": "2026-05-13T11:00:00+08:00",
            "dismiss_source": "ui",
            "dismiss_reason": "too strict today",
            "source_audit": {
                "surface": "proposal_inbox",
                "source_event_id": "dismiss-click-1",
                "run_id": "run-2",
            },
        },
        "internal_reasoning": "chain of thought should not render",
    }


def _read_model(artifacts: list[dict]) -> dict:
    from app.rescue.application.proposal_inbox_history_audit import (
        build_rescue_proposal_inbox_history_audit_read_model,
    )

    return build_rescue_proposal_inbox_history_audit_read_model(
        proposal_artifacts=artifacts,
    )


def test_accepted_rescue_plan_is_visible_in_proposal_inbox_mirror_not_actionable() -> None:
    model = _read_model([_card_packet(), _accept_contract(), _commit_effect()])

    assert model["status"] == "pass"
    assert model["chat_first_primary_surface"] is True
    assert model["ui_is_mirror_only"] is True
    assert model["active_proposal_inbox"] == []
    assert [item["proposal_id"] for item in model["proposal_inbox_mirror"]] == [
        "rescue-proposal-1"
    ]
    item = model["proposal_inbox_mirror"][0]
    assert item["proposal_status"] == "accepted"
    assert item["primary_actions"] == []
    assert item["summary"] == "Accepted rescue plan: 225 kcal per day for 2 days."
    assert item["expandable_explanation"].endswith("775.")
    assert model["audit_events"] == [
        {
            "event_type": "accepted",
            "proposal_id": "rescue-proposal-1",
            "occurred_at": "2026-05-13T10:30:00+08:00",
            "surface": "chat",
            "source_event_id": "msg-accept-1",
            "run_id": "run-1",
            "summary": "Rescue proposal accepted.",
            "raw_trace_exposed": False,
            "sidecar_diagnostic_exposed": False,
        }
    ]


def test_dismissed_proposal_leaves_inbox_but_remains_in_history_and_audit() -> None:
    model = _read_model([_card_packet(), _dismiss_contract()])

    active_ids = [item["proposal_id"] for item in model["active_proposal_inbox"]]
    inbox_ids = [item["proposal_id"] for item in model["proposal_inbox_mirror"]]
    assert "rescue-proposal-2" not in active_ids
    assert "rescue-proposal-2" not in inbox_ids
    assert "rescue-proposal-1" in active_ids
    dismissed = [item for item in model["history_items"] if item["proposal_id"] == "rescue-proposal-2"][0]
    assert dismissed["proposal_status"] == "dismissed"
    assert dismissed["same_proposal_redelivery_allowed"] is False
    assert dismissed["expandable_explanation"] == "too strict today"
    assert model["audit_events"][0]["surface"] == "proposal_inbox"
    assert model["audit_events"][0]["event_type"] == "dismissed"


def test_presented_proposal_remains_actionable_in_active_inbox() -> None:
    model = _read_model([_card_packet()])

    assert [item["proposal_id"] for item in model["active_proposal_inbox"]] == [
        "rescue-proposal-1"
    ]
    assert model["active_proposal_inbox"][0]["primary_actions"] == [
        "accept_rescue_plan",
        "dismiss_rescue_plan",
    ]
    assert model["proposal_inbox_mirror"] == model["active_proposal_inbox"]


def test_read_model_does_not_expose_raw_trace_sidecar_or_internal_reasoning() -> None:
    model = _read_model([_card_packet(), _accept_contract(), _commit_effect(), _dismiss_contract()])
    rendered = json.dumps(model, ensure_ascii=False)

    assert model["raw_trace_exposed"] is False
    assert model["sidecar_diagnostic_exposed"] is False
    assert model["internal_reasoning_exposed"] is False
    assert "raw_secret_should_not_render" not in rendered
    assert "sidecar_payload_should_not_render" not in rendered
    assert "chain of thought should not render" not in rendered


def test_read_model_blocks_unknown_artifacts_without_runtime_activation() -> None:
    model = _read_model([{"artifact_type": "unknown"}])

    assert model["status"] == "blocked"
    assert model["blockers"] == ["unsupported_artifact_type:unknown"]
    assert model["mainline_route_or_api_mount_allowed"] is False
    assert model["production_db_mutation_allowed"] is False
