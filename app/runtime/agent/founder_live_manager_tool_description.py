from __future__ import annotations

from app.runtime.agent import founder_live_manager_composition_refinement_policy as refinement_policy


def founder_live_manager_tool_description() -> str:
    return (
        "Return the ManagerRuntime structured decision payload. Follow the system prompt and founder live "
        "manager contract; this tool description is compact transport guidance, not product truth. Always include "
        "required top-level fields. Use tool_calls=[] when manager_action is final; use a non-empty tool_calls "
        "array with supported tool names when manager_action is call_tools. Do not collapse query-only, estimate-basis inquiry, or correction turns into log_meal: "
        "answer_query uses intent_type='answer_query' and no mutation; estimate-basis inquiries use answer_query/answer_only/tool_calls=[] with "
        "answer_contract.answer_basis from manager_context_packet_v1 when available; answer those basis questions in user-facing language without exposing LLM/llm_only/internal enum labels or unsupported macro gram claims; "
        "correct_meal uses intent_type='correct_meal' with correction_applied/correction_write. Do not use ask_followup, "
        "no_commit, or answer_only as substitutes for evidence-required commit/correction_applied/overshoot_note; "
        "call estimate_nutrition first unless user_provided_kcal_evidence is already present. For a named-food kcal conflict such as a whole bowl or plate with suspicious kcal, do not treat it as a kcal-only shortcut. If you set evidence_posture to requires_tool or evidence_missing, use "
        "manager_action call_tools with estimate_nutrition; the invalid evidence-required candidate pattern is "
        "manager_action final while final_action_candidate still points at commit/correction/overshoot. If target_evidence_present is true with target_evidence_operation "
        "remove_item or target_evidence_operation remove_meal, finalize correction_applied and do not call resolve_correction_target again; "
        "use versioned whole-meal removal only when the Manager-selected meal_thread_id has been validated; do not "
        "hard-delete or rely on deterministic raw text routing. For a composition-unknown "
        "self-selected basket or unanchored patterned combo, return final ask_followup directly, use tool_calls=[] for composition-unknown "
        "ask_followup, and do not call estimate_nutrition for composition-unknown baskets; "
        "manager_action call_tools is invalid for composition-unknown baskets. For a "
        "specific branded product/drink or a turn that explicitly asks to check/search nutrition because FoodDB may be missing it, "
        "preserve brand/product fields and use semantic_decision.retrieval_goal='exact_brand_lookup'; external/WebSearch evidence is candidate-only until approved. "
        "For a named brand or chain menu set meal, include base_dish or product identity, use exact_brand_lookup before asking composition, and do not downgrade it to a composition-unknown basket until the evidence tool rejects or misses. "
        "Do not use generic_anchor_lookup for exact branded lookup requests. For a "
        "turn that explicitly lists concrete food components, include them in semantic_decision.listed_items, set retrieval_goal='listed_item_lookup', and do not classify that turn as composition-unknown; for a listed-item follow-up, call estimate_nutrition and do not repeat the same composition clarification. "
        "For a brand combo with user-listed components, the listed-items rule has priority over exact brand lookup: set retrieval_goal='listed_item_lookup' and do not repeat the component-list question; use the component evidence result to commit or explain rejected/missing sources. "
        "If semantic_decision.listed_items is non-empty, retrieval_goal must be retrieval_goal='listed_item_lookup'; never exact_brand_lookup with non-empty listed_items. "
        "For a branded combo plus concrete items in the same turn, put the main item and named side/drink items in semantic_decision.listed_items before calling estimate_nutrition. "
        "For a correction that removes an item or changes a portion, use existing context components, keep unchanged components, use operation='update_meal_components', call estimate_nutrition for the updated list, and do not ask for already-known context facts; do not use operation='correct_item'. "
        "For named meal-slot removal, select a matching meal_thread_id from provided candidates; target_display_name alone is not enough, and never expose meal_thread_id in user-facing reply_text. "
        "If guard_feedback.failure_family is nutrition_evidence_not_commit_eligible, guard rejected a Manager-proposed commit; choose legal final ask_followup/no_mutation/tool_calls=[] and never commit a fallback value. "
        "If guard_feedback.failure_family is named_food_user_kcal_conflict_requires_confirmation, your own semantic decision marked a named-food kcal conflict; ask the user to confirm the kcal or portion before logging, and do not commit the system estimate. "
        "If manager_contract_evidence_state.target_validation_failure_family is manager_thread_target_proposal_ambiguous, ask a target clarification with no mutation and do not retry the same rejected target. "
        "If guard_feedback.failure_family is pending_followup_attach_requires_commit, the prior pending target is an unresolved draft; repair by returning log_meal/commit/canonical_write, not correct_meal/correction_applied. "
        + refinement_policy.COMPOSITION_REFINEMENT_AFTER_BASIS_QUERY_DESCRIPTION
        + "If followup_posture is refinement_optional, refinement_not_commit_gate, or size_clarification, include a followup_question. "
        "If you do not have a concrete follow-up question, use none or closed."
    )


__all__ = ["founder_live_manager_tool_description"]
