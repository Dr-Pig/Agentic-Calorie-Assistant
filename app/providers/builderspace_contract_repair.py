from __future__ import annotations

from typing import Any


def contract_repair_message(parse_attempt: dict[str, Any]) -> str:
    semantic_repair = _semantic_repair_message(parse_attempt)
    if semantic_repair:
        return semantic_repair
    scoped_hint = _scoped_repair_hint(parse_attempt)
    return (
        "CONTRACT_REPAIR: Return the same manager decision using the required structured schema. "
        "Do not change user intent, target_attachment, exactness, confidence, or evidence_posture. "
        "Fix only the contract fields named by the validation error; if final_action and workflow_effect "
        "are inconsistent, update both consistently. "
        f"{scoped_hint}"
        f"Previous validation error: {parse_attempt.get('error')}"
    )


def _semantic_repair_message(parse_attempt: dict[str, Any]) -> str:
    error = str(parse_attempt.get("error") or "")
    if "listed_item_lookup requires multiple Manager-owned component items" in error:
        return (
            "CONTRACT_REPAIR: Your previous listed_item_lookup decision only supplied one component item. "
            "You, the Manager, must choose a legal route: if it is a single concrete food, use generic or exact "
            "retrieval instead of listed_item_lookup; if it is a bundle/combo whose components are not known, "
            "return manager_action='final', final_action='ask_followup', workflow_effect='ask_followup', "
            "semantic_decision.final_action_candidate='ask_followup', "
            "semantic_decision.mutation_intent_candidate='no_mutation', tool_calls=[], and ask one concise "
            "composition question. Do not let runtime infer the missing components. Previous validation error: "
            f"{parse_attempt.get('error')}"
        )
    if "ask_followup requires top-level final_action='ask_followup'" in error:
        return (
            "CONTRACT_REPAIR: Your semantic decision chose an ask-followup workflow. Keep that Manager-owned "
            "meaning and align the structured fields: manager_action='final', final_action='ask_followup', "
            "workflow_effect='ask_followup', semantic_decision.final_action_candidate='ask_followup', "
            "semantic_decision.mutation_intent_candidate='no_mutation', tool_calls=[], and include a concrete "
            "answer_contract.followup_question or semantic_decision.followup_question. Previous validation error: "
            f"{parse_attempt.get('error')}"
        )
    if "ask_followup requires workflow_effect='ask_followup'" in error:
        return (
            "CONTRACT_REPAIR: Your final action is ask_followup, so keep the Manager-owned follow-up meaning "
            "and align workflow_effect='ask_followup' at both top level and semantic_decision. Use "
            "mutation_intent_candidate='no_mutation', tool_calls=[], and include a concrete followup_question. "
            "Previous validation error: "
            f"{parse_attempt.get('error')}"
        )
    if "ambiguous correction target requires final ask_followup" not in error:
        return ""
    return (
        "CONTRACT_REPAIR: The target validator rejected the correction/removal target because multiple "
        "candidate meals remain possible. This is a semantic legality repair: ask the user to clarify the "
        "target, use manager_action='final', final_action='ask_followup', workflow_effect='ask_followup', "
        "tool_calls=[], semantic_decision.final_action_candidate='ask_followup', and "
        "semantic_decision.mutation_intent_candidate='no_mutation'. Do not preserve the rejected "
        "target_attachment as a concrete mutation target. Previous validation error: "
        f"{parse_attempt.get('error')}"
    )


