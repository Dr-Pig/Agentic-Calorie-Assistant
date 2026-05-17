from __future__ import annotations

from typing import Any


def pending_followup_object_ref(pending_followup: dict[str, Any] | None) -> dict[str, Any]:
    if pending_followup is None:
        return {"meal_thread_id": None}
    object_ref: dict[str, Any] = {"meal_thread_id": pending_followup.get("meal_thread_id")}
    for key in ("meal_version_id", "meal_id", "source_meal_id", "runtime_turn_id", "assistant_message_id"):
        value = pending_followup.get(key)
        if value is not None:
            object_ref[key] = value
    return object_ref


def candidate_attachment_targets(
    *,
    pending_followup: dict[str, Any] | None,
    target_meal_reference: dict[str, Any],
    recent_committed_meals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add_target(target: dict[str, Any]) -> None:
        target_id = str(target.get("target_object_id") or "").strip()
        target_type = str(target.get("target_object_type") or "").strip()
        seen_key = (target_type, target_id)
        if not target_id or seen_key in seen:
            return
        seen.add(seen_key)
        targets.append(target)

    pending_target = _pending_followup_target(pending_followup)
    if pending_target:
        add_target(pending_target)
    add_target(
        _meal_thread_target(
            target_meal_reference.get("meal_thread_id"),
            source=str(target_meal_reference.get("target_resolution_source") or "target_meal_reference"),
            confidence=str(target_meal_reference.get("correction_confidence") or "medium"),
            meal_title=target_meal_reference.get("meal_title"),
            meal_version_id=target_meal_reference.get("meal_version_id"),
        )
    )
    for meal in recent_committed_meals:
        add_target(
            _meal_thread_target(
                meal.get("meal_thread_id"),
                source="recent_committed_meal",
                confidence="medium",
                meal_title=meal.get("meal_title"),
                meal_version_id=meal.get("meal_version_id"),
                total_kcal=meal.get("total_kcal"),
                occurred_at=meal.get("occurred_at"),
            )
        )
    return targets


def _pending_followup_target(pending_followup: dict[str, Any] | None) -> dict[str, Any]:
    if pending_followup is None:
        return {}
    meal_thread_id = pending_followup.get("meal_thread_id")
    if meal_thread_id is not None:
        return _meal_thread_target(meal_thread_id, source="pending_followup", confidence="high")
    target_id = pending_followup.get("source_meal_id") or pending_followup.get("meal_id")
    target = _base_target(
        target_id,
        target_object_type="pending_followup",
        source="pending_followup",
        confidence="high",
    )
    for key in ("meal_id", "source_meal_id"):
        value = pending_followup.get(key)
        if value is not None:
            target[key] = value
    question = pending_followup.get("pending_question") or pending_followup.get("question")
    if question is not None:
        target["pending_question"] = question
    return target


def _meal_thread_target(
    meal_thread_id: Any,
    *,
    source: str,
    confidence: str,
    meal_title: Any | None = None,
    meal_version_id: Any | None = None,
    total_kcal: Any | None = None,
    occurred_at: Any | None = None,
) -> dict[str, Any]:
    target = _base_target(
        meal_thread_id,
        target_object_type="meal_thread",
        source=source,
        confidence=confidence,
    )
    if not target:
        return target
    for key, value in {
        "meal_title": meal_title,
        "display_name": meal_title,
        "meal_version_id": meal_version_id,
        "total_kcal": total_kcal,
        "occurred_at": occurred_at,
    }.items():
        if value not in (None, ""):
            target[key] = value
    return target


def _base_target(
    target_id: Any,
    *,
    target_object_type: str,
    source: str,
    confidence: str,
) -> dict[str, Any]:
    normalized = str(target_id).strip() if target_id is not None else ""
    if not normalized:
        return {}
    return {
        "target_object_type": target_object_type,
        "target_object_id": normalized,
        "source": source,
        "confidence": confidence,
        "mutation_authority": False,
    }


__all__ = ["candidate_attachment_targets", "pending_followup_object_ref"]
