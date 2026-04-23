from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# ==============================================================================
# Types & Constants
# ==============================================================================

@dataclass(frozen=True)
class PrimaryManagerDecision:
    intent_type: str
    workflow_effect: str
    response_summary: str
    pending_followup: str | None = None
    tool_calls: tuple[str, ...] = field(default_factory=tuple)
    llm_used: bool = False
    trace: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Bundle2ManagerDecision1:
    intent_type: str
    clarify_posture: str
    tool_plan: tuple[str, ...]
    target_attachment: dict[str, Any]
    pending_followup_resolution_mode: str | None = None
    workflow_effect: str = "none"
    llm_used: bool = False
    trace: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Bundle2ManagerDecision2:
    final_action: str
    workflow_effect: str
    llm_used: bool = False
    trace: dict[str, Any] = field(default_factory=dict)

_BUDGET_QUERY_TOKENS = (
    "剩", "還剩", "還能吃多少", "還剩多少", "剩多少", 
    "剩餘熱量", "剩下多少熱量", "目標是多少", "每日目標", 
    "熱量目標", "remaining", "left", "budget", "目標", 
    "熱量", "kcal", "calorie",
)

_BUNDLE2_CORRECTION_TOKENS = (
    "改成", "改為", "不是", "更正", "刪掉",
    "拿掉", "remove", "change", "replace", "without",
)

_BUNDLE2_STRUCTURED_DRINK_TOKENS = (
    "珍珠奶茶", "奶茶", "bubble tea", "milk tea", "latte",
)

_BUNDLE2_CLARIFY_FIRST_TOKENS = (
    "家常菜", "滷味", "poke", "便當菜",
)

# ==============================================================================
# Prompts
# ==============================================================================

BUNDLE1_SYSTEM_PROMPT = (
    "You are the Bundle 1 primary manager for a chat-first calorie assistant.\n"
    "Choose exactly one intent from the allowed_intents list.\n"
    "Return strict JSON with keys: intent_type, workflow_effect, response_summary, pending_followup, tool_calls.\n"
    "Rules:\n"
    "- If onboarding is not ready and the user is asking about remaining budget or today's target, choose onboarding_required.\n"
    "- If onboarding is ready and the user is asking how much budget remains or today's target, choose answer_remaining_budget.\n"
    "- If the user is asking what was just changed or updated about the latest meal, choose log_meal so the Bundle 2 recap lane can answer.\n"
    "- Otherwise, for Bundle 1, treat the turn as log_meal, even if onboarding is missing.\n"
    "- Do not invent hidden intent state.\n"
    "- Do not mutate state in this step.\n"
)

BUNDLE2_STEP1_SYSTEM_PROMPT = (
    "You are the Bundle 2 primary manager for a chat-first calorie assistant.\n"
    "Return strict JSON with keys: intent_type, clarify_posture, tool_plan, target_attachment, pending_followup_resolution_mode, workflow_effect.\n"
    "Allowed clarify_posture values: estimate_with_followup, clarify_before_estimate, direct_estimate, item_correction, overshoot_note.\n"
    "Rules:\n"
    "- Pearl milk tea or standardized drink cases usually map to estimate_with_followup.\n"
    "- Home-cooked mixed dishes, luwei, or poke cases usually map to clarify_before_estimate.\n"
    "- Explicit correction requests map to item_correction.\n"
    "- Do not mutate state.\n"
)

