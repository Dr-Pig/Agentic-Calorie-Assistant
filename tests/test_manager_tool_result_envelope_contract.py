from __future__ import annotations

from app.shared.contracts.manager_tool_result_envelope import (
    build_manager_tool_result_envelope_contract,
    normalize_manager_tool_result,
)


def test_manager_tool_result_envelope_contract_declares_shared_runtime_targets() -> None:
    artifact = build_manager_tool_result_envelope_contract()

    assert artifact["artifact_type"] == "shared_manager_tool_result_envelope_contract"
    assert artifact["status"] == "pass"
    assert artifact["allowed_source_runtimes"] == [
        "current_shell",
        "advanced_product_lab",
    ]
    assert artifact["derived_current_shell_read_model_refs_allowed"] is True


def test_normalize_manager_tool_result_handles_current_shell_read_model_tool() -> None:
    artifact = normalize_manager_tool_result(
        {
            "tool_name": "budget.get_remaining_calories",
            "confidence": "high",
            "evidence": {"remaining_budget_contract": {"remaining_kcal": 300}},
            "provenance": {"canonical_tool_name": "budget.get_remaining_calories"},
        }
    )

    assert artifact["status"] == "pass"
    assert artifact["source_runtime"] == "current_shell"
    assert artifact["tool_name"] == "budget.get_remaining_calories"
    assert artifact["capability_id"] == "query"
    assert artifact["source_refs"] == ["read_model:current_budget_view"]


def test_normalize_manager_tool_result_handles_advanced_lab_memory_wrapper() -> None:
    artifact = normalize_manager_tool_result(
        {
            "artifact_type": "advanced_product_lab_manager_tool_result",
            "status": "pass",
            "tool_name": "memory.search",
            "returned_to_manager": True,
            "result_artifact": {
                "artifact_type": "advanced_product_lab_memory_tool_call_artifact",
                "status": "pass",
                "context_pack": {
                    "selected_record_ids": ["memory-1"],
                    "source_refs": ["memory_record:memory-1", "message:turn-1"],
                },
                "raw_transcript_included": False,
            },
            "blockers": [],
        }
    )

    assert artifact["status"] == "pass"
    assert artifact["source_runtime"] == "advanced_product_lab"
    assert artifact["capability_id"] == "memory"
    assert artifact["source_refs"] == ["memory_record:memory-1", "message:turn-1"]
    assert artifact["payload_summary"]["selected_record_ids"] == ["memory-1"]


def test_normalize_manager_tool_result_propagates_blocked_advanced_lab_wrapper() -> None:
    artifact = normalize_manager_tool_result(
        {
            "artifact_type": "advanced_product_lab_manager_tool_result",
            "status": "blocked",
            "tool_name": "generic.workflow_engine.run",
            "returned_to_manager": True,
            "result_artifact": {},
            "blockers": ["tool.unsupported:generic.workflow_engine.run"],
        }
    )

    assert artifact["status"] == "blocked"
    assert artifact["capability_id"] == "unknown"
    assert "tool.unsupported:generic.workflow_engine.run" in artifact["blockers"]
    assert "capability_id.unmapped:generic.workflow_engine.run" in artifact["blockers"]


def test_normalize_manager_tool_result_marks_current_shell_failure_family_as_blocker() -> None:
    artifact = normalize_manager_tool_result(
        {
            "tool_name": "estimate_nutrition",
            "failure_family": "tool_execution_error",
            "evidence": {},
            "provenance": {},
        }
    )

    assert artifact["status"] == "blocked"
    assert artifact["capability_id"] == "intake"
    assert artifact["blockers"] == ["tool.failure_family:tool_execution_error"]
