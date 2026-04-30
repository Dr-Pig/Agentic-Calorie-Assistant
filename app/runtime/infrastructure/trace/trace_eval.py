from __future__ import annotations

from typing import Any


def _is_exact_truth_win_candidate(
    trace_contract: dict[str, Any],
    *,
    best_answer_source: str | None,
) -> bool:
    return (
        trace_contract.get("db_hit_type") == "exact_truth"
        and best_answer_source in {"with_local_knowledge", "primary"}
        and trace_contract.get("match_confidence") == "high"
        and not trace_contract.get("grounding_contradiction")
    )


def evaluate_trace_contract(
    trace_contract: dict[str, Any],
    quality_signals: dict[str, Any],
    *,
    best_answer_source: str | None,
    retry_triggered: bool,
) -> dict[str, Any]:
    manager_output = trace_contract.get("manager_output", {}) or {}
    semantic_decision = (
        trace_contract.get("semantic_decision")
        or manager_output.get("semantic_decision")
        or {}
    )
    normalizer_diff = trace_contract.get("normalizer_diff", {}) or {}
    template_match = trace_contract.get("template_match", {}) or {}
    final_answer = trace_contract.get("final_answer_summary", {}) or {}
    multi_turn = trace_contract.get("multi_turn_context", {}) or {}
    is_multi_turn = multi_turn.get("is_multi_turn", False)

    metrics = {
        "is_manager_intent_food_estimation_correct": (
            semantic_decision.get("current_turn_intent")
            or manager_output.get("intent")
            or manager_output.get("intent_type")
        ) in {"log_meal", "food_estimation", "", None},
        "core_identity_tokens_preserved": not (
            trace_contract.get("normalizer_mode") != "off"
            and normalizer_diff.get("changed")
            and not normalizer_diff.get("normalized_text", "").strip()
        ),
        "risk_flag_was_triggered": len(trace_contract.get("risk_flags", [])) > 0,
        "blocking_slots_coverage": (
            "complete" if len(trace_contract.get("required_checks", [])) > 0 and not quality_signals.get("missing_required_checks")
            else "missing" if quality_signals.get("missing_required_checks")
            else "none"
        ),
        "template_was_activated": bool(template_match),
        "template_activation_appropriateness": (
            "falsely_activated_for_specific_item" if template_match and quality_signals.get("meal_template_kcal_mismatch") and not template_match.get("blocked")
            else "correctly_activated_for_vague_meal" if template_match
            else "skipped"
        ),
        "components_extracted_accurately": not quality_signals.get("missing_components"),
        "LLM_followup_decision_quality": (
            "correctly_asked" if trace_contract.get("followup_policy_decision") in {"clarify_before_estimate", "estimate_with_targeted_followup"} and final_answer.get("decision") == "ASK_USER"
            else "blindly_guessed" if trace_contract.get("followup_policy_decision") == "clarify_before_estimate" and final_answer.get("decision") != "ASK_USER"
            else "safely_estimated"
        ),
        "top_drivers_align_with_slots": not quality_signals.get("missing_expected_drivers"),
        "local_evidence_identity_pass": (
            not trace_contract.get("grounding_contradiction")
            and trace_contract.get("match_confidence") in {"high", "medium"}
        ) if trace_contract.get("grounding_attempts") else True,
        "search_fallback_was_triggered": trace_contract.get("used_search", False),
        "search_evidence_identity_pass": (
            trace_contract.get("search_quality") in {"high", "medium"}
        ) if trace_contract.get("used_search") else True,
        "evidence_was_passed_to_llm": best_answer_source in {"with_local_knowledge", "with_search_evidence", "initial", "retry", "primary"},
        "rescue_was_triggered": False,
        "rescue_reason": "none",
        "rescue_was_successful": False,
        "multi_turn_intent_correct": (
            (is_multi_turn and multi_turn.get("turn_intent") in {"clarification", "modification"})
            or (not is_multi_turn and multi_turn.get("turn_intent") in {"new_intake", "food_estimation", "log_edit", None})
        ),
        "context_injection_present": bool(multi_turn.get("context_injection_snapshot")),
        "retrieval_query_contextual": (not is_multi_turn) or multi_turn.get("retrieval_query_rewritten", False),
    }

    attribution_map = [
        (not metrics["is_manager_intent_food_estimation_correct"], "manager", "Manager intent drifted."),
        (not metrics["core_identity_tokens_preserved"], "normalizer", "Normalizer erased core input."),
        (metrics["template_activation_appropriateness"] == "falsely_activated_for_specific_item", "grounding", "Template overrode specific item."),
        (quality_signals.get("missing_top_uncertainty_drivers"), "layer3_primary_llm", "Missing uncertainty drivers for follow-up case."),
        (trace_contract.get("grounding_contradiction"), "grounding", "Local evidence ID mismatch or contradiction."),
        (not metrics["local_evidence_identity_pass"] and metrics["evidence_was_passed_to_llm"], "grounding", "Local evidence ID mismatch or contradiction."),
        (quality_signals.get("invalid_zero_kcal_candidate"), "layer3_primary_llm", "CRITICAL: Calorie output is 0. This is a hard loss."),
        (quality_signals.get("reference_kcal_mismatch"), "grounding", "Grounded truth not preserved in final answer."),
        (metrics["blocking_slots_coverage"] == "missing" and best_answer_source not in {"with_local_knowledge", "exact_truth", "primary"}, "risk_validator", "Required risk checks were ignored."),
        (metrics["LLM_followup_decision_quality"] == "blindly_guessed", "layer3_primary_llm", "clarification before estimation was required but skipped."),
        (is_multi_turn and not metrics["multi_turn_intent_correct"], "manager", f"Multi-turn intent misclassified as {multi_turn.get('turn_intent')}."),
        (is_multi_turn and not metrics["context_injection_present"], "manager", "Multi-turn context injection failed."),
        (is_multi_turn and not metrics["retrieval_query_contextual"], "grounding", "Retrieval query not contextualized in Turn 2+."),
    ]

    failed_layer = next((layer for condition, layer, _msg in attribution_map if condition), None)
    why = next((msg for condition, _layer, msg in attribution_map if condition), "No regression signal detected.")
    kcal = final_answer.get("estimated_kcal") or quality_signals.get("kcal_most_likely") or 0
    verdict = "loss" if failed_layer else "neutral"

    if verdict == "neutral":
        if _is_exact_truth_win_candidate(trace_contract, best_answer_source=best_answer_source):
            verdict, improved_dimension, why = "win", "exact_truth_correctness", "Exact truth grounding success."
        elif kcal > 0 and best_answer_source != "clarify_user":
            verdict, improved_dimension, why = "win", "delivered_baseline", "Successfully delivered a non-zero calorie baseline."
        elif metrics["LLM_followup_decision_quality"] == "correctly_asked":
            verdict, improved_dimension, why = "win", "followup_correctness", "Properly identified need for clarification."
        elif trace_contract.get("followup_decision") == "must_ask":
            verdict, improved_dimension, why = "win", "followup_correctness", "High-value uncertainty driver identified."
        else:
            improved_dimension = None
    else:
        improved_dimension = None

    return {
        "win_loss_neutral": verdict,
        "failed_layer": failed_layer,
        "why": why,
        "improved_dimension": improved_dimension,
        "regressed_dimension": failed_layer if verdict == "loss" else None,
        "north_star_alignment": "aligned" if verdict != "loss" else "misaligned",
        "observable_metrics": metrics,
    }
