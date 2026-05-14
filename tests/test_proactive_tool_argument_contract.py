from __future__ import annotations

import yaml

from app.advanced_shadow_lab.product_lab_manager_tool_contract import (
    build_product_lab_manager_tool_registry,
)
from app.shared.contracts.proactive_tool_arguments import (
    build_proactive_tool_argument_contract,
    validate_proactive_tool_arguments,
)


def test_proactive_tool_argument_contract_requires_scope_wake_ref_and_call_refs() -> None:
    contract = build_proactive_tool_argument_contract()

    assert contract["artifact_type"] == "shared_proactive_tool_argument_contract"
    assert contract["tool_name"] == "proactive.run"
    assert contract["required_scope_keys"] == [
        "user_id",
        "workspace_id",
        "project_id",
        "surface",
    ]
    assert contract["required_wake_source_ref_fields"] == [
        "wake_source",
        "source_id",
        "user_relevant_reason",
        "downstream_workflow_family",
        "permission_posture",
    ]
    assert contract["allowed_call_ref_fields"] == [
        "memory_context_call_id",
        "recommendation_call_id",
        "rescue_call_id",
        "pending_meal_intent_call_id",
        "control_state_call_id",
    ]
    assert contract["raw_transcript_bypass_allowed"] is False
    assert contract["production_notification_delivery_allowed"] is False
    assert contract["blockers"] == []


def test_proactive_tool_argument_validation_accepts_scoped_wake_and_refs() -> None:
    artifact = validate_proactive_tool_arguments(
        {
            "scope_keys": _scope(),
            "wake_source_ref": {
                "wake_source": "app_open",
                "source_id": "rec-candidate-1",
                "user_relevant_reason": "meal_time_candidate_ready",
                "downstream_workflow_family": "recommendation",
                "permission_posture": "app_open_only",
            },
            "memory_context_call_id": "memory-1",
            "recommendation_call_id": "recommendation-1",
        }
    )

    assert artifact["status"] == "pass"
    assert artifact["normalized_scope_keys"] == _scope()
    assert artifact["wake_source_ref"]["wake_source"] == "app_open"
    assert artifact["context_call_refs"] == {
        "memory_context_call_id": "memory-1",
        "recommendation_call_id": "recommendation-1",
    }
    assert artifact["raw_transcript_bypass_allowed"] is False
    assert artifact["blockers"] == []


def test_proactive_tool_argument_validation_blocks_missing_wake_and_raw_prompt() -> None:
    artifact = validate_proactive_tool_arguments(
        {
            "scope_keys": {"user_id": "user-1", "workspace_id": "ws-1", "surface": "chat"},
            "wake_source_ref": {
                "wake_source": "cron",
                "source_id": "",
                "downstream_workflow_family": "recommendation",
                "permission_posture": "push_allowed",
            },
            "raw_transcript": "full chat history",
            "manager_context_packet": {"raw": "packet"},
            "recommendation_offer_call_id": "unsupported",
        }
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "scope_keys.project_id_missing",
        "wake_source_ref.source_id_missing",
        "wake_source_ref.user_relevant_reason_missing",
        "wake_source_ref.wake_source_unsupported:cron",
        "wake_source_ref.permission_posture_unsupported:push_allowed",
        "argument.raw_transcript_forbidden",
        "argument.manager_context_packet_forbidden",
        "argument.recommendation_offer_call_id_unsupported_call_ref",
    ]


def test_product_lab_manager_tool_registry_exposes_proactive_argument_contract() -> None:
    registry = build_product_lab_manager_tool_registry()
    specs = {item["tool_name"]: item for item in registry["tool_specs"]}

    proactive_spec = specs["proactive.run"]

    assert proactive_spec["argument_contract"]["tool_name"] == "proactive.run"
    assert proactive_spec["argument_contract"]["required_wake_source_ref_fields"][0] == "wake_source"
    assert proactive_spec["argument_contract"]["production_notification_delivery_allowed"] is False


def test_proactive_train_records_pr2_completion_and_next_active_slice() -> None:
    with open(
        "docs/quality/advanced_product_lab_proactive_chat_first_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 22
    assert plan["last_completed_pr_number"] >= 2
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 3
    assert {
        "pr_number": 2,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "proactive_tool_argument_contract_completed_locally",
        "dynamic_remaining_pr_count_after": 22,
    } in plan["last_merge_evidence"]["completed_prs"]


def _scope() -> dict[str, str]:
    return {
        "user_id": "user-1",
        "workspace_id": "ws-1",
        "project_id": "project-1",
        "surface": "chat",
    }