BUNDLE2_STEP2_SYSTEM_PROMPT = (
    "You are the Bundle 2 primary manager after tool execution.\n"
    "Return strict JSON with keys: final_action, workflow_effect.\n"
    "Allowed final_action values: commit, ask_followup, correction_applied, overshoot_note, no_commit.\n"
    "Generalized Principles:\n"
    "- If a valid estimate exists (estimated_kcal > 0) and the user intent was to correct or supplement information (Modification/item_correction), choose 'correction_applied' or 'commit' to finish the update.\n"
    "- If the user provides specific numerical corrections (e.g., \"Change it to 500 kcal\" or \"It was 10 pieces\"), prioritize `commit` or `correction_applied` immediately.\n"
    "- For `Modification` intents originating from Step 1, favor `correction_applied` over further clarification if the primary correction has been provided.\n"
    "- Only use `ask_followup` if the estimation depends on a critical missing variable that the user has not yet addressed.\n"
    "- When `overshoot_note` is needed, ensure it is combined with the commitment of the meal.\n"
    "- Favor 'commit' over 'ask_followup' if the tool provided a specific caloric value, even if minor cooking details are missing, unless the uncertainty is extreme.\n"
    "- Use 'ask_followup' only if core information (like the main food category or a completely missing portion) makes a meaningful estimate impossible.\n"
    "- If budget comparison predicts negative remaining kcal, choose 'overshoot_note'.\n"
    "- RELEASE LLM CAPACITY: Trust the tool outputs. Your goal is to help the user log their meal efficiently. Avoid excessive clarification loops.\n"
)


# ==============================================================================
# Helpers
# ==============================================================================

def looks_like_correction(text: str) -> bool:
    normalized = text.strip().lower()
    return any(token in normalized for token in _BUNDLE2_CORRECTION_TOKENS) or any(
        token in normalized for token in ("沒喝", "没喝", "沒吃", "没吃", "沒", "没")
    )

def looks_like_budget_query(text: str) -> bool:
    normalized = text.strip().lower()
    return any(token in normalized for token in _BUDGET_QUERY_TOKENS)


def looks_like_recent_change_query(text: str) -> bool:
    normalized = text.strip().lower()
    tokens = (
        "改了什麼",
        "改了甚麼",
        "幫我改了",
        "剛剛改",
        "updated",
        "what changed",
        "what was changed",
        "what did you change",
    )
    return any(token in normalized for token in tokens)

def fallback_decision(
    *,
    raw_user_input: str,
    onboarding_payload: dict[str, Any] | None,
    onboarding_ready: bool,
) -> PrimaryManagerDecision:
    if onboarding_payload is not None:
        return PrimaryManagerDecision(
            intent_type="complete_onboarding",
            workflow_effect="seed_active_body_plan_and_day_budget",
            response_summary="Complete onboarding and seed the active body plan plus current-day budget.",
            tool_calls=("read_body_plan", "read_day_budget"),
            llm_used=False,
            trace={"decision_source": "fallback_structured_onboarding"},
        )
    if looks_like_correction(raw_user_input):
        return PrimaryManagerDecision(
            intent_type="log_meal",
            workflow_effect="append_meal_and_refresh_budget",
            response_summary="Treat explicit correction language as intake/correction rather than a budget query.",
            tool_calls=("estimate_nutrition", "persist_meal_log", "read_day_budget"),
            llm_used=False,
            trace={"decision_source": "fallback_item_correction_guard"},
        )
    if looks_like_recent_change_query(raw_user_input):
        return PrimaryManagerDecision(
            intent_type="log_meal",
            workflow_effect="recent_change_summary",
            response_summary="Route recent change recap queries through the Bundle 2 lane instead of the generic budget answer lane.",
            tool_calls=("read_day_budget",),
            llm_used=False,
            trace={"decision_source": "fallback_recent_change_guard"},
        )
    if not onboarding_ready and looks_like_budget_query(raw_user_input):
        return PrimaryManagerDecision(
            intent_type="onboarding_required",
            workflow_effect="none",
            response_summary="Ask the user to finish onboarding before budget questions can be answered.",
            tool_calls=("read_body_plan",),
            llm_used=False,
            trace={"decision_source": "fallback_onboarding_gate"},
        )
    if onboarding_ready and looks_like_budget_query(raw_user_input):
        return PrimaryManagerDecision(
            intent_type="answer_remaining_budget",
            workflow_effect="none",
            response_summary="Answer the remaining budget question from deterministic read surfaces.",
            tool_calls=("read_day_budget", "read_body_plan"),
            llm_used=False,
            trace={"decision_source": "fallback_budget_query"},
        )
    return PrimaryManagerDecision(
        intent_type="log_meal",
        workflow_effect="append_meal_and_refresh_budget",
        response_summary="Estimate the described intake, persist it, and refresh the current budget surfaces.",
        tool_calls=("estimate_nutrition", "persist_meal_log", "read_day_budget"),
        llm_used=False,
        trace={"decision_source": "fallback_default_log_meal"},
    )

