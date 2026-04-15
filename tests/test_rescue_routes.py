from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.application.rescue_overlay import RescueOverlayTargetDay
from app.application.rescue_runtime import (
    RescueAssessmentResult,
    RescueRuntimeInputs,
    RescueTriggerResult,
    build_rescue_runtime_artifact,
    persist_rescue_runtime_artifact,
)
from app.database import SessionLocal, get_or_create_user
from app.main import app

client = TestClient(app)


def _seed_open_rescue_proposal(user_id: str) -> None:
    db = SessionLocal()
    try:
        user = get_or_create_user(db, user_id)
        artifact = build_rescue_runtime_artifact(
            RescueRuntimeInputs(
                trigger_result=RescueTriggerResult(
                    triggered=True,
                    trigger_reason="daily overshoot exceeded soft threshold",
                    overshoot_kcal=450,
                    current_local_date="2026-04-15",
                    relevant_ledger_summary={"effective_budget_kcal": 1800, "consumed_kcal": 2250},
                ),
                assessment_result=RescueAssessmentResult(
                    rescue_needed=True,
                    rescue_horizon=3,
                    recovery_viability="viable",
                    recommended_rescue_family="short_horizon_spread",
                    compression_summary={"horizon_days": 3, "overshoot_kcal": 450},
                    escalation_risk="low",
                    assessment_confidence="high",
                ),
                target_recovery_kcal=450,
                target_days=(
                    RescueOverlayTargetDay(local_date="2026-04-15", base_budget_kcal=1800),
                    RescueOverlayTargetDay(local_date="2026-04-16", base_budget_kcal=1800),
                    RescueOverlayTargetDay(local_date="2026-04-17", base_budget_kcal=1800),
                ),
                safety_floor_kcal=1500,
                activation_reference_hour_24=9,
            )
        )
        persist_rescue_runtime_artifact(db, user=user, artifact=artifact)
    finally:
        db.close()


def test_rescue_chat_route_surfaces_open_rescue_proposal() -> None:
    user_id = "rescue-route-user-surface"
    _seed_open_rescue_proposal(user_id)

    response = client.get("/rescue/chat", params={"user_id": user_id, "mode": "proactive"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["surfaced"] is True
    assert payload["response"]["ui_hints"]["delivery"] == "chat_only"
    assert payload["response"]["recommended_days"] == 2


def test_rescue_chat_action_route_accepts_and_writes_overlay() -> None:
    user_id = "rescue-route-user-accept"
    _seed_open_rescue_proposal(user_id)

    response = client.post(
        "/rescue/chat/action",
        json={
            "user_id": user_id,
            "action": "accept_rescue_plan",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["proposal_status"] == "accepted"
    assert payload["response"]["ui_hints"]["mode"] == "rescue_accept_applied"
    assert payload["writeback"]["status"] == "applied"
    assert len(payload["writeback"]["entry_ids"]) == 3


def test_rescue_chat_action_route_second_accept_returns_no_open_proposal() -> None:
    user_id = "rescue-route-user-accept-twice"
    _seed_open_rescue_proposal(user_id)

    first = client.post(
        "/rescue/chat/action",
        json={
            "user_id": user_id,
            "action": "accept_rescue_plan",
        },
    )
    second = client.post(
        "/rescue/chat/action",
        json={
            "user_id": user_id,
            "action": "accept_rescue_plan",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    payload = second.json()
    assert payload["surfaced"] is False
    assert payload["response"]["ui_hints"]["mode"] == "no_open_rescue_proposal"
    assert payload["writeback"] is None


def test_rescue_chat_action_route_reject_with_reason_closes_proposal() -> None:
    user_id = "rescue-route-user-reject"
    _seed_open_rescue_proposal(user_id)

    response = client.post(
        "/rescue/chat/action",
        json={
            "user_id": user_id,
            "action": "reject_rescue_plan",
            "reason": "我這幾天行程不固定，現在不想套這個節奏。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["proposal_status"] == "rejected"
    assert payload["response"]["ui_hints"]["mode"] == "rescue_proposal_closed"
    assert payload["response"]["ui_hints"]["reason_bridge"]["reason_hint"] == "bad_timing"


def test_rescue_chat_action_route_defer_sets_pending_state() -> None:
    user_id = "rescue-route-user-defer"
    _seed_open_rescue_proposal(user_id)

    response = client.post(
        "/rescue/chat/action",
        json={
            "user_id": user_id,
            "action": "defer_rescue_plan",
            "reason": "我今天先不要，晚一點再說。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["proposal_status"] == "deferred_pending_reminder"
    assert payload["response"]["ui_hints"]["mode"] == "rescue_deferred_pending_reminder"
    assert payload["response"]["ui_hints"]["next_reminder_at"] is not None


def test_rescue_chat_route_waits_until_deferred_reminder_is_due() -> None:
    user_id = "rescue-route-user-reminder"
    _seed_open_rescue_proposal(user_id)

    defer = client.post(
        "/rescue/chat/action",
        json={
            "user_id": user_id,
            "action": "defer_rescue_plan",
        },
    )
    assert defer.status_code == 200

    proactive_before_due = client.get("/rescue/chat", params={"user_id": user_id, "mode": "proactive"})
    assert proactive_before_due.status_code == 200
    assert proactive_before_due.json()["surfaced"] is False
    assert proactive_before_due.json()["response"]["ui_hints"]["mode"] == "rescue_deferred_waiting"

    db = SessionLocal()
    try:
        user = get_or_create_user(db, user_id)
        proposal = user.proposals[-1]
        proposal.metadata_json = {
            **dict(proposal.metadata_json or {}),
            "next_reminder_at": (datetime.now() - timedelta(minutes=1)).isoformat(timespec="seconds"),
        }
        db.commit()
    finally:
        db.close()

    proactive_after_due = client.get("/rescue/chat", params={"user_id": user_id, "mode": "proactive"})
    assert proactive_after_due.status_code == 200
    assert proactive_after_due.json()["surfaced"] is True
