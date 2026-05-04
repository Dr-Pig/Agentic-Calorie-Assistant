from __future__ import annotations

from collections import Counter, defaultdict

from app.memory.domain.summaries import (
    AdherenceSummary,
    CalibrationHistorySummary,
    CommittedMealEvent,
    CountedLabel,
    GoldenOrder,
    GoldenOrderSummary,
    InteractionPreferenceEvent,
    IntakeCompletenessSummary,
    PreferenceProfileSummary,
    RescueHistorySummary,
    SuppressionSignal,
    SuppressionSummary,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.derived_summaries"
)


def build_preference_profile_summary(
    events: list[CommittedMealEvent],
    *,
    limit: int = 5,
) -> PreferenceProfileSummary:
    item_counts: Counter[str] = Counter()
    store_counts: Counter[str] = Counter()
    cuisine_counts: Counter[str] = Counter()

    for event in events:
        item_counts.update(event.item_names)
        if event.store_name:
            store_counts[event.store_name] += 1
        if event.cuisine_family:
            cuisine_counts[event.cuisine_family] += 1

    return PreferenceProfileSummary(
        event_count=len(events),
        top_items=_to_counted_labels(item_counts, limit),
        top_stores=_to_counted_labels(store_counts, limit),
        cuisine_families=_to_counted_labels(cuisine_counts, limit),
    )


def build_golden_order_summary(
    events: list[CommittedMealEvent],
    *,
    minimum_count: int = 3,
    limit: int = 5,
) -> GoldenOrderSummary:
    grouped: dict[tuple[str, tuple[str, ...]], list[CommittedMealEvent]] = defaultdict(
        list
    )
    for event in events:
        if not event.store_name or not event.item_names:
            continue
        key = (event.store_name, tuple(event.item_names))
        grouped[key].append(event)

    orders: list[GoldenOrder] = []
    for (store_name, item_names), matches in grouped.items():
        if len(matches) < minimum_count:
            continue
        last_seen = max(event.occurred_at for event in matches)
        orders.append(
            GoldenOrder(
                store_name=store_name,
                item_names=list(item_names),
                count=len(matches),
                last_seen_at=last_seen,
            )
        )

    orders.sort(key=lambda order: (-order.count, order.store_name, order.item_names))
    return GoldenOrderSummary(orders=orders[:limit])


def build_intake_completeness_summary(
    events: list[CommittedMealEvent],
) -> IntakeCompletenessSummary:
    observed = sorted(event.occurred_at for event in events)
    logged_days = {event.occurred_at.date().isoformat() for event in events}
    return IntakeCompletenessSummary(
        meal_event_count=len(events),
        logged_day_count=len(logged_days),
        first_observed_at=observed[0] if observed else None,
        last_observed_at=observed[-1] if observed else None,
        coverage_posture=_coverage_posture(len(events), len(logged_days)),
    )


def build_adherence_summary(budget_summaries: list[dict]) -> AdherenceSummary:
    overshoots = [
        float(item.get("overshoot_kcal") or 0)
        for item in budget_summaries
        if float(item.get("overshoot_kcal") or 0) > 0
    ]
    day_count = len(budget_summaries)
    at_or_under = day_count - len(overshoots)
    return AdherenceSummary(
        budget_day_count=day_count,
        at_or_under_target_day_count=at_or_under,
        overshoot_day_count=len(overshoots),
        average_overshoot_kcal=round(sum(overshoots) / len(overshoots), 2)
        if overshoots
        else 0.0,
        adherence_posture=_adherence_posture(day_count, at_or_under),
    )


def build_rescue_history_summary(
    *,
    budget_summaries: list[dict],
    rescue_events: list[dict],
) -> RescueHistorySummary:
    overshoot_days = sum(
        1 for item in budget_summaries if float(item.get("overshoot_kcal") or 0) > 0
    )
    return RescueHistorySummary(
        rescue_event_count=len(rescue_events),
        overshoot_day_count=overshoot_days,
        rescue_viability_posture="shadow_candidate_only"
        if overshoot_days
        else "insufficient_fixture",
    )


def build_calibration_history_summary(
    diagnostics: list[dict],
) -> CalibrationHistorySummary:
    if not diagnostics:
        return CalibrationHistorySummary()
    latest = diagnostics[-1]
    expected = float(latest.get("expected_weight_delta_kg") or 0)
    observed = float(latest.get("observed_weight_delta_kg") or 0)
    return CalibrationHistorySummary(
        diagnostic_count=len(diagnostics),
        latest_expected_weight_delta_kg=expected,
        latest_observed_weight_delta_kg=observed,
        latest_bias_posture=_calibration_bias_posture(expected, observed),
    )


def build_suppression_summary(
    events: list[InteractionPreferenceEvent],
) -> SuppressionSummary:
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for event in events:
        if event.action != "ignored":
            continue
        grouped[event.trigger_type][event.action] += 1

    signals = [
        SuppressionSignal(
            trigger_type=trigger_type,
            count=sum(actions.values()),
            actions=sorted(actions.elements()),
        )
        for trigger_type, actions in grouped.items()
    ]
    signals.sort(key=lambda signal: (-signal.count, signal.trigger_type))
    return SuppressionSummary(suppression_signals=signals)


def _to_counted_labels(counter: Counter[str], limit: int) -> list[CountedLabel]:
    pairs = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [CountedLabel(label=label, count=count) for label, count in pairs[:limit]]


def _coverage_posture(event_count: int, day_count: int) -> str:
    if event_count < 7 or day_count < 3:
        return "insufficient_fixture"
    if day_count < 7:
        return "partial"
    return "reviewable"


def _adherence_posture(day_count: int, at_or_under: int) -> str:
    if day_count < 7:
        return "insufficient_fixture"
    if at_or_under / day_count >= 0.7:
        return "mostly_on_target"
    return "mixed"


def _calibration_bias_posture(expected: float, observed: float) -> str:
    mismatch = observed - expected
    if abs(mismatch) <= 0.1:
        return "aligned"
    if mismatch > 0:
        return "likely_underestimate_or_expenditure_overestimate"
    return "likely_overestimate_or_expenditure_underestimate"