def fallback_bundle2_step1(
    *,
    raw_user_input: str,
    resolved_state: Any,
) -> Bundle2ManagerDecision1:
    normalized = (raw_user_input or "").strip().lower()
    pending_followup = ((resolved_state.injected_context or {}).get("PENDING_FOLLOWUP") or {})
    target_attachment = ((resolved_state.injected_context or {}).get("TARGET_MEAL_REFERENCE") or {})
    if looks_like_correction(raw_user_input):
        return Bundle2ManagerDecision1(
            intent_type="log_meal",
            clarify_posture="item_correction",
            tool_plan=("resolve_correction_target", "estimate_nutrition", "compare_against_budget"),
            target_attachment=target_attachment,
            workflow_effect="correction_candidate",
            trace={"decision_source": "bundle2_fallback_item_correction"},
        )
    if bool(pending_followup.get("is_open")):
        return Bundle2ManagerDecision1(
            intent_type="log_meal",
            clarify_posture="estimate_with_followup",
            tool_plan=("estimate_nutrition", "compare_against_budget"),
            target_attachment=target_attachment,
            pending_followup_resolution_mode="resolve_existing_followup",
            workflow_effect="followup_resolution",
            trace={"decision_source": "bundle2_fallback_pending_followup"},
        )
    if any(token in normalized for token in _BUNDLE2_CLARIFY_FIRST_TOKENS):
        return Bundle2ManagerDecision1(
            intent_type="log_meal",
            clarify_posture="clarify_before_estimate",
            tool_plan=("estimate_nutrition", "compare_against_budget"),
            target_attachment=target_attachment,
            workflow_effect="clarify_before_estimate",
            trace={"decision_source": "bundle2_fallback_clarify_before_estimate"},
        )
    if any(token in normalized for token in _BUNDLE2_STRUCTURED_DRINK_TOKENS):
        return Bundle2ManagerDecision1(
            intent_type="log_meal",
            clarify_posture="estimate_with_followup",
            tool_plan=("estimate_nutrition", "compare_against_budget"),
            target_attachment=target_attachment,
            workflow_effect="estimate_with_followup",
            trace={"decision_source": "bundle2_fallback_estimate_with_followup"},
        )
    return Bundle2ManagerDecision1(
        intent_type="log_meal",
        clarify_posture="direct_estimate",
        tool_plan=("estimate_nutrition", "compare_against_budget"),
        target_attachment=target_attachment,
        workflow_effect="direct_estimate",
        trace={"decision_source": "bundle2_fallback_direct_estimate"},
    )

