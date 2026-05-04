from __future__ import annotations


def _default_consumers(candidate_type: str) -> list[str]:
    if candidate_type == "golden_order":
        return ["recommendation", "intake_clarification", "chat_context"]
    if candidate_type == "food_preference":
        return ["recommendation", "proactive", "intake_clarification"]
    if candidate_type == "negative_preference":
        return ["recommendation", "proactive", "intake_clarification"]
    if candidate_type == "temporary_preference":
        return [
            "recommendation",
            "chat_context",
            "proactive",
            "intake_clarification",
        ]
    if candidate_type == "logging_adherence_pattern":
        return ["calibration", "proactive", "rescue_later"]
    if candidate_type == "intake_estimation_bias":
        return [
            "calibration",
            "intake_risk_tagging",
            "nutrition_clarify_priority",
            "response_context",
        ]
    if candidate_type == "user_language_pattern":
        return ["intake_clarification", "chat_context", "recommendation"]
    if candidate_type == "app_usage_style":
        return ["chat_context", "proactive", "ux", "recommendation_presentation"]
    if candidate_type == "interaction_preference":
        return ["response_generation", "chat_context", "proactive_message_style"]
    if candidate_type == "conversation_recall_context":
        return ["chat_context", "intake_clarification", "recommendation", "calibration"]
    return ["recommendation", "proactive"]


def _consumer_use_hints(consumers: list[str]) -> dict[str, str]:
    hints: dict[str, str] = {}
    for consumer in consumers:
        if consumer == "calibration":
            hints[consumer] = (
                "Use only as confidence or attribution context; never rewrite calibration truth."
            )
        elif consumer in {"intake_clarification", "nutrition_clarify_priority"}:
            hints[consumer] = (
                "Use to prioritize clarification in shadow review, not to default food truth."
            )
        elif consumer in {"chat_context", "response_generation", "response_context"}:
            hints[consumer] = (
                "Use as future response-context candidate only after human review."
            )
        elif consumer.startswith("proactive"):
            hints[consumer] = (
                "Use only for no-send simulation until proactive activation is approved."
            )
        elif consumer == "rescue_later":
            hints[consumer] = (
                "Secondary rescue input only; no rescue proposal or budget mutation."
            )
        else:
            hints[consumer] = "Use as review-only context value signal."
    return hints


def _risk_if_wrong(candidate_type: str) -> str:
    if candidate_type == "intake_estimation_bias":
        return "Could misattribute calibration mismatch to user behavior and change clarification priority too early."
    if candidate_type == "user_language_pattern":
        return "Could misunderstand the user's phrasing and bias intake clarification."
    if candidate_type == "app_usage_style":
        return "Could personalize chat or reminders in a way the user did not actually prefer."
    if candidate_type == "interaction_preference":
        return "Could alter response style before the preference is confirmed."
    if candidate_type in {"food_preference", "golden_order"}:
        return (
            "Could overfit recommendations or intake defaults to a weak food pattern."
        )
    if candidate_type == "negative_preference":
        return "Could suppress acceptable foods or recommendations before a dislike is confirmed."
    if candidate_type == "temporary_preference":
        return "Could keep a short-term preference active after it should expire."
    if candidate_type == "logging_adherence_pattern":
        return "Could overstate adherence or logging quality and distort calibration confidence."
    if candidate_type == "conversation_recall_context":
        return "Could retrieve stale or irrelevant conversation history and pollute current-turn context."
    return "Could inject unconfirmed context into future runtime behavior."


def _promotion_path(candidate_type: str) -> str:
    if candidate_type == "temporary_preference":
        return "human_review_then_time_bounded_l3_confirmed_memory_later"
    if candidate_type in {
        "golden_order",
        "food_preference",
        "negative_preference",
        "user_language_pattern",
        "intake_estimation_bias",
        "app_usage_style",
        "interaction_preference",
    }:
        return "human_review_then_l3_confirmed_memory_later"
    if candidate_type == "conversation_recall_context":
        return "future_tool_mediated_recall_contract_review_only"
    return "keep_shadowing_until_consumer_value_review"


def _candidate_non_runtime_truth_reason(candidate_type: str) -> str:
    if candidate_type == "golden_order":
        return (
            "Golden orders are materialized review views over MealThread history; "
            "they do not replace canonical MealThread or FoodDB truth."
        )
    if candidate_type == "intake_estimation_bias":
        return (
            "Bias posture is calibration context only; it cannot rewrite calorie, "
            "BodyPlan, or DayBudgetLedger truth."
        )
    if candidate_type == "conversation_recall_context":
        return (
            "Conversation recall remains summary-first future retrieval context; "
            "no transcript is injected into ManagerContextPacket."
        )
    return (
        "This is an offline shadow candidate derived from fixture/export evidence "
        "for human review; runtime truth and mutation authority stay unchanged."
    )


def _artifact_risk_if_wrong(artifact_type: str) -> str:
    if artifact_type == "artifact_registry_manifest":
        return "Could hide an unowned or pseudo-runtime artifact from reviewer triage."
    if "recommendation" in artifact_type:
        return "Could overstate recommendation readiness or ranking value before runtime review."
    if "proactive" in artifact_type:
        return "Could make no-send trigger candidates look like approved sends."
    if "rescue" in artifact_type:
        return "Could imply rescue viability or budget mutation authority too early."
    if "context_pack" in artifact_type:
        return "Could make shadow context packs look ready for ManagerContextPacket injection."
    if "framework" in artifact_type:
        return "Could over-adopt external framework patterns over canonical L4A/L4C/L4D specs."
    return "Could overstate unconfirmed long-term context as product or runtime truth."


def _artifact_promotion_path(artifact_type: str) -> str:
    if artifact_type == "artifact_registry_manifest":
        return "review_manifest_then_keep_or_defer_each_artifact"
    if "context_pack" in artifact_type:
        return "human_review_then_future_context_pack_contract_slice"
    if "recommendation" in artifact_type:
        return "human_review_then_future_recommendation_shadow_eval_slice"
    if "proactive" in artifact_type:
        return "human_review_then_future_no_send_scheduler_eval_slice"
    if "rescue" in artifact_type:
        return "human_review_then_future_rescue_shadow_eval_slice"
    if "framework" in artifact_type:
        return "research_review_only_no_runtime_adoption"
    return "human_review_then_keep_shadowing_or_defer"


def _artifact_non_runtime_truth_reason(artifact_type: str) -> str:
    return (
        f"{artifact_type} is generated by the offline shadow lab for review only; "
        "it cannot write durable memory, mutate canonical product objects, or inject "
        "ManagerContextPacket context."
    )
