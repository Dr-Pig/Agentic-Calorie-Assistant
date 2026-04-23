from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Literal, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import BodyPlanRecord, LedgerEntryRecord, User
from ...intake.application.canonical_commit_bridge import apply_rescue_overlay_skeleton


@dataclass(frozen=True)
class RescueOverlayTargetDay:
    local_date: str
    base_budget_kcal: int
    calibration_adjustment_kcal: int = 0


@dataclass(frozen=True)
class RescueOverlayDayAssessment:
    local_date: str
    proposed_rescue_overlay_kcal: int
    base_budget_kcal: int
    calibration_adjustment_kcal: int
    max_daily_rescue_compression_kcal: int
    candidate_effective_budget_kcal: int
    safety_floor_kcal: int
    compression_ratio: float
    viability: Literal["viable", "strained", "non_viable"]
    within_compression_cap: bool
    meets_safety_floor: bool


@dataclass(frozen=True)
class ShortHorizonRescuePlan:
    rescue_family: Literal["short_horizon_spread"] = "short_horizon_spread"
    target_recovery_kcal: int = 0
    scheduled_recovery_kcal: int = 0
    unallocated_recovery_kcal: int = 0
    safety_floor_kcal: int = 0
    viability: Literal["viable", "strained", "non_viable"] = "non_viable"
    requires_escalation: bool = False
    overlay_days: tuple[RescueOverlayDayAssessment, ...] = ()


