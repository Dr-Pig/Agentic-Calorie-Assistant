from __future__ import annotations

from collections import Counter, defaultdict

from app.memory.domain.summaries import (
    CommittedMealEvent,
    CountedLabel,
    GoldenOrder,
    GoldenOrderSummary,
    InteractionPreferenceEvent,
    PreferenceProfileSummary,
    SuppressionSignal,
    SuppressionSummary,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("memory.application.derived_summaries")


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
    grouped: dict[tuple[str, tuple[str, ...]], list[CommittedMealEvent]] = defaultdict(list)
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


def build_suppression_summary(events: list[InteractionPreferenceEvent]) -> SuppressionSummary:
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
