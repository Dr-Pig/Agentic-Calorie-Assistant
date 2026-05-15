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
        "turn that explicitly lists concrete food components, include them in semantic_decision.listed_items, set retrieval_goal='listed_item_lookup', and do not classify that turn as composition-unknown; for a listed-item follow-up, call estimate_nutrition and do not repeat the same composition clarification. If guard_feedback.failure_family is nutrition_evidence_not_commit_eligible, guard rejected a Manager-proposed commit; choose legal final ask_followup/no_mutation/tool_calls=[] and never commit a fallback value. "
        + refinement_policy.COMPOSITION_REFINEMENT_AFTER_BASIS_QUERY_DESCRIPTION
        + "If followup_posture is refinement_not_commit_gate or size_clarification, include a followup_question. "
        "If you do not have a concrete follow-up question, use none, closed, or refinement_optional."
    )


__all__ = ["founder_live_manager_tool_description"]
