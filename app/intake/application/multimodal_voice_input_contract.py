from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


_REQUIRED_CASE_IDS = (
    "food_photo_clear_single_item",
    "food_photo_unclear_requires_description",
    "food_photo_multiple_items_component_candidates",
    "non_food_photo_rejected_as_intake",
    "menu_photo_recommendation_context_only",
    "voice_food_log_transcript_candidate",
    "voice_unclear_requires_confirmation",
)

_SEMANTIC_OWNER = "future_intake_manager_or_provider_structured_output"
_DETERMINISTIC_ROLE = "validate_contract_boundaries_and_handoff"
_CASE_FALSE_FIELDS = (
    "evidence_candidate_only",
    "estimate_allowed",
    "component_candidates_allowed",
    "component_candidates_commit_authority",
    "transcript_text_is_display_only",
    "recommendation_activation_required",
    "media_adapter_connected",
    "ocr_provider_invoked",
    "transcription_provider_invoked",
    "vision_model_invoked",
    "live_llm_invoked",
    "recommendation_served",
    "meal_thread_created",
    "food_truth_committed",
    "ledger_mutation_authority",
    "proposal_state_changed",
    "manager_context_packet_schema_changed",
    "runtime_connected",
)
_ARTIFACT_FALSE_FIELDS = (
    "runtime_connected",
    "runtime_truth_changed",
    "mutation_changed",
    "manager_context_packet_schema_changed",
    "media_adapter_connected",
    "ocr_provider_invoked",
    "transcription_provider_invoked",
    "vision_model_invoked",
    "live_llm_invoked",
    "recommendation_served",
    "meal_thread_created",
    "ledger_mutation_authority",
)


def _base_case(
    *,
    case_id: str,
    modality: str,
    source_surface: str,
    user_visible_input_summary: str,
    normalized_handoff: str,
    expected_workflow_effect: str,
    ask_first_required: bool = False,
    requires_manager_decision: bool = True,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "modality": modality,
        "source_surface": source_surface,
        "user_visible_input_summary": user_visible_input_summary,
        "normalized_handoff": normalized_handoff,
        "expected_workflow_effect": expected_workflow_effect,
        "ask_first_required": ask_first_required,
        "requires_manager_decision": requires_manager_decision,
        "semantic_owner": _SEMANTIC_OWNER,
        "deterministic_role": _DETERMINISTIC_ROLE,
        "media_ref_read_only": True,
        "text_intake_reentry_allowed": "not_applicable",
        "ui_thumbnail_binding_allowed": "not_allowed_until_commit",
        "intake_flow_allowed": True,
        **dict.fromkeys(_CASE_FALSE_FIELDS, False),
    }


def _cases() -> list[dict[str, Any]]:
    return [
        _base_case(
            case_id="food_photo_clear_single_item",
            modality="photo",
            source_surface="chat_attachment",
            user_visible_input_summary="food photo that appears to contain one bowl of noodles",
            normalized_handoff="intake_evidence_candidate",
            expected_workflow_effect="manager_decides_intake_or_clarify",
        )
        | {"evidence_candidate_only": True, "ui_thumbnail_binding_allowed": "after_meal_commit_only"},
        _base_case(
            case_id="food_photo_unclear_requires_description",
            modality="photo",
            source_surface="chat_attachment",
            user_visible_input_summary="blurred or low-light food photo",
            normalized_handoff="clarification_required",
            expected_workflow_effect="ask_user_to_describe_food",
            ask_first_required=True,
        ),
        _base_case(
            case_id="food_photo_multiple_items_component_candidates",
            modality="photo",
            source_surface="chat_attachment",
            user_visible_input_summary="bento photo with several visible items",
            normalized_handoff="component_candidate_set",
            expected_workflow_effect="manager_may_itemize_or_ask",
        )
        | {"evidence_candidate_only": True, "component_candidates_allowed": True},
        _base_case(
            case_id="non_food_photo_rejected_as_intake",
            modality="photo",
            source_surface="chat_attachment",
            user_visible_input_summary="non-food image",
            normalized_handoff="not_food_or_not_actionable",
            expected_workflow_effect="explain_not_food_and_request_food_or_text",
            ask_first_required=True,
            requires_manager_decision=False,
        )
        | {"intake_flow_allowed": False},
        _base_case(
            case_id="menu_photo_recommendation_context_only",
            modality="photo",
            source_surface="chat_attachment",
            user_visible_input_summary="restaurant menu photo asking what to order",
            normalized_handoff="recommendation_context_candidate",
            expected_workflow_effect="defer_to_future_recommendation_contract",
        )
        | {"evidence_candidate_only": True, "recommendation_activation_required": True},
        _base_case(
            case_id="voice_food_log_transcript_candidate",
            modality="voice",
            source_surface="chat_voice_input",
            user_visible_input_summary="voice says a lu rou fan and unsweetened soy milk",
            normalized_handoff="transcript_candidate",
            expected_workflow_effect="confirm_transcript_before_text_intake_reentry",
        )
        | {
            "transcript_text_is_display_only": True,
            "text_intake_reentry_allowed": "after_transcript_confirmation_only",
        },
        _base_case(
            case_id="voice_unclear_requires_confirmation",
            modality="voice",
            source_surface="chat_voice_input",
            user_visible_input_summary="unclear voice clip",
            normalized_handoff="clarification_required",
            expected_workflow_effect="show_transcript_candidate_and_ask_confirmation",
            ask_first_required=True,
        )
        | {"transcript_text_is_display_only": True, "text_intake_reentry_allowed": "not_allowed_until_clear"},
    ]


def _validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    case_ids = [str(case.get("case_id") or "") for case in cases]
    if case_ids != list(_REQUIRED_CASE_IDS):
        blockers.append("required_case_order_mismatch")
    for case in cases:
        case_id = str(case.get("case_id") or "unknown")
        for field in _CASE_FALSE_FIELDS:
            if case.get(field) is not False and field.endswith(
                (
                    "_connected",
                    "_invoked",
                    "_served",
                    "_created",
                    "_committed",
                    "_authority",
                    "_changed",
                )
            ):
                blockers.append(f"{case_id}.{field}")
        if case.get("semantic_owner") != _SEMANTIC_OWNER:
            blockers.append(f"{case_id}.semantic_owner_drift")
        if case.get("deterministic_role") != _DETERMINISTIC_ROLE:
            blockers.append(f"{case_id}.deterministic_role_drift")
    return blockers


def build_multimodal_voice_input_contract_artifact() -> dict[str, Any]:
    cases = _cases()
    blockers = _validate_cases(cases)
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_multimodal_voice_input_contract",
        "status": "pass" if not blockers else "fail",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "owner": "app/intake",
        "consumer": "future intake input normalization slices",
        "retirement_trigger": "approved multimodal_or_voice_runtime_activation_plan",
        "claim_scope": "no_runtime_multimodal_voice_input_contract_fixture",
        "local_only": True,
        "diagnostic_only": True,
        "fixture_only": True,
        **dict.fromkeys(_ARTIFACT_FALSE_FIELDS, False),
        "best_practice_evidence": {
            "required": False,
            "rationale": "fixture-only no-runtime input contract; no provider, route, API, security, or runtime design is added",
        },
        "blockers": blockers,
        "summary": {
            "case_count": len(cases),
            "photo_case_count": sum(1 for case in cases if case["modality"] == "photo"),
            "voice_case_count": sum(1 for case in cases if case["modality"] == "voice"),
            "ask_first_case_count": sum(1 for case in cases if case["ask_first_required"]),
        },
        "cases": cases,
    }


__all__ = ["build_multimodal_voice_input_contract_artifact"]
