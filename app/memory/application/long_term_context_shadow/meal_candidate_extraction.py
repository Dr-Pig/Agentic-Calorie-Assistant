from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from app.memory.application.long_term_context_shadow.candidate_records import _candidate
from app.memory.application.long_term_context_shadow.utils import (
    _confidence,
    _most_common,
    _parse_datetime,
    _slug,
    _source_refs_for_meals,
    _source_refs_matching,
    _time_bucket,
    _trace_id,
    _trace_ids_matching,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _meal_distribution_candidates(
    user_id: str,
    meals: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not meals:
        return []

    counters = _meal_distribution_counters(meals)
    observed_at = counters["observed_at"]
    preference_candidates = [
        candidate
        for candidate in (
            _top_staple_preference_candidate(
                user_id=user_id,
                meals=meals,
                trace_refs=trace_refs,
                observed_at=observed_at,
                staple_types=counters["staple_types"],
            ),
            _top_drink_preference_candidate(
                user_id=user_id,
                meals=meals,
                trace_refs=trace_refs,
                observed_at=observed_at,
                drinks=counters["drinks"],
            ),
        )
        if candidate is not None
    ]
    return (
        _base_meal_pattern_candidates(
            user_id=user_id,
            meals=meals,
            trace_refs=trace_refs,
            trace_ids=counters["trace_ids"],
            observed_at=observed_at,
            item_kinds=counters["item_kinds"],
            time_buckets=counters["time_buckets"],
        )
        + preference_candidates
    )


def _meal_distribution_counters(meals: list[dict[str, Any]]) -> dict[str, Any]:
    item_kinds: Counter[str] = Counter()
    staple_types: Counter[str] = Counter()
    drinks: Counter[str] = Counter()
    time_buckets: Counter[str] = Counter()
    trace_ids: list[str] = []
    observed_at: list[datetime] = []

    for meal in meals:
        trace_ids.append(_trace_id(meal))
        item_kinds.update(str(value) for value in meal.get("item_kinds") or [])
        staple_types.update(str(value) for value in meal.get("staple_types") or [])
        drinks.update(str(value) for value in meal.get("drink_names") or [])
        time_buckets[_time_bucket(meal.get("logged_at"))] += 1
        parsed = _parse_datetime(meal.get("logged_at"))
        if parsed:
            observed_at.append(parsed)
    return {
        "item_kinds": item_kinds,
        "staple_types": staple_types,
        "drinks": drinks,
        "time_buckets": time_buckets,
        "trace_ids": trace_ids,
        "observed_at": observed_at,
    }


def _base_meal_pattern_candidates(
    *,
    user_id: str,
    meals: list[dict[str, Any]],
    trace_refs: dict[str, str],
    trace_ids: list[str],
    observed_at: list[datetime],
    item_kinds: Counter[str],
    time_buckets: Counter[str],
) -> list[LongTermContextCandidate]:
    return [
        _candidate(
            candidate_id="pattern-item-kind-distribution",
            candidate_type="pattern",
            user_id=user_id,
            source_trace_ids=trace_ids,
            source_object_refs=_source_refs_for_meals(meals, trace_refs),
            evidence_count=len(meals),
            observed_at=observed_at,
            confidence=_confidence(len(meals), threshold=5),
            proposed_memory_text="Observed meal item-kind distribution in fixture logs",
            payload={"distribution": dict(sorted(item_kinds.items()))},
            reason_codes=["l2a_item_kind_distribution"],
            intended_consumers=["recommendation", "intake_clarification"],
        ),
        _candidate(
            candidate_id="pattern-time-of-day-distribution",
            candidate_type="pattern",
            user_id=user_id,
            source_trace_ids=trace_ids,
            source_object_refs=_source_refs_for_meals(meals, trace_refs),
            evidence_count=len(meals),
            observed_at=observed_at,
            confidence=_confidence(len(meals), threshold=5),
            proposed_memory_text="Observed time-of-day logging pattern in fixture logs",
            payload={"distribution": dict(sorted(time_buckets.items()))},
            reason_codes=["l2a_time_of_day_pattern"],
            intended_consumers=["chat_context", "proactive", "intake_clarification"],
        ),
    ]


def _top_staple_preference_candidate(
    *,
    user_id: str,
    meals: list[dict[str, Any]],
    trace_refs: dict[str, str],
    observed_at: list[datetime],
    staple_types: Counter[str],
) -> LongTermContextCandidate | None:
    if not staple_types:
        return None
    label, count = _most_common(staple_types)
    return _candidate(
        candidate_id=f"preference-staple-{_slug(label)}",
        candidate_type="food_preference",
        user_id=user_id,
        source_trace_ids=_trace_ids_matching(meals, "staple_types", label),
        source_object_refs=_source_refs_matching(
            meals, trace_refs, "staple_types", label
        ),
        evidence_count=count,
        observed_at=observed_at,
        confidence=_confidence(count, threshold=5),
        proposed_memory_text=f"Candidate staple preference: {label}",
        payload={"preference_kind": "staple_type", "value": label, "count": count},
        reason_codes=["l2a_staple_type_distribution"],
        intended_consumers=["recommendation", "proactive", "intake_clarification"],
    )


def _top_drink_preference_candidate(
    *,
    user_id: str,
    meals: list[dict[str, Any]],
    trace_refs: dict[str, str],
    observed_at: list[datetime],
    drinks: Counter[str],
) -> LongTermContextCandidate | None:
    if not drinks:
        return None
    label, count = _most_common(drinks)
    return _candidate(
        candidate_id=f"preference-drink-{_slug(label)}",
        candidate_type="food_preference",
        user_id=user_id,
        source_trace_ids=_trace_ids_matching(meals, "drink_names", label),
        source_object_refs=_source_refs_matching(
            meals, trace_refs, "drink_names", label
        ),
        evidence_count=count,
        observed_at=observed_at,
        confidence=_confidence(count, threshold=5),
        proposed_memory_text=f"Candidate drink preference: {label}",
        payload={"preference_kind": "drink", "value": label, "count": count},
        reason_codes=["l2a_drink_preference_strength"],
        intended_consumers=["recommendation", "proactive", "intake_clarification"],
    )


def _golden_order_candidates(
    user_id: str,
    meals: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    grouped: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = defaultdict(list)
    for meal in meals:
        store_name = meal.get("store_name")
        item_names = tuple(str(item) for item in meal.get("item_names") or [])
        if store_name and item_names:
            grouped[(str(store_name), item_names)].append(meal)

    candidates: list[LongTermContextCandidate] = []
    for (store_name, item_names), matches in sorted(grouped.items()):
        if len(matches) < 3:
            continue
        observed_at = [_parse_datetime(meal.get("logged_at")) for meal in matches]
        item_text = ", ".join(item_names)
        candidates.append(
            _candidate(
                candidate_id=f"golden-order-{_slug(store_name)}-{_slug('-'.join(item_names))}",
                candidate_type="golden_order",
                user_id=user_id,
                source_trace_ids=[_trace_id(meal) for meal in matches],
                source_object_refs=_source_refs_for_meals(matches, trace_refs),
                evidence_count=len(matches),
                observed_at=[value for value in observed_at if value is not None],
                confidence=_confidence(len(matches), threshold=3),
                proposed_memory_text=f"Possible golden order: {store_name} - {item_text}",
                payload={
                    "store_name": store_name,
                    "item_names": list(item_names),
                    "materialized_from_canonical_history": True,
                    "not_promoted_memory": True,
                },
                reason_codes=["golden_order_materialized_view_candidate"],
                intended_consumers=[
                    "recommendation",
                    "intake_clarification",
                    "chat_context",
                ],
            )
        )
    return candidates