def _normalize_resolved_safety_floor(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def resolve_rescue_safety_floor_kcal(
    db: Session,
    *,
    user: User,
    explicit_safety_floor_kcal: int | None = None,
) -> int | None:
    resolved_override = _normalize_resolved_safety_floor(explicit_safety_floor_kcal)
    if resolved_override is not None:
        return resolved_override

    active_body_plan = db.execute(
        select(BodyPlanRecord)
        .where(
            BodyPlanRecord.user_id == user.id,
            BodyPlanRecord.plan_status == "active",
        )
        .order_by(BodyPlanRecord.id.desc())
    ).scalars().first()
    if active_body_plan is None:
        return None
    return _normalize_resolved_safety_floor(active_body_plan.safety_floor_kcal)


def max_daily_rescue_compression(base_budget_kcal: int) -> int:
    return max(0, floor(max(0, base_budget_kcal) * 0.15))


def candidate_effective_budget(
    *,
    base_budget_kcal: int,
    calibration_adjustment_kcal: int,
    proposed_rescue_overlay_kcal: int,
) -> int:
    return base_budget_kcal + calibration_adjustment_kcal + proposed_rescue_overlay_kcal


def assess_rescue_overlay_day(
    *,
    local_date: str,
    base_budget_kcal: int,
    calibration_adjustment_kcal: int,
    proposed_rescue_overlay_kcal: int,
    safety_floor_kcal: int,
) -> RescueOverlayDayAssessment:
    max_compression = max_daily_rescue_compression(base_budget_kcal)
    candidate_budget = candidate_effective_budget(
        base_budget_kcal=base_budget_kcal,
        calibration_adjustment_kcal=calibration_adjustment_kcal,
        proposed_rescue_overlay_kcal=proposed_rescue_overlay_kcal,
    )
    proposed_compression = abs(min(0, proposed_rescue_overlay_kcal))
    within_cap = proposed_compression <= max_compression
    meets_floor = candidate_budget >= safety_floor_kcal
    compression_ratio = 0.0 if base_budget_kcal <= 0 else proposed_compression / base_budget_kcal

    if not within_cap or not meets_floor:
        viability: Literal["viable", "strained", "non_viable"] = "non_viable"
    elif compression_ratio > 0.10:
        viability = "strained"
    else:
        viability = "viable"

    return RescueOverlayDayAssessment(
        local_date=local_date,
        proposed_rescue_overlay_kcal=proposed_rescue_overlay_kcal,
        base_budget_kcal=base_budget_kcal,
        calibration_adjustment_kcal=calibration_adjustment_kcal,
        max_daily_rescue_compression_kcal=max_compression,
        candidate_effective_budget_kcal=candidate_budget,
        safety_floor_kcal=safety_floor_kcal,
        compression_ratio=compression_ratio,
        viability=viability,
        within_compression_cap=within_cap,
        meets_safety_floor=meets_floor,
    )


def build_short_horizon_rescue_plan(
    *,
    overshoot_kcal: int,
    target_days: Sequence[RescueOverlayTargetDay],
    safety_floor_kcal: int | None = None,
    db: Session | None = None,
    user: User | None = None,
) -> ShortHorizonRescuePlan:
    resolved_safety_floor_kcal = _normalize_resolved_safety_floor(safety_floor_kcal)
    if resolved_safety_floor_kcal is None and db is not None and user is not None:
        resolved_safety_floor_kcal = resolve_rescue_safety_floor_kcal(
            db,
            user=user,
            explicit_safety_floor_kcal=safety_floor_kcal,
        )
    if resolved_safety_floor_kcal is None:
        raise ValueError(
            "Rescue overlay requires a resolved safety_floor_kcal from active BodyPlan or explicit override."
        )

    normalized_overshoot = max(0, overshoot_kcal)
    if normalized_overshoot == 0:
        return ShortHorizonRescuePlan(
            target_recovery_kcal=0,
            scheduled_recovery_kcal=0,
            unallocated_recovery_kcal=0,
            safety_floor_kcal=resolved_safety_floor_kcal,
            viability="viable",
            requires_escalation=False,
            overlay_days=tuple(),
        )

    remaining = normalized_overshoot
    scheduled = 0
    overlay_days: list[RescueOverlayDayAssessment] = []

    for index, day in enumerate(target_days):
        remaining_slots = len(target_days) - index
        requested_recovery = (remaining + remaining_slots - 1) // remaining_slots
        proposed_overlay = -requested_recovery
        assessment = assess_rescue_overlay_day(
            local_date=day.local_date,
            base_budget_kcal=day.base_budget_kcal,
            calibration_adjustment_kcal=day.calibration_adjustment_kcal,
            proposed_rescue_overlay_kcal=proposed_overlay,
            safety_floor_kcal=resolved_safety_floor_kcal,
        )

        if assessment.viability == "non_viable":
            floor_headroom = max(
                0,
                day.base_budget_kcal + day.calibration_adjustment_kcal - resolved_safety_floor_kcal,
            )
            allowed_recovery = min(
                requested_recovery,
                max_daily_rescue_compression(day.base_budget_kcal),
                floor_headroom,
            )
            proposed_overlay = -allowed_recovery if allowed_recovery > 0 else 0
            assessment = assess_rescue_overlay_day(
                local_date=day.local_date,
                base_budget_kcal=day.base_budget_kcal,
                calibration_adjustment_kcal=day.calibration_adjustment_kcal,
                proposed_rescue_overlay_kcal=proposed_overlay,
                safety_floor_kcal=resolved_safety_floor_kcal,
            )

        scheduled += abs(min(0, assessment.proposed_rescue_overlay_kcal))
        remaining = max(0, normalized_overshoot - scheduled)
        overlay_days.append(assessment)

    if remaining > 0:
        viability: Literal["viable", "strained", "non_viable"] = "non_viable"
    elif any(day.viability == "strained" for day in overlay_days):
        viability = "strained"
    else:
        viability = "viable"

    return ShortHorizonRescuePlan(
        target_recovery_kcal=normalized_overshoot,
        scheduled_recovery_kcal=scheduled,
        unallocated_recovery_kcal=remaining,
        safety_floor_kcal=resolved_safety_floor_kcal,
        viability=viability,
        requires_escalation=remaining > 0,
        overlay_days=tuple(overlay_days),
    )


def apply_short_horizon_rescue_plan(
    db: Session,
    *,
    user: User,
    plan: ShortHorizonRescuePlan,
    source_id: int | None = None,
    source_type: str = "rescue_plan",
) -> list[LedgerEntryRecord]:
    entries: list[LedgerEntryRecord] = []
    for day in plan.overlay_days:
        delta_kcal = day.proposed_rescue_overlay_kcal
        if delta_kcal == 0:
            continue
        entry = apply_rescue_overlay_skeleton(
            db,
            user=user,
            local_date=day.local_date,
            delta_kcal=delta_kcal,
            source_id=source_id,
            source_type=source_type,
            budget_kcal=day.base_budget_kcal,
            metadata={
                "rescue_family": plan.rescue_family,
                "safety_floor_kcal": plan.safety_floor_kcal,
                "calibration_adjustment_kcal": day.calibration_adjustment_kcal,
                "plan_viability": plan.viability,
            },
        )
        entries.append(entry)
    return entries


def apply_overlay_days_payload(
    db: Session,
    *,
    user: User,
    overlay_days: Sequence[dict[str, object]],
    safety_floor_kcal: int,
    source_id: int | None = None,
    source_type: str = "rescue_plan",
    plan_viability: Literal["viable", "strained", "non_viable"] = "viable",
) -> list[LedgerEntryRecord]:
    plan = ShortHorizonRescuePlan(
        target_recovery_kcal=sum(abs(int(day.get("proposed_rescue_overlay_kcal", 0))) for day in overlay_days),
        scheduled_recovery_kcal=sum(abs(int(day.get("proposed_rescue_overlay_kcal", 0))) for day in overlay_days),
        unallocated_recovery_kcal=0,
        safety_floor_kcal=safety_floor_kcal,
        viability=plan_viability,
        requires_escalation=False,
        overlay_days=tuple(
            RescueOverlayDayAssessment(
                local_date=str(day.get("local_date") or ""),
                proposed_rescue_overlay_kcal=int(day.get("proposed_rescue_overlay_kcal") or 0),
                base_budget_kcal=int(day.get("base_budget_kcal") or 0),
                calibration_adjustment_kcal=int(day.get("calibration_adjustment_kcal") or 0),
                max_daily_rescue_compression_kcal=int(day.get("max_daily_rescue_compression_kcal") or 0),
                candidate_effective_budget_kcal=int(day.get("candidate_effective_budget_kcal") or 0),
                safety_floor_kcal=int(day.get("safety_floor_kcal") or safety_floor_kcal),
                compression_ratio=float(day.get("compression_ratio") or 0.0),
                viability=str(day.get("viability") or plan_viability),  # type: ignore[arg-type]
                within_compression_cap=bool(day.get("within_compression_cap", True)),
                meets_safety_floor=bool(day.get("meets_safety_floor", True)),
            )
            for day in overlay_days
        ),
    )
    return apply_short_horizon_rescue_plan(
        db,
        user=user,
        plan=plan,
        source_id=source_id,
        source_type=source_type,
    )
