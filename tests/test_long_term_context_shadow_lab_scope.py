from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_scope_isolation_shadow_eval_blocks_cross_user_project_and_session_leakage() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "scope_isolation_shadow_eval"
    ]

    assert artifact["artifact_type"] == "scope_isolation_shadow_eval"
    assert artifact["scope_key_owner"] == "deterministic_runtime_boundary_later"
    assert artifact["llm_scope_override_allowed"] is False
    assert artifact["retrieval_tool_called"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["required_scope_keys"] == [
        "user_id",
        "workspace_id",
        "project_id",
        "surface",
    ]
    assert artifact["candidate_scope_coverage"]["candidate_count"] > 0
    assert artifact["candidate_scope_coverage"]["missing_scope_key_count"] == 0

    cases = {case["case_id"]: case for case in artifact["regression_cases"]}
    assert cases["same_user_two_projects"]["cross_project_recall_allowed"] is False
    assert cases["two_users_shared_surface"]["cross_user_recall_allowed"] is False
    assert cases["session_memory_vs_user_memory"]["scope_merge_allowed"] is False
    assert cases["missing_scope_keys"]["retrieval_allowed"] is False
