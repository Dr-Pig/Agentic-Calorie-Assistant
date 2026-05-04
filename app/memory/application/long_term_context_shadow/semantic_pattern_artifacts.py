from __future__ import annotations

from collections import Counter
from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.utils import (
    _confidence,
    _list_of_dicts,
    _most_common,
    _slug,
    _time_bucket,
)


def _semantic_pattern_extraction_shadow_artifact(
    fixture: dict[str, Any],
) -> dict[str, Any]:
    meals = _list_of_dicts(fixture.get("meal_logs"))
    committed_count = len(meals)
    extraction_allowed = committed_count >= 21
    return _base_artifact(
        artifact_type="semantic_pattern_extraction_shadow_plan",
        fixture=fixture,
        extra={
            "source_spec": "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
            "llm_extraction_called": False,
            "semantic_memory_written": False,
            "runtime_effect_allowed": False,
            "semantic_extraction_flags": {
                "fixture_llm_output_used": True,
                "live_provider_used": False,
                "semantic_extraction_runtime_ready": False,
            },
            "readiness_gate": {
                "required_new_committed_meal_items": 21,
                "required_days_since_last_extraction": 7,
                "fixture_committed_meal_items": committed_count,
                "extraction_allowed_now": extraction_allowed,
                "block_reason": None
                if extraction_allowed
                else "insufficient_committed_meal_items",
            },
            "planned_output_schema": {
                "pattern_type_values": [
                    "contextual_preference",
                    "temporal_preference",
                    "trend_shift",
                    "situational_avoidance",
                ],
                "required_fields": [
                    "pattern_type",
                    "description",
                    "evidence_window_days",
                    "evidence_meal_count",
                    "confidence",
                    "content_hash",
                    "extracted_at",
                ],
                "optional_fields": [
                    "time_condition",
                    "food_category",
                    "trend_direction",
                ],
            },
            "intended_consumers": [
                "recommendation",
                "nightly_insight",
                "confirmed_memory_candidate_review",
            ],
            "shadow_extraction_candidates": _semantic_shadow_candidates(meals),
        },
    )


def _semantic_shadow_candidates(meals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not meals:
        return []
    time_buckets = Counter(_time_bucket(meal.get("logged_at")) for meal in meals)
    bucket, count = _most_common(time_buckets)
    return [
        {
            "candidate_id": f"semantic-shadow-temporal-{_slug(bucket)}",
            "pattern_type": "temporal_preference",
            "description": f"Shadow-only temporal pattern pressure around {bucket} logging.",
            "evidence_meal_count": count,
            "confidence": _confidence(count, threshold=21),
            "llm_extraction_required_later": True,
            "durable_memory_write_allowed": False,
            "runtime_effect_allowed": False,
        }
    ]
