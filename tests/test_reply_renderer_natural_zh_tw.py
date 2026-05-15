from __future__ import annotations

from types import SimpleNamespace

from app.runtime.application.reply_renderer import render_intake_reply
from app.shared.contracts.intake import ComponentEstimate, EstimatePayload


def _remaining_budget(*, remaining_kcal: int) -> SimpleNamespace:
    return SimpleNamespace(
        status="ready",
        daily_target_kcal=1800,
        consumed_kcal=1800 - remaining_kcal,
        remaining_kcal=remaining_kcal,
    )


def _payload(*, total_kcal: int = 650) -> EstimatePayload:
    components = [
        ComponentEstimate(name="鐵板麵", estimated_kcal=430, protein_g=12, carb_g=68, fat_g=14),
        ComponentEstimate(name="荷包蛋", estimated_kcal=90, protein_g=7, carb_g=1, fat_g=7),
        ComponentEstimate(name="早餐店豬肉片", estimated_kcal=130, protein_g=13, carb_g=2, fat_g=8),
    ]
    return EstimatePayload(
        request_id="reply-renderer-natural-zh-tw",
        meal_title="早餐店鐵板麵套餐",
        components=[component.name for component in components],
        component_estimates=components,
        estimated_kcal=total_kcal,
        protein_g=32,
        carb_g=71,
        fat_g=29,
        reply_text="internal fallback",
        action_taken="direct_answer",
        route_target="direct_answer",
        source_decision="ready",
    )


def _generic_payload() -> EstimatePayload:
    component = ComponentEstimate(
        name="雞肉飯",
        estimated_kcal=560,
        source="lookup",
        evidence_role="meal_pattern_prior",
        estimate_basis="anchored",
        confidence_tier="medium",
        quantity_hint="common_serving",
        evidence_ids=["rice_bowl_chicken_rice"],
    )
    return EstimatePayload(
        request_id="reply-renderer-generic-range-basis",
        meal_title="雞肉飯",
        components=[component.name],
        component_estimates=[component],
        component_breakdown=[
            {
                "name": "雞肉飯",
                "estimated_kcal": 560,
                "source_lane": "generic_common_serving",
                "kcal_range": [450, 700],
            }
        ],
        estimated_kcal=560,
        reply_text="internal fallback",
        action_taken="direct_answer",
        route_target="direct_answer",
        source_decision="ready",
        trace_contract={
            "approved_fooddb_evidence_trace": {
                "source_lane": "generic_common_serving",
                "runtime_truth_allowed": True,
                "evidence_ids": ["rice_bowl_chicken_rice"],
                "kcal_range": [450, 700],
            }
        },
    )


def _persistence_result() -> SimpleNamespace:
    return SimpleNamespace(canonical_commit={"meal_version_id": 123})


def _assert_no_internal_words(text: str) -> None:
    forbidden = ["Logged", "Updated", "Total", "Remaining", "commit", "canonical", "manager"]
    assert not any(word in text for word in forbidden)


def test_render_commit_reply_uses_natural_zh_tw_without_internal_status_words() -> None:
    text = render_intake_reply(
        intent_type="log_meal",
        nutrition_payload=_payload(),
        persistence_result=_persistence_result(),
        manager_final_action="commit",
        remaining_budget=_remaining_budget(remaining_kcal=1150),
    )

    assert "已記錄" in text
    assert "約 650 kcal" in text
    assert "今天還剩約 1150 kcal" in text
    assert "鐵板麵 430 kcal" in text
    _assert_no_internal_words(text)


def test_render_correction_reply_uses_natural_zh_tw_and_states_update() -> None:
    text = render_intake_reply(
        intent_type="correct_meal",
        nutrition_payload=_payload(),
        persistence_result=_persistence_result(),
        manager_final_action="correction_applied",
        remaining_budget=_remaining_budget(remaining_kcal=1040),
    )

    assert "已更新" in text
    assert "約 650 kcal" in text
    assert "今天還剩約 1040 kcal" in text
    _assert_no_internal_words(text)


def test_render_correction_removal_prefers_manager_visible_reply_over_target_evidence_payload() -> None:
    payload = EstimatePayload(
        request_id="reply-renderer-remove-meal",
        meal_title="remove 早餐店鐵板麵套餐",
        estimated_kcal=0,
        protein_g=0,
        carb_g=0,
        fat_g=0,
        reply_text="Removed the selected item.",
        action_taken="correction_applied",
        route_target="direct_answer",
        source_decision="ready",
        trace_contract={
            "correction_operation": "remove_meal",
            "target_evidence_contract": {
                "evidence_type": "target_evidence",
                "nutrition_evidence_required": False,
            },
        },
    )

    text = render_intake_reply(
        intent_type="correct_meal",
        nutrition_payload=payload,
        persistence_result=_persistence_result(),
        manager_final_action="correction_applied",
        remaining_budget=_remaining_budget(remaining_kcal=1180),
        manager_answer_contract={"reply_text": "已刪除早餐那筆記錄。"},
    )

    assert text == "已刪除早餐那筆記錄。"
    _assert_no_internal_words(text)


def test_render_no_commit_reply_is_user_facing_zh_tw() -> None:
    text = render_intake_reply(
        intent_type="log_meal",
        nutrition_payload=_payload(),
        persistence_result=None,
        manager_final_action="no_commit",
        remaining_budget=_remaining_budget(remaining_kcal=1150),
    )

    assert text == "這次我沒有記錄到日記裡。你可以再補一句餐點內容，我再幫你估。"
    _assert_no_internal_words(text)


def test_render_generic_common_serving_reply_exposes_range_basis() -> None:
    text = render_intake_reply(
        intent_type="log_meal",
        nutrition_payload=_generic_payload(),
        persistence_result=_persistence_result(),
        manager_final_action="commit",
        remaining_budget=_remaining_budget(remaining_kcal=752),
    )

    assert "已記錄" in text
    assert "雞肉飯 560 kcal" in text
    assert "常見份量" in text
    assert "參考範圍 450-700 kcal" in text
    assert "今天還剩約 752 kcal" in text
    _assert_no_internal_words(text)


def test_render_commit_reply_appends_only_manager_owned_optional_refinement() -> None:
    payload = _payload()
    payload.followup_question = "如果紅茶的糖度或杯型不同，可以補充，我會幫你修正。"
    payload.trace_contract["manager_followup_projection"] = {
        "source": "manager_answer_contract",
        "role": "manager_owned_renderer_projection",
    }

    text = render_intake_reply(
        intent_type="log_meal",
        nutrition_payload=payload,
        persistence_result=_persistence_result(),
        manager_final_action="commit",
        remaining_budget=_remaining_budget(remaining_kcal=1150),
    )

    assert "如果紅茶的糖度或杯型不同" in text
