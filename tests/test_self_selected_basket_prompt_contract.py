from __future__ import annotations

from app.providers.builderspace_runtime_contract import manager_loop_schema
from app.runtime.agent.founder_live_manager_contract import founder_live_manager_tool_description
from app.runtime.agent.manager_system_prompt import (
    SINGLE_MANAGER_SYSTEM_PROMPT,
    SINGLE_MANAGER_SYSTEM_PROMPT_VERSION,
)


def test_self_selected_basket_blocking_clarify_policy_is_explicit_static_prompt_guidance() -> None:
    assert SINGLE_MANAGER_SYSTEM_PROMPT_VERSION == "v15"
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


def test_self_selected_basket_blocking_clarify_policy_is_tool_guidance_not_raw_text_router() -> None:
    description = founder_live_manager_tool_description()

    assert "self-selected basket" in description
    assert "tool_calls=[]" in description
    assert "final ask_followup" in description
    assert "do not call estimate_nutrition" in description
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
    assert "composition-unknown baskets are not tool evidence missing" in action_description
    assert "composition_unknown_basket is not pending_tool_call" in posture_description
    assert "LLM semantic decision" in posture_description
