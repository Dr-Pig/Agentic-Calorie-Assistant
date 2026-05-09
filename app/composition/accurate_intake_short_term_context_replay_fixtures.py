from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.runtime.contracts.pending_meal_intent import PendingMealIntent


def _meal(
    *,
    thread_id: int,
    version_id: int,
    title: str,
    item_names: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "meal_thread_id": thread_id,
        "meal_version_id": version_id,
        "meal_title": title,
        "occurred_at": "2026-05-05T12:30:00",
        "item_resolution_source": "runtime_replay_fixture_state",
        "item_candidates": [
            {
                "meal_item_id": thread_id * 100 + index,
                "canonical_name": item_name,
                "item_index": index,
                "estimated_kcal": 100 + index * 20,
                "mutation_authority": False,
                "selected_target": False,
            }
            for index, item_name in enumerate(item_names, start=1)
        ],
    }


def _recent_chat(count: int) -> list[dict[str, Any]]:
    return [
        {
            "message_id": index,
            "role": "user" if index % 2 else "assistant",
            "content": f"context replay prior turn {index}",
            "created_at": f"2026-05-05T10:{index % 60:02d}:00",
            "trace_id": f"prior-{index}",
            "local_date": "2026-05-05",
            "read_only": True,
            "mutation_authority": False,
            "source": "runtime_replay_fixture_state",
        }
        for index in range(1, count + 1)
    ]


def _target_reference(
    *,
    thread_id: int,
    version_id: int,
    title: str,
    source: str,
    confidence: str = "high",
    item_id: int | None = None,
    canonical_name: str | None = None,
) -> dict[str, Any]:
    ref: dict[str, Any] = {
        "meal_thread_id": thread_id,
        "meal_version_id": version_id,
        "meal_title": title,
        "target_resolution_source": source,
        "correction_confidence": confidence,
        "item_resolution_source": "runtime_replay_fixture_state",
    }
    if item_id is not None:
        ref["meal_item_id"] = item_id
    if canonical_name is not None:
        ref["canonical_name"] = canonical_name
    return ref


def _pending_meal_trace(
    *,
    intent_id: str,
    candidate_title: str,
    status: str,
    source_surface: str,
) -> dict[str, Any]:
    created_at = datetime(2026, 5, 5, 10, 0, tzinfo=UTC)
    intent = PendingMealIntent(
        intent_id=intent_id,
        user_id="short-term-context-runtime-replay-user",
        candidate_title=candidate_title,
        source_surface=source_surface,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        created_at=created_at,
        expires_at=created_at + timedelta(hours=6),
    )
    return intent.to_trace_payload()


def short_term_context_replay_scenario_specs() -> list[dict[str, Any]]:
    drink_meal = _meal(thread_id=31, version_id=310, title="bubble tea", item_names=("bubble tea",))
    rice_meal = _meal(thread_id=41, version_id=410, title="lunch rice", item_names=("rice", "egg"))
    luwei_meal = _meal(
        thread_id=51,
        version_id=510,
        title="luwei",
        item_names=("tofu", "seaweed", "fish ball"),
    )
    return [
        {
            "scenario_id": "remove_previous_item",
            "raw_user_input": "把剛剛那個拿掉",
            "expected_context_posture": "ambiguous_until_manager_decision",
            "recent_committed_meals": [luwei_meal],
            "target_meal_reference": _target_reference(
                thread_id=51,
                version_id=510,
                title="luwei",
                source="recent_committed_meal",
                confidence="medium",
            ),
        },
        {
            "scenario_id": "remove_named_item",
            "raw_user_input": "豆干拿掉",
            "expected_context_posture": "candidate_supported",
            "recent_committed_meals": [luwei_meal],
        },
        {
            "scenario_id": "modify_drink_sugar",
            "raw_user_input": "那杯改半糖",
            "expected_context_posture": "candidate_supported",
            "recent_committed_meals": [drink_meal],
        },
        {
            "scenario_id": "modify_rice_portion",
            "raw_user_input": "飯改少一點",
            "expected_context_posture": "candidate_supported",
            "recent_committed_meals": [rice_meal],
        },
        {
            "scenario_id": "correct_previous_identity",
            "raw_user_input": "剛剛那個其實不是拿鐵",
            "expected_context_posture": "ambiguous_until_manager_decision",
            "recent_committed_meals": [drink_meal],
            "target_meal_reference": _target_reference(
                thread_id=31,
                version_id=310,
                title="drink",
                source="recent_committed_meal",
                confidence="medium",
            ),
        },
        {
            "scenario_id": "pending_followup_answer",
            "raw_user_input": "有豆干、海帶、貢丸",
            "expected_context_posture": "pending_followup_pinned",
            "pending_followup": {
                "is_open": True,
                "meal_id": 51,
                "meal_thread_id": 51,
                "pending_question": "請列出滷味品項",
                "expected_answer_type": "listed_basket_components",
            },
            "target_meal_reference": _target_reference(
                thread_id=51,
                version_id=510,
                title="luwei",
                source="pending_followup_state",
            ),
        },
        {
            "scenario_id": "long_chat_with_pinned_pending_draft",
            "raw_user_input": "剛剛那份滷味裡還有米血",
            "expected_context_posture": "pending_draft_pinned_despite_recent_window",
            "recent_chat_turns": _recent_chat(28),
            "pending_draft": {
                "meal_thread_id": 61,
                "meal_version_id": 610,
                "meal_title": "luwei draft",
                "resolution_status": "draft_unresolved",
            },
            "target_meal_reference": _target_reference(
                thread_id=61,
                version_id=610,
                title="luwei draft",
                source="pending_draft_state",
            ),
        },
        {
            "scenario_id": "future_meal_intent_from_recommendation",
            "raw_user_input": "等等就吃這個",
            "expected_context_posture": "short_term_context_only",
            "case_provenance": "runtime_observed_replay_seed",
            "pending_meal_intent_trace": _pending_meal_trace(
                intent_id="pending-meal-recommendation-001",
                candidate_title="low-calorie chicken bento candidate",
                status="created",
                source_surface="recommendation_card",
            ),
        },
        {
            "scenario_id": "cancel_pending_meal_intent",
            "raw_user_input": "先不要這個",
            "expected_context_posture": "pending_intent_dismissal_only",
            "case_provenance": "runtime_observed_replay_seed",
            "pending_meal_intent_trace": _pending_meal_trace(
                intent_id="pending-meal-recommendation-001",
                candidate_title="low-calorie chicken bento candidate",
                status="dismissed",
                source_surface="recommendation_card",
            ),
        },
    ]


__all__ = ["short_term_context_replay_scenario_specs"]
