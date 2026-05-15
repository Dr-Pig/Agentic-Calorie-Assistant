from __future__ import annotations

from app.providers.builderspace_runtime_contract import manager_loop_schema
from app.runtime.agent.founder_live_manager_contract import founder_live_manager_tool_description
from app.runtime.agent.manager_system_prompt import (
    SINGLE_MANAGER_SYSTEM_PROMPT,
    SINGLE_MANAGER_SYSTEM_PROMPT_VERSION,
)


def test_self_selected_basket_blocking_clarify_policy_is_explicit_static_prompt_guidance() -> None:
    assert SINGLE_MANAGER_SYSTEM_PROMPT_VERSION == "v29"
    assert "Self-selected basket examples include" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "滷味" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "鹽酥雞" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "自助餐" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "麻辣燙" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "final_action_candidate='ask_followup'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "mutation_intent_candidate='no_mutation'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "estimation_posture='composition_unknown_basket'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "semantic_decision.followup_question" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "do not call estimate_nutrition" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "do not create a canonical commit" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "named set meal, combo, or patterned bundle" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "no approved composition anchor" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "ask one blocking composition question" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "nutrition_evidence_not_commit_eligible" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "You, the Manager, own open-world food semantics" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "it must not decide those semantics from raw user text before your pass" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "repair by choosing a legal final action" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_self_selected_basket_blocking_clarify_policy_is_tool_guidance_not_raw_text_router() -> None:
    description = founder_live_manager_tool_description()

    assert "self-selected basket" in description
    assert "unanchored patterned combo" in description
    assert "tool_calls=[]" in description
    assert "final ask_followup" in description
    assert "do not call estimate_nutrition" in description
    assert "nutrition_evidence_not_commit_eligible" in description
    assert "ask_followup/no_mutation" in description
    assert "Manager-proposed commit" in description
    assert "deterministic raw text routing" in description


def test_self_selected_basket_blocking_clarify_schema_guidance_keeps_llm_as_semantic_owner() -> None:
    schema = manager_loop_schema(
        {
            "manager_contract_profile_id": "founder_live_contract",
            "manager_loop_scope": "intake_execution",
            "manager_contract_evidence_state": {
                "nutrition_evidence_present": False,
            },
        }
    )

    action_description = schema["properties"]["manager_action"]["description"]
    posture_description = schema["properties"]["semantic_decision"]["properties"]["estimation_posture"]["description"]
    assert "composition-unknown baskets or unanchored patterned combos are not tool evidence missing" in action_description
    assert "unanchored patterned combos are not tool evidence missing" in action_description
    assert "composition_unknown_basket or unanchored_patterned_combo is not pending_tool_call" in posture_description
    assert "LLM semantic decision" in posture_description


def test_explicit_listed_components_are_not_blocking_combo_prompt_guidance() -> None:
    assert "explicitly lists concrete food components" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "semantic_decision.listed_items" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "retrieval_goal='listed_item_lookup'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "ask for portions as optional refinement" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "not a composition-unknown basket" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_pending_followup_commit_requires_manager_owned_target_attachment() -> None:
    assert SINGLE_MANAGER_SYSTEM_PROMPT_VERSION == "v29"
    assert "target_resolution_source='pending_followup_state'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "operation='attach_to_pending_followup'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "Do not return target_attachment={}" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_explicit_listed_components_are_not_blocking_combo_tool_guidance() -> None:
    description = founder_live_manager_tool_description()

    assert "explicitly lists concrete food components" in description
    assert "include them in semantic_decision.listed_items" in description
    assert "retrieval_goal='listed_item_lookup'" in description
    assert "do not classify that turn as composition-unknown" in description


def test_explicit_listed_components_schema_guidance_keeps_manager_as_list_owner() -> None:
    schema = manager_loop_schema(
        {
            "manager_contract_profile_id": "founder_live_contract",
            "manager_loop_scope": "intake_execution",
            "manager_contract_evidence_state": {
                "nutrition_evidence_present": False,
            },
        }
    )

    listed_items_description = schema["properties"]["semantic_decision"]["properties"]["listed_items"][
        "description"
    ]
    retrieval_goal_description = schema["properties"]["semantic_decision"]["properties"]["retrieval_goal"][
        "description"
    ]
    assert "Manager-owned list" in listed_items_description
    assert "raw-text deterministic parser" in listed_items_description
    assert "explicit listed components" in retrieval_goal_description
    assert "listed_item_lookup" in retrieval_goal_description


def test_pending_followup_target_attachment_schema_guidance_keeps_manager_as_attach_owner() -> None:
    schema = manager_loop_schema(
        {
            "manager_contract_profile_id": "founder_live_contract",
            "manager_loop_scope": "intake_execution",
            "manager_contract_evidence_state": {
                "nutrition_evidence_present": True,
            },
        }
    )

    top_level_description = schema["properties"]["target_attachment"]["description"]
    semantic_description = schema["properties"]["semantic_decision"]["properties"]["target_attachment"][
        "description"
    ]
    assert "pending_followup_state" in top_level_description
    assert "attach_to_pending_followup" in top_level_description
    assert "Manager-owned attach decision" in semantic_description
    assert "must not be empty" in semantic_description
