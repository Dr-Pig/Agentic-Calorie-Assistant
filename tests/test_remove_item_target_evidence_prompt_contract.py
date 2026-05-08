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
    assert SINGLE_MANAGER_SYSTEM_PROMPT_VERSION == "v10"
    assert "target_evidence_present=true" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "target_evidence_operation='remove_item'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "do not call resolve_correction_target again" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "final_action='correction_applied'" in SINGLE_MANAGER_SYSTEM_PROMPT


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
