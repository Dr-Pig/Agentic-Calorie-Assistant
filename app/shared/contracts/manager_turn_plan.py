from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.shared.contracts.capability_registry import build_shared_capability_registry


class CapabilityRequest(BaseModel):
    capability_id: str
    request_mode: Literal["required", "optional", "deferred_candidate"]
    priority: int = 0


class ToolCallCandidate(BaseModel):
    tool_name: str
    capability_id: str
    requires_prior_call_ids: list[str] = Field(default_factory=list)


class ManagerTurnPlan(BaseModel):
    primary_workflow: str
    secondary_intents: list[str] = Field(default_factory=list)
    requested_capabilities: list[CapabilityRequest] = Field(default_factory=list)
    candidate_tool_calls: list[ToolCallCandidate] = Field(default_factory=list)
    ordering_constraints: list[str] = Field(default_factory=list)
    mutation_posture: Literal["read_only", "proposal_only", "mutation_guarded"]
    clarification_posture: Literal["none", "optional", "required"]
    response_obligations: list[str] = Field(default_factory=list)
    omission_candidates: list[str] = Field(default_factory=list)
    scope_keys: dict[str, str] = Field(default_factory=dict)


class FinalResponsePlan(BaseModel):
    response_mode: Literal["chat_first", "answer_only", "proposal", "mixed"]
    user_visible_capabilities: list[str] = Field(default_factory=list)
    source_tool_call_ids: list[str] = Field(default_factory=list)
    action_affordances: list[str] = Field(default_factory=list)
    must_not_claim: list[str] = Field(default_factory=list)


def build_manager_turn_plan_contract() -> dict[str, Any]:
    registry = build_shared_capability_registry()
    capability_ids = [item["capability_id"] for item in registry["capabilities"]]
    return {
        "artifact_type": "shared_manager_turn_plan_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "allowed_capability_ids": capability_ids,
        "allowed_mutation_postures": ["read_only", "proposal_only", "mutation_guarded"],
        "allowed_clarification_postures": ["none", "optional", "required"],
        "allowed_response_modes": ["chat_first", "answer_only", "proposal", "mixed"],
        "planner_outputs_structure_not_raw_transcript": True,
        "shared_capability_registry_required": True,
        "blockers": [],
    }


__all__ = [
    "CapabilityRequest",
    "FinalResponsePlan",
    "ManagerTurnPlan",
    "ToolCallCandidate",
    "build_manager_turn_plan_contract",
]
