from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ReusableMealVersion(BaseModel):
    version_id: str
    normalized_signature: str
    source_kind: Literal["home_cooked", "mom_bought", "store_item", "custom_combo"]
    ingredient_profile: list[str] = Field(default_factory=list)
    portion_profile: dict[str, Any] = Field(default_factory=dict)
    estimate_posture: Literal["reuse_exact", "reuse_anchored", "re_estimate_required"]
    source_refs: list[str] = Field(default_factory=list)
    supersedes_version_id: str | None = None


class UserFoodEntity(BaseModel):
    entity_id: str
    user_id: str
    workspace_id: str
    display_name: str
    status: Literal["candidate", "pending_review", "confirmed", "archived", "superseded"]
    review_required: bool = True
    current_version_id: str
    version_history: list[ReusableMealVersion] = Field(default_factory=list)
    correction_count: int = 0
    last_confirmed_at: str | None = None
    drift_status: Literal["stable", "watch", "reestimate_required", "superseded"] = "stable"


def build_reusable_meal_entity_contract() -> dict[str, Any]:
    return {
        "artifact_type": "shared_reusable_meal_entity_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "truth_owner": "reusable_meal_entity",
        "memory_is_not_truth_owner": True,
        "durable_write_enabled": False,
        "supported_estimate_postures": [
            "reuse_exact",
            "reuse_anchored",
            "re_estimate_required",
        ],
        "required_scope_keys": ["user_id", "workspace_id"],
        "required_version_fields": [
            "version_id",
            "normalized_signature",
            "source_kind",
            "estimate_posture",
            "source_refs",
        ],
        "blockers": [],
    }


__all__ = [
    "ReusableMealVersion",
    "UserFoodEntity",
    "build_reusable_meal_entity_contract",
]
