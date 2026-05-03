from __future__ import annotations

from app.composition.dogfood_trace_policy import (
    CHAT_TURN_ROUTE_CONTRACT,
    build_dogfood_review_record,
    build_manager_mode_policy,
    build_session_date_policy,
    build_unsupported_intent_policy,
    build_user_correction_feedback_event,
    validate_canonical_eval_promotion,
)


def test_raw_trace_cannot_become_canonical_eval_without_human_approval() -> None:
    record = build_dogfood_review_record(
        trace_id="turn-unsupported-rescue",
        raw_trace={"request_id": "turn-unsupported-rescue"},
        auto_flags=["unsupported_intent"],
        reviewer_agent_suggestion={
            "review_candidate": True,
            "likely_failure_family": "unsupported_intent",
            "confidence": 0.87,
        },
    )

    assert record["status"] == "review_candidate"
    assert record["raw_trace_is_truth"] is False
    assert record["review_candidate"]["proposed_by"] == ["deterministic_rules", "optional_reviewer_agent"]
    assert record["review_candidate"]["approved_by_required"] is False
    assert record["human_labeled"]["required_for_canonical_eval"] is True
    assert validate_canonical_eval_promotion(record)["allowed"] is False
    assert validate_canonical_eval_promotion(record)["missing"] == [
        "human_approval",
        "product_semantic_source",
        "stable_expected_behavior",
        "regression_test_or_eval_registration",
    ]


def test_canonical_eval_requires_human_label_semantic_source_and_registration() -> None:
    record = build_dogfood_review_record(
        trace_id="turn-luwei-followup",
        raw_trace={"request_id": "turn-luwei-followup"},
        auto_flags=["manager_context_gap"],
        human_label={
            "approved_by": "avery",
            "failure_family": "manager_context_gap",
            "expected_behavior": {"final_action": "commit"},
        },
        promotion={
            "golden_candidate": True,
            "canonical_eval_case": True,
            "product_semantic_source": "composition_unknown_basket_listed_components_policy",
            "stable_expected_behavior": True,
            "regression_test_or_eval_registration": "tests/test_future_eval.py::test_luwei_followup",
        },
    )

    promotion_check = validate_canonical_eval_promotion(record)

    assert record["status"] == "canonical_eval_case"
    assert record["golden_candidate"]["status"] == "candidate_only_until_human_approval"
    assert promotion_check == {"allowed": True, "missing": []}


def test_unsupported_intent_policy_is_answer_only_without_mutation_or_product_claim() -> None:
    for family in ("rescue", "recommendation", "meal_planning", "proactive_reminder", "long_term_memory"):
        policy = build_unsupported_intent_policy(family)

        assert policy["final_action"] == "answer_only"
        assert policy["answer_only_subtype"] in {"general_guidance", "unsupported_intent_notice"}
        assert policy["unsupported_intent_family"] == family
        assert policy["mutation_allowed"] is False
        assert policy["forbidden_side_effects"] == [
            "create_meal_thread",
            "create_food_item",
            "update_daily_target",
            "create_pending_food_draft",
            "create_reminder",
            "create_meal_plan",
        ]
        assert policy["product_capability_claimed"] is False


def test_user_correction_feedback_event_remains_review_material_not_food_truth() -> None:
    event = build_user_correction_feedback_event(
        trace_id="turn-bento-correction",
        original_user_input="我吃雞腿便當",
        original_estimate={"kcal": 900},
        correction_text="飯吃一半",
        correction_type="portion_correction",
        final_accepted_estimate={"kcal": 700},
        likely_failure_family="portion_missing",
    )

    assert event["review_status"] == "raw"
    assert event["food_kb_truth_update_allowed"] is False
    assert event["canonical_eval_promotion_allowed"] is False
    assert event["likely_failure_family"] == "portion_missing"


def test_session_date_policy_blocks_ambiguous_or_unsupported_date_mutation() -> None:
    today = build_session_date_policy(active_local_date="2026-05-04", requested_date="2026-05-04")
    yesterday = build_session_date_policy(active_local_date="2026-05-04", requested_date="2026-05-03")
    ambiguous = build_session_date_policy(active_local_date="2026-05-04", requested_date=None)

    assert today["date_status"] == "supported_current_active_date"
    assert today["mutation_allowed"] is True
    assert yesterday["date_status"] == "limited_or_unsupported"
    assert yesterday["mutation_allowed"] is False
    assert yesterday["required_behavior"] == "block_mutation_or_ask_clarification"
    assert ambiguous["date_status"] == "ambiguous"
    assert ambiguous["mutation_allowed"] is False


def test_manager_mode_policy_keeps_fixture_default_and_kimi_deferred() -> None:
    fixture = build_manager_mode_policy(manager_mode="fixture")
    grokfast = build_manager_mode_policy(
        manager_mode="grokfast_diagnostic",
        provider_profile="builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
        live_call_used=True,
        model_id="grok-4-fast",
    )
    kimi = build_manager_mode_policy(manager_mode="kimi")

    assert fixture["default_for_deterministic_dogfood"] is True
    assert fixture["readiness_claim_allowed"] is False
    assert grokfast["explicit_only"] is True
    assert grokfast["readiness_claim_allowed"] is False
    assert grokfast["trace_fields"]["live_call_used"] is True
    assert kimi["deferred_until_target_model_validation"] is True
    assert kimi["active_runtime_default_allowed"] is False


def test_estimate_route_contract_is_chat_turn_entrypoint_not_estimate_truth_owner() -> None:
    assert CHAT_TURN_ROUTE_CONTRACT["current_route"] == "/estimate"
    assert CHAT_TURN_ROUTE_CONTRACT["semantic_role"] == "accurate_intake_chat_turn_entrypoint"
    assert "unsupported_answer_only" in CHAT_TURN_ROUTE_CONTRACT["manager_may_return"]
    assert CHAT_TURN_ROUTE_CONTRACT["route_name_is_truth_owner"] is False
