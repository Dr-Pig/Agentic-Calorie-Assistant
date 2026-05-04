from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


REQUIRED_SCOPE_KEYS = ["user_id", "workspace_id", "project_id", "surface"]


def _scope_isolation_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    missing = [
        candidate.candidate_id
        for candidate in candidates
        if not set(REQUIRED_SCOPE_KEYS).issubset(candidate.scope_keys)
    ]
    return _base_artifact(
        artifact_type="scope_isolation_shadow_eval",
        fixture=fixture,
        extra={
            "scope_key_owner": "deterministic_runtime_boundary_later",
            "llm_scope_override_allowed": False,
            "retrieval_tool_called": False,
            "required_scope_keys": REQUIRED_SCOPE_KEYS,
            "candidate_scope_coverage": {
                "candidate_count": len(candidates),
                "missing_scope_key_count": len(missing),
                "missing_scope_key_candidate_ids": missing,
            },
            "regression_cases": _regression_cases(),
            "future_query_policy": {
                "metadata_filter_before_semantic_search": True,
                "missing_scope_key_blocks_retrieval": True,
                "cross_user_join_allowed": False,
                "cross_project_join_allowed": False,
                "raw_transcript_return_allowed": False,
            },
        },
    )


def _regression_cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "same_user_two_projects",
            "cross_project_recall_allowed": False,
            "required_filter": ["user_id", "project_id"],
            "runtime_effect_allowed": False,
        },
        {
            "case_id": "two_users_shared_surface",
            "cross_user_recall_allowed": False,
            "required_filter": ["user_id", "surface"],
            "runtime_effect_allowed": False,
        },
        {
            "case_id": "session_memory_vs_user_memory",
            "scope_merge_allowed": False,
            "required_filter": ["user_id", "workspace_id", "project_id"],
            "runtime_effect_allowed": False,
        },
        {
            "case_id": "missing_scope_keys",
            "retrieval_allowed": False,
            "block_reason": "scope_keys_required_before_recall",
            "runtime_effect_allowed": False,
        },
    ]


__all__ = ["_scope_isolation_shadow_artifact"]
