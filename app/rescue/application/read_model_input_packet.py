from __future__ import annotations

from typing import Any, Mapping

from app.rescue.application.self_use_trace_ingress_contracts import REQUIRED_SCOPE_KEYS
from app.rescue.domain.read_model_inputs import (
    RescueActiveBodyPlanReadModel,
    RescueCommittedMealReadModel,
    RescueCurrentBudgetReadModel,
    RescueOpenProposalsReadModel,
    RescueProactiveStatusReadModel,
    RescueReadModelInputPacket,
    RescueRecentCommittedMealsReadModel,
    RescueTargetDayReadModel,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.read_model_input_packet"
)
VIEW_SOURCE_ORDER = [
    "CurrentBudgetView",
    "RecentCommittedMealsView",
    "RescueHistorySummary",
    "AdherenceSummary",
    "OpenProposalsView",
    "ProactiveStatusView",
    "ActiveBodyPlanView",
]
FORBIDDEN_INPUT_SOURCES = [
    "current_intake_event_context",
    "raw_transcript_search",
    "full_session_history",
    "durable_memory_truth",
]


def build_rescue_read_model_input_packet(
    ingress_event: Mapping[str, Any],
    *,
    rescue_history_summary: Mapping[str, Any] | None = None,
    adherence_summary: Mapping[str, Any] | None = None,
    proactive_status_view: Mapping[str, Any] | None = None,
) -> RescueReadModelInputPacket:
    scope = _string_mapping(ingress_event.get("scope_keys"))
    budget = _current_budget_view(_mapping(ingress_event.get("current_budget_view")))
    recent_meals = _recent_meals_view(
        _mapping(ingress_event.get("recent_committed_meals_view"))
    )
    body_plan = _active_body_plan_view(
        _mapping(ingress_event.get("active_body_plan_view"))
    )
    open_proposals = _open_proposals_view(
        _mapping(ingress_event.get("open_proposals_view"))
    )
    proactive = _proactive_status_view(_mapping(proactive_status_view))
    blockers = _blockers(ingress_event, scope, budget)
    return RescueReadModelInputPacket(
        status="blocked" if blockers else "ready",
        blockers=blockers,
        scope_keys=scope,
        source_trace_ids=[str(item) for item in ingress_event.get("source_trace_ids") or []],
        canonical_source_refs=_source_refs(ingress_event),
        view_source_order=list(VIEW_SOURCE_ORDER),
        forbidden_input_sources=list(FORBIDDEN_INPUT_SOURCES),
        current_budget_view=budget,
        recent_committed_meals_view=recent_meals,
        active_body_plan_view=body_plan,
        open_proposals_view=open_proposals,
        proactive_status_view=proactive,
        rescue_history_summary=dict(rescue_history_summary or {}),
        adherence_summary=dict(adherence_summary or {}),
    )


def _current_budget_view(view: Mapping[str, Any]) -> RescueCurrentBudgetReadModel:
    effective = _int_or_none(view.get("effective_budget_kcal"))
    consumed = _int_or_none(view.get("meal_consumption_total_kcal"))
    available = effective is not None and consumed is not None
    return RescueCurrentBudgetReadModel(
        view_available=available,
        local_date=str(view.get("local_date") or ""),
        base_budget_kcal=_int(view.get("base_budget_kcal")),
        effective_budget_kcal=effective or 0,
        meal_consumption_total_kcal=consumed or 0,
        remaining_kcal=_int(view.get("remaining_kcal")),
        overshoot_kcal=max(0, (consumed or 0) - (effective or 0)) if available else 0,
        source=str(view.get("source") or ""),
    )


def _recent_meals_view(view: Mapping[str, Any]) -> RescueRecentCommittedMealsReadModel:
    meals = [
        RescueCommittedMealReadModel(
            meal_thread_id=str(_mapping(item).get("meal_thread_id") or ""),
            meal_title=str(_mapping(item).get("meal_title") or ""),
            total_kcal=_int(_mapping(item).get("total_kcal")),
        )
        for item in view.get("meals") or []
        if isinstance(item, Mapping)
    ]
    return RescueRecentCommittedMealsReadModel(
        view_available=bool(view),
        meal_count=_int(view.get("meal_count")) or len(meals),
        meals=meals,
    )


def _active_body_plan_view(view: Mapping[str, Any]) -> RescueActiveBodyPlanReadModel:
    target_days = [
        RescueTargetDayReadModel(
            local_date=str(_mapping(item).get("local_date") or ""),
            base_budget_kcal=_int(_mapping(item).get("base_budget_kcal")),
            calibration_adjustment_total_kcal=_int(
                _mapping(item).get("calibration_adjustment_total_kcal")
            ),
        )
        for item in view.get("target_days") or []
        if isinstance(item, Mapping)
    ]
    return RescueActiveBodyPlanReadModel(
        view_available=bool(view),
        safety_floor_kcal=_int(view.get("safety_floor_kcal")),
        target_day_count=len(target_days),
        target_days=target_days,
        source=str(view.get("source") or ""),
    )


def _open_proposals_view(view: Mapping[str, Any]) -> RescueOpenProposalsReadModel:
    return RescueOpenProposalsReadModel(
        view_available=bool(view),
        open_rescue_proposal_count=_int(view.get("open_rescue_proposal_count")),
        active_proposal_ids=[
            str(item) for item in view.get("active_proposal_ids") or []
        ],
    )


def _proactive_status_view(view: Mapping[str, Any]) -> RescueProactiveStatusReadModel:
    return RescueProactiveStatusReadModel(
        view_available=bool(view),
        budget_alert_cooldown_active=bool(view.get("budget_alert_cooldown_active")),
        suppressed_trigger_types=[
            str(item) for item in view.get("suppressed_trigger_types") or []
        ],
        next_allowed_signal=(
            str(view.get("next_allowed_signal"))
            if view.get("next_allowed_signal") is not None
            else None
        ),
    )


def _blockers(
    ingress_event: Mapping[str, Any],
    scope: Mapping[str, str],
    budget: RescueCurrentBudgetReadModel,
) -> list[str]:
    blockers: list[str] = []
    if ingress_event.get("artifact_type") != "rescue_ingress_event":
        blockers.append("unsupported_ingress_artifact")
    missing_scope = [key for key in REQUIRED_SCOPE_KEYS if not scope.get(key)]
    blockers.extend(f"missing_scope.{key}" for key in missing_scope)
    if not budget.view_available:
        blockers.append("missing_current_budget_view")
    return blockers


def _source_refs(ingress_event: Mapping[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for item in ingress_event.get("canonical_source_refs") or []:
        if not isinstance(item, Mapping):
            continue
        refs.append({str(key): str(value) for key, value in item.items()})
    return refs


def _string_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


__all__ = [
    "FORBIDDEN_INPUT_SOURCES",
    "SIDECAR_ACTIVATION_CONTRACT",
    "VIEW_SOURCE_ORDER",
    "build_rescue_read_model_input_packet",
]
