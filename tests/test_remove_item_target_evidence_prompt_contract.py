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
    assert SINGLE_MANAGER_SYSTEM_PROMPT_VERSION == "v23"
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


def test_remove_item_target_evidence_reuse_is_tool_schema_policy() -> None:
    description = founder_live_manager_tool_description()
    assert "target_evidence_present is true" in description
    assert "target_evidence_operation remove_item" in description
    assert "do not call resolve_correction_target again" in description
    assert "deterministic raw text routing" in description


def test_remove_item_target_evidence_reuse_is_evidence_instruction_policy() -> None:
    assert "manager_contract_evidence_state.target_evidence_present=true" in FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION
    assert "target_evidence_operation='remove_item'" in FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION
    assert "tool_calls=[]" in FOUNDER_LIVE_MANAGER_EVIDENCE_INSTRUCTION


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
