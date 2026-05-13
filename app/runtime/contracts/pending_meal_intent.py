from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("runtime.contracts.pending_meal_intent")


PendingMealIntentStatus = Literal["created", "confirmed_eaten", "dismissed", "expired"]
PendingMealIntentSourceSurface = Literal["chat", "recommendation_card", "menu_scan", "unknown"]
PendingMealIntentWindow = Literal["breakfast", "lunch", "dinner", "late_night", "unknown"]
PendingMealIntentWindowSource = Literal[
    "default",
    "confirmed_memory",
    "pattern_memory",
    "user_explicit",
    "unknown",
]
PendingMealIntentFollowupTiming = Literal["meal_window_end", "explicit_user_time", "none"]
PendingMealIntentQuietHoursPolicy = Literal[
    "chat_thread_message_only_no_push",
    "none",
]


class PendingMealIntentScopeKeys(BaseModel):
    user_id: str
    workspace_id: str = "default"
    project_id: str = "default"
    surface: PendingMealIntentSourceSurface = "unknown"


class PendingMealIntentTTLPolicy(BaseModel):
    ttl_hours: int = 6
    max_ttl_hours: int = 6
    expiry_source: Literal["default", "explicit_user_time", "meal_window_policy"] = "default"

    @model_validator(mode="after")
    def _validate_ttl_bounds(self) -> "PendingMealIntentTTLPolicy":
        if self.ttl_hours <= 0:
            raise ValueError("ttl_policy.ttl_hours must be positive")
        if self.max_ttl_hours <= 0:
            raise ValueError("ttl_policy.max_ttl_hours must be positive")
        if self.ttl_hours > self.max_ttl_hours:
            raise ValueError("ttl_policy.ttl_hours must not exceed max_ttl_hours")
        return self


class PendingMealIntentMealWindowPosture(BaseModel):
    target_window: PendingMealIntentWindow = "unknown"
    window_source: PendingMealIntentWindowSource = "unknown"
    followup_timing: PendingMealIntentFollowupTiming = "meal_window_end"
    quiet_hours_policy: PendingMealIntentQuietHoursPolicy = "chat_thread_message_only_no_push"
    local_timezone: str = "Asia/Taipei"


class PendingMealIntentContextPackIdentity(BaseModel):
    block_type: Literal["PENDING_MEAL_INTENT"] = "PENDING_MEAL_INTENT"
    block_id: str | None = None
    source_ref: str | None = None
    include_in_manager_context: bool = True
    canonical_write_authorized: Literal[False] = False


class PendingMealIntent(BaseModel):
    contract_version: Literal["2.0"] = "2.0"
    intent_id: str
    user_id: str
    scope_keys: PendingMealIntentScopeKeys | None = None
    candidate_title: str
    source_surface: PendingMealIntentSourceSurface = "unknown"
    status: PendingMealIntentStatus = "created"
    created_at: datetime
    expires_at: datetime
    ttl_policy: PendingMealIntentTTLPolicy = Field(default_factory=PendingMealIntentTTLPolicy)
    meal_window_posture: PendingMealIntentMealWindowPosture = Field(
        default_factory=PendingMealIntentMealWindowPosture
    )
    context_pack_identity: PendingMealIntentContextPackIdentity | None = None
    candidate_metadata: dict[str, Any] = Field(default_factory=dict)
    canonical_write_authorized: Literal[False] = False

    @property
    def is_active(self) -> bool:
        return self.is_active_at(datetime.now(tz=self.expires_at.tzinfo))

    @model_validator(mode="after")
    def _validate_context_boundaries(self) -> "PendingMealIntent":
        if self.scope_keys is None:
            self.scope_keys = PendingMealIntentScopeKeys(
                user_id=self.user_id,
                surface=self.source_surface,
            )
        if self.scope_keys.user_id != self.user_id:
            raise ValueError("scope_keys.user_id must match user_id")

        duration = self.expires_at - self.created_at
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        if duration > timedelta(hours=self.ttl_policy.max_ttl_hours):
            raise ValueError("expires_at exceeds ttl_policy.max_ttl_hours")

        expected_block_id = f"pending_meal_intent:{self.intent_id}"
        expected_source_ref = f"pending_meal_intent:{self.intent_id}"
        if self.context_pack_identity is None:
            self.context_pack_identity = PendingMealIntentContextPackIdentity(
                block_id=expected_block_id,
                source_ref=expected_source_ref,
            )
        if self.context_pack_identity.block_id not in {None, expected_block_id}:
            raise ValueError("context_pack_identity.block_id must match intent_id")
        if self.context_pack_identity.block_id is None:
            self.context_pack_identity.block_id = expected_block_id
        if self.context_pack_identity.source_ref is None:
            self.context_pack_identity.source_ref = expected_source_ref
        return self

    def is_active_at(self, now: datetime) -> bool:
        return self.status == "created" and now < self.expires_at

    def to_context_pack_block(self) -> dict[str, Any]:
        return {
            "block_type": self.context_pack_identity.block_type,
            "block_id": self.context_pack_identity.block_id,
            "source_ref": self.context_pack_identity.source_ref,
            "state_category": "short_term_context",
            "intent_id": self.intent_id,
            "candidate_title": self.candidate_title,
            "source_surface": self.source_surface,
            "status": self.status,
            "scope_keys": self.scope_keys.model_dump(),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "ttl_policy": self.ttl_policy.model_dump(),
            "meal_window_posture": self.meal_window_posture.model_dump(),
            "candidate_metadata_summary": self._candidate_metadata_summary(),
            "canonical_write_authorized": self.canonical_write_authorized,
            "intake_handoff_required": True,
            "durable_memory_write_authorized": False,
        }

    def to_trace_payload(self) -> dict[str, Any]:
        return {
            "contract_scope": "pending_meal_intent_only",
            "contract_version": self.contract_version,
            "state_category": "short_term_context",
            "intent_id": self.intent_id,
            "status": self.status,
            "source_surface": self.source_surface,
            "scope_keys": self.scope_keys.model_dump(),
            "ttl_policy": self.ttl_policy.model_dump(),
            "meal_window_posture": self.meal_window_posture.model_dump(),
            "context_pack_block_id": self.context_pack_identity.block_id,
            "canonical_write_authorized": self.canonical_write_authorized,
            "durable_memory_write_authorized": False,
            "dismissed_scope": "current_intent_instance_only" if self.status == "dismissed" else None,
        }

    def _candidate_metadata_summary(self) -> dict[str, Any]:
        allowed_keys = {
            "candidate_id",
            "store_name",
            "estimated_kcal",
            "source_refs",
            "meal_window",
        }
        return {
            key: value
            for key, value in self.candidate_metadata.items()
            if key in allowed_keys and _is_bounded_metadata_value(value)
        }


def _is_bounded_metadata_value(value: Any) -> bool:
    if isinstance(value, str):
        return len(value) <= 200
    if isinstance(value, int | float | bool) or value is None:
        return True
    if isinstance(value, list):
        return len(value) <= 5 and all(isinstance(item, str) and len(item) <= 120 for item in value)
    return False
