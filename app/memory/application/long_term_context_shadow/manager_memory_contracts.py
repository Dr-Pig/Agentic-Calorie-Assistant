from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.memory.application.long_term_context_shadow.contracts import _base_artifact


class MemoryIngressRequest(BaseModel):
    user_id: str
    conversation_id: str | None = None
    consumer: str
    source_classes: list[str] = Field(default_factory=list)
    max_context_tokens: int
    requires_summary_first: Literal[True] = True
    runtime_effect_allowed: Literal[False] = False


class MemoryContextPack(BaseModel):
    pack_id: str
    consumer: str
    summary_blocks: list[dict[str, Any]] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    omitted_source_classes: list[str] = Field(default_factory=list)
    freshness_posture: str
    manager_context_injection_allowed: Literal[False] = False
    runtime_effect_allowed: Literal[False] = False


class MemoryUseDecisionTrace(BaseModel):
    trace_id: str
    consumer: str
    deterministic_scope_passed: bool
    llm_semantic_decision_required_later: bool
    used_candidate_ids: list[str] = Field(default_factory=list)
    ignored_candidate_ids: list[str] = Field(default_factory=list)
    omission_reason_codes: list[str] = Field(default_factory=list)
    runtime_effect_allowed: Literal[False] = False


def _manager_memory_contract_shadow_artifact(fixture: dict[str, Any]) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="manager_memory_contract_shadow_plan",
        fixture=fixture,
        extra={
            "source_specs": [
                "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
                "docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md",
                "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
                "docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md",
            ],
            "contract_symbols": [
                "MemoryIngressRequest",
                "MemoryContextPack",
                "MemoryUseDecisionTrace",
            ],
            "active_manager_import_allowed": False,
            "manager_context_packet_changed": False,
            "runtime_tool_registered": False,
            "route_or_startup_hook_allowed": False,
            "scheduler_hook_allowed": False,
            "deterministic_role": [
                "scope_by_user_workspace_surface",
                "validate_source_class",
                "enforce_token_budget",
                "block_raw_history_dump",
                "record_omission_trace",
            ],
            "llm_manager_role_later": [
                "decide_semantic_usefulness",
                "synthesize_consumer_specific_context",
                "explain_why_memory_was_used_or_ignored",
            ],
            "human_role_later": [
                "confirm_memory_before_promotion",
                "correct_or_delete_reviewed_memory",
                "approve_runtime_injection_gate",
            ],
            "forbidden_now": [
                "active_manager_import",
                "manager_context_packet_injection",
                "durable_memory_write",
                "live_retrieval_tool_call",
                "provider_call",
            ],
        },
    )


__all__ = [
    "MemoryContextPack",
    "MemoryIngressRequest",
    "MemoryUseDecisionTrace",
    "_manager_memory_contract_shadow_artifact",
]
