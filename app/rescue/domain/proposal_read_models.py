from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

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
    proposal_id: str
    proposal_status: str
    title: str
    summary: str
    expandable_explanation: str
    primary_actions: list[str] = Field(default_factory=list)
    raw_trace_exposed: Literal[False] = False
    created_at: datetime


class ActiveRescueProposalInbox(BaseModel):
    source_kind: Literal["proposal_read_model"] = "proposal_read_model"
    items: list[RescueProposalReadItem] = Field(default_factory=list)


class RescueProposalHistory(BaseModel):
    source_kind: Literal["proposal_read_model"] = "proposal_read_model"
    items: list[RescueProposalReadItem] = Field(default_factory=list)
