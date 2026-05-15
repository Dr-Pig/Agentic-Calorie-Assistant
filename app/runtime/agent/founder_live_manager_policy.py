from __future__ import annotations

from app.runtime.agent import founder_live_manager_composition_refinement_policy as refinement_policy
from app.runtime.agent.founder_live_manager_allowed_values import (
    FOUNDER_LIVE_MANAGER_EVIDENCE_REQUIRED_FINAL_ACTIONS,
    FOUNDER_LIVE_MANAGER_FOLLOWUP_QUESTION_REQUIRED_POSTURES,
    FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT,
)
from app.runtime.agent.founder_live_manager_removal_policy import EXPLICIT_WHOLE_MEAL_REMOVAL_RULE


FOUNDER_LIVE_MANAGER_CONTRACT_POLICY = {
    "intent_type_by_semantic_intent": dict(FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT),
    "final_actions_requiring_evidence": list(FOUNDER_LIVE_MANAGER_EVIDENCE_REQUIRED_FINAL_ACTIONS),
    "required_tool_when_evidence_missing": "estimate_nutrition",
    "query_only_rule": {
        "semantic_intent": "answer_query",
        "intent_type": "answer_query",
        "workflow_effect": "answer_only",
        "final_action": "answer_only",
        "mutation_intent_candidate": "no_mutation",
        "basis_source": "manager_context_packet_v1.active_day_state.active_meal_estimate_basis",
        "estimate_basis_forbidden": ["route_to_intake", "correction_write", "canonical_write", "estimate_nutrition"],
    },
    "correction_rule": {
        "semantic_intent": "correct_meal",
        "intent_type": "correct_meal",
        "final_action": "correction_applied",
        "mutation_intent_candidate": "correction_write",
    },
    "explicit_item_removal_rule": {
        "semantic_intent": "correct_meal",
        "workflow_family": "correction",
        "operation": "remove_item",
        "evidence_type": "target_evidence",
        "nutrition_evidence_required": False,
        "manager_role": "propose_target_or_call_resolve_correction_target",
        "runtime_role": "validate_unique_writable_target",
        "forbidden": ["hard_delete", "whole_meal_undo", "raw_text_deterministic_routing"],
    },
    "explicit_whole_meal_removal_rule": EXPLICIT_WHOLE_MEAL_REMOVAL_RULE,
    "composition_unknown_rule": {
        "workflow_effect": "ask_followup",
        "final_action": "ask_followup",
        "mutation_intent_candidate": "no_mutation",
        "required_manager_action": "final",
        "required_tool_calls": [],
        "forbidden_tool": "estimate_nutrition",
        "estimate_tool_allowed": False,
    },
    "listed_basket_followup_rule": {
        "semantic_intent": "log_meal",
        "workflow_family": "listed_item_followup_after_clarification",
        "required_tool_when_evidence_missing": "estimate_nutrition",
        "forbidden_substitute_final_actions": ["ask_followup", "no_commit", "answer_only"],
        "runtime_role": "validate_evidence_packet_and_final_mapping_only",
    },
    "composition_refinement_after_basis_query_rule": refinement_policy.COMPOSITION_REFINEMENT_AFTER_BASIS_QUERY_RULE,
    "followup_question_rule": {
        "question_required_postures": sorted(FOUNDER_LIVE_MANAGER_FOLLOWUP_QUESTION_REQUIRED_POSTURES),
        "fallback_postures_when_no_question": ["none", "closed"],
    },
    "followup_question_required_postures": sorted(FOUNDER_LIVE_MANAGER_FOLLOWUP_QUESTION_REQUIRED_POSTURES),
    "forbidden_repair_shortcuts": ["case_id_matching", "raw_text_matching", "food_name_specific_patch", "deterministic_semantic_rewrite"],
}