def _scoped_repair_hint(parse_attempt: dict[str, Any]) -> str:
    observed = parse_attempt.get("observed_value")
    if not isinstance(observed, dict):
        return ""
    semantic_decision = observed.get("semantic_decision")
    semantic_intent = (
        str(semantic_decision.get("current_turn_intent") or "")
        if isinstance(semantic_decision, dict)
        else ""
    )
    error = str(parse_attempt.get("error") or "")
    if "listed_item_lookup requires semantic_decision.listed_items" in error:
        target_attachment = (
            semantic_decision.get("target_attachment")
            if isinstance(semantic_decision, dict)
            else None
        )
        target_operation = (
            str(target_attachment.get("operation") or "")
            if isinstance(target_attachment, dict)
            else ""
        )
        mutation_intent = (
            str(semantic_decision.get("mutation_intent_candidate") or "")
            if isinstance(semantic_decision, dict)
            else ""
        )
        final_candidate = (
            str(semantic_decision.get("final_action_candidate") or "")
            if isinstance(semantic_decision, dict)
            else ""
        )
        if (
            target_operation == "update_meal_components"
            and mutation_intent == "correction_write"
            and final_candidate == "correction_applied"
        ):
            return (
                "Your correction selected operation='update_meal_components' with "
                "retrieval_goal='listed_item_lookup'. Keep that Manager-owned correction meaning, "
                "but supply the updated component list in semantic_decision.listed_items before "
                "calling estimate_nutrition. Build that list from the active meal context you were "
                "given: remove excluded components, apply portion changes in modifier_hints or "
                "size_hint, and keep unchanged components. If the target meal or changed component "
                "is still ambiguous, change to manager_action='final', final_action='ask_followup', "
                "workflow_effect='ask_followup', semantic_decision.final_action_candidate='ask_followup', "
                "semantic_decision.mutation_intent_candidate='no_mutation', and tool_calls=[]. "
                "Runtime must not infer or rewrite the updated component list for you. "
            )
        if (
            str(observed.get("intent_type") or "") == "correct_meal"
            or semantic_intent == "correct_meal"
        ):
            return (
                "Your correct_meal decision selected retrieval_goal='listed_item_lookup' without "
                "semantic_decision.listed_items. Keep the Manager-owned correction meaning, "
                "but supply the updated component list in semantic_decision.listed_items before "
                "calling estimate_nutrition. Build that list from the active meal context you were "
                "given: remove excluded components, apply portion changes in modifier_hints or "
                "size_hint, and keep unchanged components. If the target meal or changed component "
                "is still ambiguous, change to manager_action='final', final_action='ask_followup', "
                "workflow_effect='ask_followup', semantic_decision.final_action_candidate='ask_followup', "
                "semantic_decision.mutation_intent_candidate='no_mutation', and tool_calls=[]. "
                "Runtime must not infer or rewrite the updated component list for you. "
            )
        return (
            "Your previous retrieval_goal='listed_item_lookup' decision is under-specified. You, the Manager, "
            "must make one legal semantic choice: if you already identified concrete food components, include "
            "those Manager-owned components in semantic_decision.listed_items and keep "
            "retrieval_goal='listed_item_lookup'; if you did not identify concrete "
            "components, change to manager_action='final', final_action='ask_followup', "
            "workflow_effect='ask_followup', semantic_decision.final_action_candidate='ask_followup', "
            "semantic_decision.mutation_intent_candidate='no_mutation', and tool_calls=[]. "
            "Do not let runtime infer components or estimability for you. "
        )
    if "non-empty semantic_decision.listed_items requires retrieval_goal='listed_item_lookup'" in error:
        return (
            "You already identified concrete component items in semantic_decision.listed_items; keep those "
            "Manager-owned listed items, do not discard listed items, and set "
            "retrieval_goal='listed_item_lookup'. "
        )
    if "branded_combo with manager-identified component hints" in error:
        return (
            "You identified a branded combo and also placed concrete components in modifier_hints. Move those "
            "Manager-owned component items into semantic_decision.listed_items, preserve the brand, and set "
            "retrieval_goal='listed_item_lookup'. Do not ask again for component names already supplied. "
        )
    if str(observed.get("intent_type") or "") != "body_observation" and semantic_intent != "body_observation":
        return ""
    if "final_action invalid" not in error and "call_tools cannot use" not in error:
        return ""
    return (
        "For body_observation, commit is intake-only and is not a valid body action. "
        "If calling body.record_observation, use manager_action='call_tools' and "
        "final_action='record_observation'. If confirming an already successful body.record_observation "
        "tool result, use manager_action='final', final_action='answer_only', and "
        "workflow_effect='record_weight'. "
    )
