from __future__ import annotations

from app.providers.builderspace_runtime_contract import manager_loop_schema
from app.runtime.agent.founder_live_manager_contract import (
    FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION,
    founder_live_manager_tool_description,
)
from app.runtime.agent.manager_system_prompt import (
    SINGLE_MANAGER_SYSTEM_PROMPT,
    SINGLE_MANAGER_SYSTEM_PROMPT_VERSION,
)


def test_remove_item_target_evidence_reuse_is_static_prompt_policy() -> None:
    assert SINGLE_MANAGER_SYSTEM_PROMPT_VERSION == "v33"
    assert "target_evidence_present=true" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "target_evidence_operation='remove_item'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "do not call resolve_correction_target again" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "final_action='correction_applied'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "nutrition evidence is present" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "workflow_effect='route_to_intake'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "final_action='no_commit'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "final_action_candidate must be the intended intake action" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "not route_to_intake or no_commit" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "explicit item removal" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "operation='remove_item'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "estimation_posture='target_evidence_needed'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "not nutrition pending_tool_call" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_whole_meal_removal_is_static_prompt_policy_without_deterministic_semantics() -> None:
    assert SINGLE_MANAGER_SYSTEM_PROMPT_VERSION == "v33"
    assert "operation='remove_meal'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "whole meal, meal entry, or named meal slot deletion" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "Manager-selected meal_thread_id" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "do not let a stale pending follow-up override the explicit current-turn target" in (
        SINGLE_MANAGER_SYSTEM_PROMPT
    )
    assert "runtime validates that selected thread id against context candidates" in (
        SINGLE_MANAGER_SYSTEM_PROMPT
    )
    assert "must not infer remove_meal from raw text" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "Do not default to the active/latest meal_thread_id" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "multiple meal_thread candidates" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "current turn does not uniquely identify one target" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "target clarification must use final_action='ask_followup'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "workflow_effect='ask_followup'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "Do not expose meal_thread_id" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_remove_item_target_evidence_reuse_is_tool_schema_policy() -> None:
    description = founder_live_manager_tool_description()
    assert "target_evidence_present is true" in description
    assert "target_evidence_operation remove_item" in description
    assert "do not call resolve_correction_target again" in description
    assert "deterministic raw text routing" in description


def test_whole_meal_removal_is_tool_schema_policy() -> None:
    description = founder_live_manager_tool_description()

    assert "target_evidence_operation remove_meal" in description
    assert "versioned whole-meal removal" in description
    assert "Manager-selected meal_thread_id" in description
    assert "deterministic raw text routing" in description


def test_remove_item_target_evidence_reuse_is_evidence_instruction_policy() -> None:
    assert "manager_contract_evidence_state.target_evidence_present=true" in FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION
    assert "target_evidence_operation='remove_item'" in FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION
    assert "tool_calls=[]" in FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION


def test_whole_meal_removal_is_evidence_instruction_policy() -> None:
    assert "target_evidence_operation='remove_meal'" in FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION
    assert "versioned whole-meal removal" in FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION
    assert "does not require estimate_nutrition" in FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION


def test_remove_item_target_evidence_reuse_is_schema_guidance() -> None:
    schema = manager_loop_schema(
        {
            "manager_contract_profile_id": "founder_live_contract",
            "manager_loop_scope": "intake_execution",
            "manager_contract_evidence_state": {
                "target_evidence_present": True,
                "target_evidence_operation": "remove_item",
            },
        }
    )

    assert "do not call resolve_correction_target again" in schema["properties"]["manager_action"]["description"]
    assert "do not call it again" in schema["properties"]["tool_calls"]["description"]


def test_evidence_present_canonical_write_commit_is_schema_guidance() -> None:
    schema = manager_loop_schema(
        {
            "manager_contract_profile_id": "founder_live_contract",
            "manager_loop_scope": "intake_execution",
            "manager_contract_evidence_state": {
                "nutrition_evidence_present": True,
            },
        }
    )

    description = schema["properties"]["final_action"]["description"]
    workflow_description = schema["properties"]["workflow_effect"]["description"]
    assert "final_action_candidate is commit" in description
    assert "mutation_intent_candidate canonical_write" in description
    assert "use commit" in description
    assert "do not use no_commit as a confirmation substitute" in description
    assert "route_to_intake is only an entry-scope handoff" in workflow_description
    assert "intake_execution final mapping must not remain route_to_intake" in workflow_description
    no_commit_write_guard = [
        item
        for item in schema["allOf"]
        if isinstance(item, dict)
        and isinstance(item.get("not"), dict)
        and item["not"].get("properties", {}).get("final_action") == {"const": "no_commit"}
    ]
    assert no_commit_write_guard
    semantic_guard = no_commit_write_guard[0]["not"]["properties"]["semantic_decision"]
    assert semantic_guard["properties"]["mutation_intent_candidate"]["enum"] == [
        "canonical_write",
        "correction_write",
    ]
    assert "no_commit" not in schema["properties"]["final_action"]["enum"]
    assert "route_to_intake" not in schema["properties"]["workflow_effect"]["enum"]
    assert "Evidence-present intake final mapping" in schema["properties"]["workflow_effect"]["description"]