FOUNDER_LIVE_MANAGER_CONTRACT_POLICY_SUMMARY = (
    "Founder live manager contract policy: keep intent_type aligned with semantic_decision.current_turn_intent "
    "by workflow effect: answer_query -> answer_query, log_meal -> log_meal, correct_meal -> correct_meal, "
    "with onboarding/budget lanes using their own explicit intent_type; "
    "if no current estimate_nutrition tool result exists, call estimate_nutrition before final commit, "
    "nutrition-changing correction_applied, or overshoot_note; query-only nutrition questions must answer_only with no mutation; "
    "estimate-basis questions about a prior meal's assumed composition or why/how it was estimated are answer_query/answer_only/no_mutation and must not route_to_intake; "
    "correct_meal must update the prior target with correction_applied/correction_write, not commit as a new meal; "
    "explicit removal is a correction-family turn: propose a target item/thread or call resolve_correction_target, "
    "then let runtime validate target uniqueness/writeability; target evidence is sufficient for remove_item or "
    "versioned whole-meal removal and estimate_nutrition is not required; if target_evidence_present=true with "
    "target_evidence_operation='remove_item' or target_evidence_operation='remove_meal', finalize correction_applied without "
    "calling resolve_correction_target again; do not hard-delete, and for whole meal deletion use operation='remove_meal' "
    "with a Manager-selected meal_thread_id; "
    "self-selected basket, unanchored patterned combo, or composition-unknown meals must ask_followup/no_mutation until components are known "
    "and must not call estimate_nutrition while composition is unknown; manager_action=call_tools is invalid "
    "for composition-unknown baskets because no estimable item list exists yet; "
    "when a later follow-up supplies concrete listed items for that basket, it is no longer composition-unknown: "
    "use prior turn context, call estimate_nutrition before commit, and do not repeat the same composition clarification; "
    + refinement_policy.COMPOSITION_REFINEMENT_AFTER_BASIS_QUERY_SUMMARY
    + "refinement_optional, refinement_not_commit_gate, and size_clarification follow-up postures require a followup_question."
)

FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION = (
    "Current-loop nutrition evidence exists only when "
    "manager_contract_evidence_state.nutrition_evidence_present=true. If it is false and the intended final_action "
    "would be commit, nutrition-changing correction_applied, or overshoot_note, return manager_action='call_tools' with estimate_nutrition "
    "instead of manager_action='final'. Do not substitute final_action='ask_followup' or no_commit while "
    "semantic_decision.final_action_candidate is commit, correction_applied, or overshoot_note. "
    "Exception: explicit removal is correction_applied/remove_item or correction_applied/remove_meal and requires target evidence from resolve_correction_target or a structured target_attachment validated by runtime; "
    "it does not require estimate_nutrition because existing canonical item calories or versioned whole-meal removal are used for ledger recompute. If manager_contract_evidence_state.target_evidence_present=true and target_evidence_operation='remove_item' or target_evidence_operation='remove_meal', "
    "return manager_action='final' with final_action='correction_applied' and tool_calls=[]; do not call resolve_correction_target again. "
    "If evidence_posture is requires_tool, evidence_missing, or evidence_pending, or if "
    "semantic_decision.estimation_posture is pending_tool_call or tool_pending, the current response must be "
    "manager_action='call_tools' with estimate_nutrition, not manager_action='final'. "
    "If nutrition_evidence_present=true because tool_results include user_provided_kcal_evidence, finalize the "
    "kcal-only commit without estimate_nutrition and without macro or composition claims. A named-food kcal conflict includes a whole bowl or plate of a named noodle, rice, soup, or set-meal dish with a suspicious kcal; it is not user_provided_kcal_evidence: do not treat it as a kcal-only shortcut; call estimate_nutrition or ask for confirmation according to Manager judgment, and do not silently commit or overwrite the user's kcal. "
    "Exception: if your semantic decision is composition-unknown "
    "ask_followup/no_mutation, return manager_action='final' with final_action='ask_followup' and no tool_calls; "
    "set tool_calls=[] for composition-unknown ask_followup and do not estimate; manager_action='call_tools' "
    "with estimate_nutrition is invalid while composition is unknown. Once the user supplies concrete listed items after that clarification, treat the turn as "
    "listed-item follow-up evidence collection: use prior turn context, return manager_action='call_tools' with estimate_nutrition before "
    "final commit and do not repeat the same composition clarification."
)

FOUNDER_LIVE_MANAGER_FOLLOWUP_INSTRUCTION = (
    "Use followup_posture='refinement_optional', 'refinement_not_commit_gate', or 'size_clarification' only when you also provide "
    "a concrete user-facing followup_question in semantic_decision.followup_question or "
    "answer_contract.followup_question. If no concrete follow-up question is needed, use followup_posture='none' "
    "or 'closed' instead. Do not use refinement_not_commit_gate as a generic uncertainty "
    "or honesty label."
)
