from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("rescue.domain.proposal_read_models")


class ProposalRecordSnapshot(BaseModel):
    proposal_id: str
    proposal_type: str
    proposal_status: str
    title: str
    summary: str
    explanation: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class RescueProposalReadItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: str
    proposal_status: str
    title: str
    summary: str
    expandable_explanation: str
    primary_actions: list[str] = Field(default_factory=list, max_length=0)
    action_surface: Literal["read_only_shadow_status"] = "read_only_shadow_status"
    formal_commit_handler_bound: Literal[False] = False
    raw_trace_exposed: Literal[False] = False
    created_at: datetime

    @field_validator("primary_actions")
    @classmethod
    def validate_primary_actions_are_empty(cls, value: list[str]) -> list[str]:
        if value:
            raise ValueError("rescue proposal read model is shadow-only and cannot expose primary actions")
        return value


class ActiveRescueProposalInbox(BaseModel):
    source_kind: Literal["proposal_read_model"] = "proposal_read_model"
    items: list[RescueProposalReadItem] = Field(default_factory=list)


class RescueProposalHistory(BaseModel):
    source_kind: Literal["proposal_read_model"] = "proposal_read_model"
    items: list[RescueProposalReadItem] = Field(default_factory=list)