def fallback_bundle2_step2(*, tool_outputs: dict[str, Any], step1: Bundle2ManagerDecision1) -> Bundle2ManagerDecision2:
    error_type = str(tool_outputs.get("error_type") or "")
    if error_type == "hard":
        return Bundle2ManagerDecision2(
            final_action="no_commit",
            workflow_effect="safe_failure",
            trace={"decision_source": "bundle2_step2_hard_failure"},
        )
    nutrition_payload = tool_outputs.get("nutrition_payload") or {}
    route_target = str(nutrition_payload.get("route_target") or "")
    action_taken = str(nutrition_payload.get("action_taken") or "")
    followup_question = str(nutrition_payload.get("followup_question") or "").strip()
    unresolved = nutrition_payload.get("unresolved_info") or []
    budget_summary = tool_outputs.get("budget_summary") or {}
    overshoot_detected = bool(budget_summary.get("overshoot_detected"))
    estimated_kcal = int(nutrition_payload.get("estimated_kcal") or 0)
    if route_target == "clarify_user_private" or action_taken == "clarify_before_estimate":
        return Bundle2ManagerDecision2(
            final_action="ask_followup",
            workflow_effect="clarify_before_estimate",
            trace={"decision_source": "bundle2_step2_clarify_before_estimate"},
        )
    if step1.clarify_posture == "estimate_with_followup":
        if step1.pending_followup_resolution_mode == "resolve_existing_followup":
            if not followup_question and not unresolved and estimated_kcal > 0:
                if overshoot_detected:
                    return Bundle2ManagerDecision2(
                        final_action="overshoot_note",
                        workflow_effect="overshoot_note",
                        trace={"decision_source": "bundle2_step2_followup_resolved_overshoot"},
                    )
                return Bundle2ManagerDecision2(
                    final_action="commit",
                    workflow_effect="commit",
                    trace={"decision_source": "bundle2_step2_followup_resolved_commit"},
                )
        # RELEASE: If we have an estimate on the first turn and no blocking question, allow commit
        if not followup_question and estimated_kcal > 0:
            if overshoot_detected:
                return Bundle2ManagerDecision2(
                    final_action="overshoot_note",
                    workflow_effect="overshoot_note",
                    trace={"decision_source": "bundle2_step2_estimate_with_followup_commit_overshoot"},
                )
            return Bundle2ManagerDecision2(
                final_action="commit",
                workflow_effect="commit",
                trace={"decision_source": "bundle2_step2_estimate_with_followup_commit"},
            )
        return Bundle2ManagerDecision2(
            final_action="ask_followup",
            workflow_effect="estimate_with_followup",
            trace={"decision_source": "bundle2_step2_estimate_with_followup_fallback_ask"},
        )
    if followup_question or unresolved:
        return Bundle2ManagerDecision2(
            final_action="ask_followup",
            workflow_effect="estimate_with_followup",
            trace={"decision_source": "bundle2_step2_estimate_with_followup"},
        )
    if step1.clarify_posture == "item_correction":
        return Bundle2ManagerDecision2(
            final_action="correction_applied",
            workflow_effect="correction_applied",
            trace={"decision_source": "bundle2_step2_correction_applied"},
        )
    if overshoot_detected:
        return Bundle2ManagerDecision2(
            final_action="overshoot_note",
            workflow_effect="overshoot_note",
            trace={"decision_source": "bundle2_step2_overshoot_note"},
        )
    return Bundle2ManagerDecision2(
        final_action="commit",
        workflow_effect="commit",
        trace={"decision_source": "bundle2_step2_commit"},
    )


def normalize_bundle2_step1(
    *,
    decision: Bundle2ManagerDecision1,
    raw_user_input: str,
    resolved_state: Any,
) -> Bundle2ManagerDecision1:
    pending_followup = ((resolved_state.injected_context or {}).get("PENDING_FOLLOWUP") or {})
    target_attachment = ((resolved_state.injected_context or {}).get("TARGET_MEAL_REFERENCE") or {})
    if bool(pending_followup.get("is_open")) and not looks_like_correction(raw_user_input):
        return Bundle2ManagerDecision1(
            intent_type=decision.intent_type,
            clarify_posture="estimate_with_followup",
            tool_plan=decision.tool_plan or ("estimate_nutrition", "compare_against_budget"),
            target_attachment=target_attachment if target_attachment else decision.target_attachment,
            pending_followup_resolution_mode="resolve_existing_followup",
            workflow_effect="followup_resolution",
            llm_used=decision.llm_used,
            trace={**decision.trace, "normalized_by": "pending_followup_resolution_guard"},
        )
    if not decision.target_attachment and target_attachment:
        return Bundle2ManagerDecision1(
            intent_type=decision.intent_type,
            clarify_posture=decision.clarify_posture,
            tool_plan=decision.tool_plan,
            target_attachment=target_attachment,
            pending_followup_resolution_mode=decision.pending_followup_resolution_mode,
            workflow_effect=decision.workflow_effect,
            llm_used=decision.llm_used,
            trace={**decision.trace, "normalized_by": "target_attachment_default_guard"},
        )
    return decision
