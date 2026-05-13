from __future__ import annotations

import yaml

from app.advanced_shadow_lab.product_lab_manager_tool_contract import (
    build_product_lab_manager_tool_registry,
)
from app.shared.contracts.recommendation_tool_arguments import (
    build_recommendation_tool_argument_contract,
    validate_recommendation_tool_arguments,
)


def test_recommendation_tool_argument_contract_requires_scope_and_call_refs() -> None:
    contract = build_recommendation_tool_argument_contract()

    assert contract["artifact_type"] == "shared_recommendation_tool_argument_contract"
    assert contract["tool_name"] == "recommendation.run"
    assert contract["required_scope_keys"] == [
        "user_id",
        "workspace_id",
        "project_id",
        "surface",
    ]
    assert contract["allowed_call_ref_fields"] == [
        "memory_context_call_id",
        "query_call_id",
        "rescue_context_call_id",
        "reusable_meal_call_id",
    ]
    assert contract["forbidden_argument_fields"] == [
        "raw_user_input",
        "raw_transcript",
        "messages",
        "session_history",
        "prompt",
        "manager_context_packet",
    ]
    assert contract["raw_transcript_bypass_allowed"] is False
    assert contract["blockers"] == []


def test_recommendation_tool_argument_validation_accepts_scoped_call_refs() -> None:
    artifact = validate_recommendation_tool_arguments(
        {
            "scope_keys": {
                "user_id": "user-1",
                "workspace_id": "ws-1",
                "project_id": "project-1",
                "surface": "chat",
            },
            "memory_context_call_id": "memory-search-1",
            "query_call_id": "query-1",
        }
    )

    assert artifact["status"] == "pass"
    assert artifact["normalized_scope_keys"] == {
        "user_id": "user-1",
        "workspace_id": "ws-1",
        "project_id": "project-1",
        "surface": "chat",
    }
    assert artifact["context_call_refs"] == {
        "memory_context_call_id": "memory-search-1",
        "query_call_id": "query-1",
    }
    assert artifact["raw_transcript_bypass_allowed"] is False
    assert artifact["blockers"] == []


def test_recommendation_tool_argument_validation_blocks_missing_scope_and_raw_prompt() -> None:
    artifact = validate_recommendation_tool_arguments(
        {
            "scope_keys": {
                "user_id": "user-1",
                "workspace_id": "ws-1",
                "surface": "chat",
            },
            "raw_user_input": "recommend me dinner",
            "messages": [{"role": "user", "content": "raw transcript"}],
        }
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "scope_keys.project_id_missing",
        "argument.raw_user_input_forbidden",
        "argument.messages_forbidden",
    ]


def test_product_lab_manager_tool_registry_exposes_recommendation_argument_contract() -> None:
    registry = build_product_lab_manager_tool_registry()
    specs = {item["tool_name"]: item for item in registry["tool_specs"]}

    recommendation_spec = specs["recommendation.run"]

    assert recommendation_spec["argument_contract"]["tool_name"] == "recommendation.run"
    assert recommendation_spec["argument_contract"]["required_scope_keys"] == [
        "user_id",
        "workspace_id",
        "project_id",
        "surface",
    ]


def test_recommendation_train_records_pr2_completion_and_next_active_slice() -> None:
    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] == 22
    assert plan["last_completed_pr_number"] == 2
    assert plan["active_pr_number"] == 3
    assert plan["last_merge_evidence"]["completed_prs"][-1] == {
        "pr_number": 2,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_tool_argument_contract_completed_locally",
    }
