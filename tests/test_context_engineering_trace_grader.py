from __future__ import annotations

from app.advanced_shadow_lab.context_engineering_trace_grader import (
    grade_context_engineering_trace,
)


def test_context_engineering_trace_grader_accepts_visible_omission_and_block_boundaries() -> None:
    grade = grade_context_engineering_trace(
        {
            "capabilities_considered": ["intake", "rescue", "recommendation"],
            "capabilities_invoked": ["intake", "rescue"],
            "capabilities_omitted": ["proactive"],
            "blocked_tools": ["proactive.run"],
            "response_claim_boundary": ["must_not_claim_committed_when_only_proposed"],
        }
    )

    assert grade["artifact_type"] == "advanced_product_lab_context_engineering_trace_grade"
    assert grade["status"] == "pass"
    assert grade["blockers"] == []


def test_context_engineering_trace_grader_blocks_hidden_omission_and_claim_boundaries() -> None:
    grade = grade_context_engineering_trace(
        {
            "capabilities_considered": ["query", "memory"],
            "capabilities_invoked": ["query"],
        }
    )

    assert grade["status"] == "blocked"
    assert "capabilities_omitted_visible" in grade["blockers"]
    assert "blocked_tools_visible" in grade["blockers"]
    assert "response_claim_boundary_visible" in grade["blockers"]
