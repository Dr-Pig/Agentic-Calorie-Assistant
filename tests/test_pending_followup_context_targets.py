from __future__ import annotations

from app.intake.application.pending_followup_context_targets import candidate_attachment_targets


def test_pending_followup_candidate_does_not_hide_recent_meal_thread_with_same_numeric_id() -> None:
    targets = candidate_attachment_targets(
        pending_followup={
            "meal_id": 3,
            "source_meal_id": 3,
            "pending_question": "請問您想取消哪一餐？",
        },
        target_meal_reference={"meal_thread_id": 4, "target_resolution_source": "pending_followup_state"},
        recent_committed_meals=[
            {"meal_thread_id": 4, "meal_version_id": 4, "meal_title": "午餐雞肉飯", "total_kcal": 560},
            {"meal_thread_id": 3, "meal_version_id": 3, "meal_title": "早餐店鐵板麵套餐", "total_kcal": 620},
        ],
    )

    target_keys = {
        (target["target_object_type"], target["target_object_id"], target["source"])
        for target in targets
    }
    assert ("pending_followup", "3", "pending_followup") in target_keys
    assert ("meal_thread", "3", "recent_committed_meal") in target_keys
    assert ("meal_thread", "4", "pending_followup_state") in target_keys
    breakfast = next(
        target
        for target in targets
        if target["target_object_type"] == "meal_thread"
        and target["target_object_id"] == "3"
        and target["source"] == "recent_committed_meal"
    )
    assert breakfast["meal_title"] == "早餐店鐵板麵套餐"
    assert breakfast["display_name"] == "早餐店鐵板麵套餐"
    assert breakfast["meal_version_id"] == 3
    assert breakfast["total_kcal"] == 620
