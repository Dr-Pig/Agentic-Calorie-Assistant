from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.body.application import build_active_body_plan_view
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.models import Base
from app.schemas import EstimateRequest


class _BodyObservationManagerProvider:
    def readiness(self) -> dict[str, Any]:
        return {"configured": True, "provider": "body_observation_boundary_fixture"}

    async def complete_with_trace(
        self,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        if int(user_payload.get("round_index") or 0) == 0:
            return (
                {
                    "manager_action": "call_tools",
                    "tool_calls": [
                        {
                            "name": "body.record_observation",
                            "arguments": {
                                "observation_type": "weight",
                                "value": 70.0,
                                "unit": "kg",
                            },
                        }
                    ],
                },
                {"source": "body_observation_boundary_fixture"},
            )
        return (
            {
                "manager_action": "final",
                "intent": "body_observation",
                "intent_type": "body_observation",
                "final_action": "answer_only",
                "workflow_effect": "record_weight",
                "target_attachment": {"mode": "body_observation_recorded"},
                "exactness": "deterministic_fixture",
                "confidence": "high",
                "evidence_posture": "write_only_domain_mutation",
                "repair_ack": False,
                "answer_contract": {"reply_text": "Recorded weight 70.0 kg. Body plan was not changed."},
                "response_summary": "record_weight",
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "mutation_result",
                "semantic_decision": {
                    "semantic_authority": "deterministic_fake_provider",
                    "current_turn_intent": "body_observation",
                    "target_attachment": {"mode": "body_observation_recorded"},
                    "workflow_effect": "record_weight",
                    "final_action_candidate": "answer_only",
                    "estimation_posture": "not_applicable",
                    "followup_posture": "none",
                    "followup_targets": [],
                    "mutation_intent_candidate": "body_observation_write",
                    "uncertainty_posture": "bounded",
                    "source": "body_observation_boundary_fixture",
                    "semantic_owner": "manager",
                    "deterministic_role": "fixture_simulates_manager_output_only",
                },
                "tool_calls": [],
            },
            {"source": "body_observation_boundary_fixture"},
        )


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_estimate_body_observation_route_does_not_silently_rebootstrap_body_plan(monkeypatch) -> None:
    from app.composition import intake_routes

    db = _session()
    user = get_or_create_user(db, "estimate-body-observation-user")
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=30,
            height_cm=165.0,
            current_weight_kg=58.0,
            activity_level="sedentary",
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            local_date="2026-04-18",
            timezone="Asia/Taipei",
        ),
    )
    before = build_active_body_plan_view(db, user_id=user.id)

    monkeypatch.setattr(
        intake_routes,
        "manager_provider",
        _BodyObservationManagerProvider(),
    )
    monkeypatch.setattr(
        intake_routes,
        "build_workflow_routing_decision",
        lambda **_: SimpleNamespace(
            target_workflow_family="body_observation",
            disposition="open_new_workflow",
            phase_a_trace={},
            required_read_surfaces=[],
        ),
    )

    response = asyncio.run(
        intake_routes.estimate(
            EstimateRequest(text="my weight is 70kg", user_id="estimate-body-observation-user"),
            raw_request=SimpleNamespace(headers={}),
            db=db,
        )
    )
    after = build_active_body_plan_view(db, user_id=user.id)

    assert response["coach_message"] == "Recorded weight 70.0 kg. Body plan was not changed."
    assert response["payload"]["state_delta"]["body_observation_recorded"] is True
    assert after.body_plan_id == before.body_plan_id
    assert after.daily_budget_kcal == before.daily_budget_kcal
    assert after.recommended_target_kcal == before.recommended_target_kcal
    assert after.current_weight_kg == before.current_weight_kg
