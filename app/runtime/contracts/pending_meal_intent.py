from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("runtime.contracts.pending_meal_intent")


PendingMealIntentStatus = Literal["created", "confirmed_eaten", "dismissed", "expired"]
PendingMealIntentSourceSurface = Literal["chat", "recommendation_card", "menu_scan", "unknown"]


class PendingMealIntent(BaseModel):
    intent_id: str
    user_id: str
    candidate_title: str
    source_surface: PendingMealIntentSourceSurface = "unknown"
    status: PendingMealIntentStatus = "created"
    created_at: datetime
    expires_at: datetime
    candidate_metadata: dict[str, Any] = Field(default_factory=dict)
    canonical_write_authorized: Literal[False] = False

    @property
    def is_active(self) -> bool:
        return self.status == "created"

    def to_trace_payload(self) -> dict[str, Any]:
        return {
            "contract_scope": "pending_meal_intent_only",
            "intent_id": self.intent_id,
            "status": self.status,
            "source_surface": self.source_surface,
            "canonical_write_authorized": self.canonical_write_authorized,
            "dismissed_scope": "current_intent_instance_only" if self.status == "dismissed" else None,
        }
