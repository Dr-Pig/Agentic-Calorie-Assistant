from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("runtime.contracts.proactive_gate")


class ProactiveGateInput(BaseModel):
    trigger_type: str
    local_time: str | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    suppressed_trigger_types: list[str] = Field(default_factory=list)
    now: datetime | None = None
    cooldown_until: datetime | None = None
    recent_send_count: int = 0
    max_recent_send_count: int | None = None
    minimum_evidence_ready: bool = True
    minimum_quality_ready: bool = True
    user_allows_proactive: bool = True


class ProactiveGateResult(BaseModel):
    allowed: bool
    status: Literal["allowed", "suppressed"]
    skip_reason: str | None = None
    trace: dict[str, Any] = Field(default_factory=dict)
