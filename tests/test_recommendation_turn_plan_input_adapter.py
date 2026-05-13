from __future__ import annotations

import json

import yaml

from app.recommendation.application.turn_plan_input_adapter import (
    build_recommendation_planning_input,
)
from app.shared.contracts.manager_turn_plan import (
    CapabilityRequest,
    ManagerTurnPlan,
    ToolCallCandidate,
)


def test_recommendation_turn_plan_adapter_projects_scoped_manager_input() -> None:
    artifact = build_recommendation_planning_input(
        manager_turn_plan=_manager_turn_plan(),
        tool_arguments={
            "scope_keys": {
                "user_id": "user-1",
                "workspace_id": "ws-1",
                "project_id": "project-1",
                "surface": "chat",
            },
            "memory_context_call_id": "memory-search-1",
            "query_call_id": "query-1",
        },
        memory_context_pack={
            "artifact_type": "advanced_product_lab_memory_context_pack",
            "selected_record_ids": ["golden-bento-1"],
            "entries": [
                {
                    "record_id": "golden-bento-1",
                    "memory_type": "golden_order",
                    "summary": "Reliable FamilyMart bento.",
                }
            ],
            "negative_preference_blockers": ["spicy"],
        },
        rescue_context_pack={
            "artifact_type": "advanced_product_lab_rescue_runtime_artifact",
            "proposal_presented_to_lab": True,
        },
    )

    assert artifact["artifact_type"] == "recommendation_turn_plan_input_adapter"
    assert artifact["status"] == "pass"
    assert artifact["manager_turn_plan_used"] is True
    assert artifact["tool_argument_validation"]["status"] == "pass"
    assert artifact["planning_input"]["user_goal"] == "pre_meal_planning_guidance"
    assert artifact["planning_input"]["capability_request"] == {
        "capability_id": "recommendation",
        "request_mode": "required",
        "priority": 2,
    }
    assert artifact["planning_input"]["context_call_refs"] == {
        "memory_context_call_id": "memory-search-1",
        "query_call_id": "query-1",
    }
    assert artifact["planning_input"]["memory_summary"] == {
        "selected_record_ids": ["golden-bento-1"],
        "negative_preference_blockers": ["spicy"],
        "entry_summaries": [
            {
                "record_id": "golden-bento-1",
                "memory_type": "golden_order",
                "summary": "Reliable FamilyMart bento.",
            }
        ],
    }
    assert artifact["planning_input"]["rescue_summary"] == {
        "rescue_context_present": True,
        "proposal_presented_to_lab": True,
    }
    assert artifact["planning_input"]["raw_user_text_semantic_inference_performed"] is False
    assert artifact["planning_input"]["mainline_activation_enabled"] is False
    assert "raw_user_input" not in json.dumps(artifact)
    assert artifact["blockers"] == []


def test_recommendation_turn_plan_adapter_blocks_raw_fields_and_missing_request() -> None:
    plan = _manager_turn_plan(request_recommendation=False)

    artifact = build_recommendation_planning_input(
        manager_turn_plan=plan,
        tool_arguments={
            "scope_keys": {
                "user_id": "user-1",
                "workspace_id": "ws-1",
                "project_id": "project-1",
                "surface": "chat",
            },
            "raw_user_input": "recommend dinner",
        },
        memory_context_pack={"raw_transcript": [{"role": "user", "content": "leak"}]},
    )

    assert artifact["status"] == "blocked"
    assert artifact["planning_input"] == {}
    assert artifact["blockers"] == [
        "tool_arguments.argument.raw_user_input_forbidden",
        "manager_turn_plan.recommendation_not_requested",
        "context.memory_context_pack.raw_transcript_forbidden",
    ]


def test_recommendation_train_records_pr3_completion_and_next_active_slice() -> None:
    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 21
    assert plan["last_completed_pr_number"] >= 3
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 4
    assert {
        "pr_number": 3,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_turn_plan_input_adapter_completed_locally",
    } in plan["last_merge_evidence"]["completed_prs"]


def _manager_turn_plan(*, request_recommendation: bool = True) -> ManagerTurnPlan:
    capabilities = [
        CapabilityRequest(capability_id="memory", request_mode="required", priority=1)
    ]
    tool_calls = [ToolCallCandidate(tool_name="memory.search", capability_id="memory")]
    if request_recommendation:
        capabilities.append(
            CapabilityRequest(
                capability_id="recommendation",
                request_mode="required",
                priority=2,
            )
        )
        tool_calls.append(
            ToolCallCandidate(
                tool_name="recommendation.run",
                capability_id="recommendation",
                requires_prior_call_ids=["memory-search-1"],
            )
        )
    return ManagerTurnPlan(
        primary_workflow="pre_meal_planning_guidance",
        secondary_intents=["query_budget"],
        requested_capabilities=capabilities,
        candidate_tool_calls=tool_calls,
        ordering_constraints=["memory_before_recommendation"],
        mutation_posture="proposal_only",
        clarification_posture="none",
        response_obligations=["chat_first_surface_only"],
        omission_candidates=[],
        scope_keys={
            "user_id": "user-1",
            "workspace_id": "ws-1",
            "project_id": "project-1",
            "surface": "chat",
        },
    )
