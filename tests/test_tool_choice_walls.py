from __future__ import annotations

from app.shared.contracts.tool_choice_walls import validate_tool_choice_walls


def test_tool_choice_walls_accept_supported_tools_with_valid_ordering() -> None:
    artifact = validate_tool_choice_walls(
        requested_capability_ids=["memory", "rescue", "recommendation"],
        tool_calls=[
            {"tool_name": "memory.search", "capability_id": "memory", "arguments": {}},
            {"tool_name": "rescue.run", "capability_id": "rescue", "arguments": {}},
            {
                "tool_name": "recommendation.run",
                "capability_id": "recommendation",
                "arguments": {},
            },
        ],
        ordering_constraints=["rescue_before_recommendation"],
    )

    assert artifact["artifact_type"] == "shared_tool_choice_walls_validation"
    assert artifact["status"] == "pass"
    assert artifact["blockers"] == []


def test_tool_choice_walls_block_unrequested_capability_and_bad_order() -> None:
    artifact = validate_tool_choice_walls(
        requested_capability_ids=["memory", "recommendation"],
        tool_calls=[
            {
                "tool_name": "recommendation.run",
                "capability_id": "recommendation",
                "arguments": {},
            },
            {"tool_name": "rescue.run", "capability_id": "rescue", "arguments": {}},
        ],
        ordering_constraints=["rescue_before_recommendation"],
    )

    assert artifact["status"] == "blocked"
    assert "tool.capability_not_requested:rescue" in artifact["blockers"]
    assert "ordering_constraint_failed:rescue_before_recommendation" in artifact["blockers"]


def test_tool_choice_walls_block_unsupported_tool_and_bad_arguments() -> None:
    artifact = validate_tool_choice_walls(
        requested_capability_ids=["query"],
        tool_calls=[
            {
                "tool_name": "generic.workflow_engine.run",
                "capability_id": "query",
                "arguments": "not-a-dict",
            }
        ],
        ordering_constraints=[],
    )

    assert artifact["status"] == "blocked"
    assert "tool.unsupported:generic.workflow_engine.run" in artifact["blockers"]
    assert "tool.arguments_not_mapping:generic.workflow_engine.run" in artifact["blockers"]
