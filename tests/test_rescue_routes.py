from __future__ import annotations

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
