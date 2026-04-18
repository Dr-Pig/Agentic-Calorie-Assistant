from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import MealItemRecord, MealThreadRecord, MealVersionRecord

FreshnessPosture = Literal["fresh", "stale", "empty"]


@dataclass(frozen=True)
class PreferenceFacet:
    value: str
    count: int


@dataclass(frozen=True)
class PreferenceProfileSummary:
    user_id: int
    generated_at: datetime | None
    freshness_posture: FreshnessPosture
    common_item_kinds: tuple[PreferenceFacet, ...] = ()
    common_staple_types: tuple[PreferenceFacet, ...] = ()
    common_cuisine_families: tuple[PreferenceFacet, ...] = ()
    common_store_names: tuple[PreferenceFacet, ...] = ()
    drink_preference_strength: float = 0.0
    protein_posture_preference: str = "neutral"
    time_of_day_patterns: tuple[str, ...] = ()
    location_patterns: tuple[str, ...] = ()
    accepted_recommendation_patterns: tuple[str, ...] = ()
    ignored_recommendation_patterns: tuple[str, ...] = ()
    source_meal_count: int = 0
    source_item_count: int = 0


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _freshness_from_generated_at(generated_at: datetime | None) -> FreshnessPosture:
    if generated_at is None:
        return "empty"
    age = _now_utc() - generated_at.astimezone(timezone.utc)
    return "fresh" if age.total_seconds() <= 48 * 3600 else "stale"


def _sorted_facets(values: dict[str, int]) -> tuple[PreferenceFacet, ...]:
    ordered = sorted(
        ((name, count) for name, count in values.items() if name and count > 0),
        key=lambda item: (-item[1], item[0]),
    )
    return tuple(PreferenceFacet(value=name, count=count) for name, count in ordered)


def _protein_posture_from_avg(avg_protein_per_item: float) -> str:
    if avg_protein_per_item >= 18:
        return "high_protein_bias"
    if avg_protein_per_item <= 8:
        return "light_protein_bias"
    return "neutral"


def load_preference_profile_summary(
    db: Session,
    *,
    user_id: int,
    limit_recent_items: int = 100,
) -> PreferenceProfileSummary:
    rows = db.execute(
        select(MealItemRecord, MealVersionRecord, MealThreadRecord)
        .join(MealVersionRecord, MealItemRecord.meal_version_id == MealVersionRecord.id)
        .join(MealThreadRecord, MealVersionRecord.meal_thread_id == MealThreadRecord.id)
        .where(
            MealThreadRecord.user_id == user_id,
            MealVersionRecord.version_status == "active",
            MealVersionRecord.resolution_status == "completed_meal",
        )
        .order_by(MealVersionRecord.occurred_at.desc(), MealItemRecord.id.desc())
        .limit(limit_recent_items)
    ).all()

    if not rows:
        return PreferenceProfileSummary(
            user_id=user_id,
            generated_at=None,
            freshness_posture="empty",
        )

    item_kind_counts: dict[str, int] = {}
    staple_type_counts: dict[str, int] = {}
    cuisine_family_counts: dict[str, int] = {}
    store_name_counts: dict[str, int] = {}
    time_of_day_counts: dict[str, int] = {}
    location_counts: dict[str, int] = {}
    total_protein = 0
    generated_at: datetime | None = None
    meal_ids: set[int] = set()

    for item, version, thread in rows:
        meal_ids.add(thread.id)
        classification = dict(item.classification_json or {})
        generated_at = max(filter(None, (generated_at, version.occurred_at)), default=version.occurred_at)

        item_kind = str(classification.get("item_kind") or "").strip()
        staple_type = str(classification.get("staple_type") or "").strip()
        cuisine_family = str(classification.get("cuisine_family") or "").strip()
        store_name = str(
            classification.get("store_name")
            or classification.get("chain_name")
            or version.reason_payload_json.get("store_name")
            if isinstance(version.reason_payload_json, dict)
            else ""
        ).strip()
        location_cluster = str(classification.get("location_cluster_id") or "").strip()

        if item_kind:
            item_kind_counts[item_kind] = item_kind_counts.get(item_kind, 0) + 1
        if staple_type:
            staple_type_counts[staple_type] = staple_type_counts.get(staple_type, 0) + 1
        if cuisine_family:
            cuisine_family_counts[cuisine_family] = cuisine_family_counts.get(cuisine_family, 0) + 1
        if store_name:
            store_name_counts[store_name] = store_name_counts.get(store_name, 0) + 1
        if location_cluster:
            location_counts[location_cluster] = location_counts.get(location_cluster, 0) + 1
        if version.occurred_at is not None:
            hour = int(version.occurred_at.hour)
            if 5 <= hour < 11:
                bucket = "breakfast"
            elif 11 <= hour < 15:
                bucket = "lunch"
            elif 15 <= hour < 18:
                bucket = "afternoon"
            elif 18 <= hour < 23:
                bucket = "dinner"
            else:
                bucket = "late_night"
            time_of_day_counts[bucket] = time_of_day_counts.get(bucket, 0) + 1
        total_protein += int(item.protein_g or 0)

    source_item_count = len(rows)
    avg_protein = total_protein / max(1, source_item_count)
    drink_count = item_kind_counts.get("drink", 0)
    drink_preference_strength = round(drink_count / max(1, source_item_count), 3)

    return PreferenceProfileSummary(
        user_id=user_id,
        generated_at=generated_at,
        freshness_posture=_freshness_from_generated_at(generated_at),
        common_item_kinds=_sorted_facets(item_kind_counts),
        common_staple_types=_sorted_facets(staple_type_counts),
        common_cuisine_families=_sorted_facets(cuisine_family_counts),
        common_store_names=_sorted_facets(store_name_counts),
        drink_preference_strength=drink_preference_strength,
        protein_posture_preference=_protein_posture_from_avg(avg_protein),
        time_of_day_patterns=tuple(facet.value for facet in _sorted_facets(time_of_day_counts)[:3]),
        location_patterns=tuple(facet.value for facet in _sorted_facets(location_counts)[:3]),
        accepted_recommendation_patterns=(),
        ignored_recommendation_patterns=(),
        source_meal_count=len(meal_ids),
        source_item_count=source_item_count,
    )
