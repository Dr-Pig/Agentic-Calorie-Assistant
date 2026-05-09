from __future__ import annotations

from app.intake.application.multimodal_voice_input_contract import (
    build_multimodal_voice_input_contract_artifact,
)


REQUIRED_CASES = [
    "food_photo_clear_single_item",
    "food_photo_unclear_requires_description",
    "food_photo_multiple_items_component_candidates",
    "non_food_photo_rejected_as_intake",
    "menu_photo_recommendation_context_only",
    "voice_food_log_transcript_candidate",
    "voice_unclear_requires_confirmation",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(case["case_id"]): case
        for case in artifact["cases"]  # type: ignore[index]
    }


def test_multimodal_voice_contract_is_no_runtime_fixture_only() -> None:
    artifact = build_multimodal_voice_input_contract_artifact()

    assert artifact["artifact_type"] == "accurate_intake_multimodal_voice_input_contract"
    assert artifact["status"] == "pass"
    assert artifact["owner"] == "app/intake"
    assert artifact["consumer"] == "future intake input normalization slices"
    assert artifact["retirement_trigger"] == "approved multimodal_or_voice_runtime_activation_plan"
    assert artifact["local_only"] is True
    assert artifact["diagnostic_only"] is True
    assert artifact["fixture_only"] is True
    assert artifact["runtime_connected"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["media_adapter_connected"] is False
    assert artifact["ocr_provider_invoked"] is False
    assert artifact["transcription_provider_invoked"] is False
    assert artifact["vision_model_invoked"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["meal_thread_created"] is False
    assert artifact["ledger_mutation_authority"] is False
    assert [case["case_id"] for case in artifact["cases"]] == REQUIRED_CASES


def test_photo_cases_create_evidence_candidates_only() -> None:
    by_id = _by_id(build_multimodal_voice_input_contract_artifact())

    clear = by_id["food_photo_clear_single_item"]
    assert clear["modality"] == "photo"
    assert clear["normalized_handoff"] == "intake_evidence_candidate"
    assert clear["evidence_candidate_only"] is True
    assert clear["requires_manager_decision"] is True
    assert clear["ui_thumbnail_binding_allowed"] == "after_meal_commit_only"
    assert clear["meal_thread_created"] is False
    assert clear["food_truth_committed"] is False

    unclear = by_id["food_photo_unclear_requires_description"]
    assert unclear["normalized_handoff"] == "clarification_required"
    assert unclear["ask_first_required"] is True
    assert unclear["estimate_allowed"] is False

    multi = by_id["food_photo_multiple_items_component_candidates"]
    assert multi["normalized_handoff"] == "component_candidate_set"
    assert multi["component_candidates_allowed"] is True
    assert multi["component_candidates_commit_authority"] is False

    non_food = by_id["non_food_photo_rejected_as_intake"]
    assert non_food["normalized_handoff"] == "not_food_or_not_actionable"
    assert non_food["intake_flow_allowed"] is False


def test_menu_photo_and_voice_do_not_activate_recommendation_or_text_intake() -> None:
    by_id = _by_id(build_multimodal_voice_input_contract_artifact())

    menu = by_id["menu_photo_recommendation_context_only"]
    assert menu["modality"] == "photo"
    assert menu["normalized_handoff"] == "recommendation_context_candidate"
    assert menu["recommendation_served"] is False
    assert menu["recommendation_activation_required"] is True

    voice = by_id["voice_food_log_transcript_candidate"]
    assert voice["modality"] == "voice"
    assert voice["normalized_handoff"] == "transcript_candidate"
    assert voice["transcript_text_is_display_only"] is True
    assert voice["text_intake_reentry_allowed"] == "after_transcript_confirmation_only"
    assert voice["meal_thread_created"] is False

    unclear = by_id["voice_unclear_requires_confirmation"]
    assert unclear["normalized_handoff"] == "clarification_required"
    assert unclear["ask_first_required"] is True
    assert unclear["text_intake_reentry_allowed"] == "not_allowed_until_clear"


def test_contract_validator_rejects_runtime_or_mutation_drift() -> None:
    from app.intake.application import multimodal_voice_input_contract as module

    artifact = build_multimodal_voice_input_contract_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases[0] = {
        **dict(cases[0]),
        "meal_thread_created": True,
        "food_truth_committed": True,
    }
    cases[4] = {
        **dict(cases[4]),
        "recommendation_served": True,
    }

    blockers = module._validate_cases(cases)

    assert "food_photo_clear_single_item.meal_thread_created" in blockers
    assert "food_photo_clear_single_item.food_truth_committed" in blockers
    assert "menu_photo_recommendation_context_only.recommendation_served" in blockers
