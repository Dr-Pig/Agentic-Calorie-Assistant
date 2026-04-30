from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.domain import ActiveBodyPlanView
from app.body.infrastructure.models import BodyPlanRecord, BodyProfileRecord


def load_active_body_plan_view(
    db: Session,
    *,
    user_id: int,
) -> ActiveBodyPlanView:
    body_plan = db.execute(
        select(BodyPlanRecord)
        .where(
            BodyPlanRecord.user_id == user_id,
            BodyPlanRecord.plan_status == "active",
        )
        .order_by(BodyPlanRecord.id.desc())
    ).scalar_one_or_none()

    if body_plan is None:
        return ActiveBodyPlanView(
            user_id=user_id,
            plan_status="inactive",
            profile_status="missing",
        )

    metadata = dict(body_plan.metadata_json or {})
    body_profile = db.execute(
        select(BodyProfileRecord)
        .where(
            BodyProfileRecord.user_id == user_id,
            BodyProfileRecord.profile_status == "active",
        )
        .order_by(BodyProfileRecord.id.desc())
    ).scalar_one_or_none()
    plan_source = metadata.get("plan_source")
    goal_type = metadata.get("goal_type")
    recommended_target_kcal = int(metadata.get("recommended_target_kcal") or body_plan.daily_budget_kcal or 0)

    return ActiveBodyPlanView(
        body_plan_id=body_plan.id,
        user_id=body_plan.user_id,
        plan_status=body_plan.plan_status,
        goal_type=str(goal_type) if isinstance(goal_type, str) and goal_type.strip() else None,
        current_weight_kg=float(body_profile.current_weight_kg) if body_profile is not None else None,
        target_weight_kg=float(body_profile.target_weight_kg) if body_profile is not None and body_profile.target_weight_kg is not None else None,
        age_years=int(body_profile.age_years) if body_profile is not None else None,
        height_cm=float(body_profile.height_cm) if body_profile is not None else None,
        activity_level=str(body_profile.activity_level) if body_profile is not None and body_profile.activity_level else None,
        daily_budget_kcal=body_plan.daily_budget_kcal,
        recommended_target_kcal=recommended_target_kcal,
        safety_floor_kcal=body_plan.safety_floor_kcal,
        estimated_tdee=body_plan.estimated_tdee,
        target_pace_kg_per_week=body_plan.target_pace_kg_per_week,
        plan_source=str(plan_source) if isinstance(plan_source, str) and plan_source.strip() else None,
        profile_status="ready",
        last_updated_at=body_plan.created_at,
    )
