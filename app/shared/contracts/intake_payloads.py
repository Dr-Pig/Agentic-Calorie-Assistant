from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import CommitVersionReason, MealStatus


class MealItemPayload(BaseModel):
    name: str
    quantity_hint: str | None = None
    source: Literal["llm", "retrieval", "lookup", "user"] = "llm"
    evidence_role: Literal[
        "exact_truth", "ingredient_anchor", "meal_pattern_prior", "retailer_fallback", "user_provided", "unknown"
    ] = "unknown"
    estimate_basis: Literal["exact", "anchored", "heuristic_only", "llm_only", "user_provided"] = "llm_only"
    confidence_tier: Literal["high", "medium", "low"] = "low"
    estimated_kcal: int = 0
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    evidence_ids: list[str] = Field(default_factory=list)
    classification: dict[str, Any] = Field(default_factory=dict)


class CommitRequestCandidate(BaseModel):
    commit_kind: Literal["meal_commit"] = "meal_commit"
    request_id: str
    manager_intent: str
    meal_thread_id: int | None = None
    parent_version_id: int | None = None
    version_reason: CommitVersionReason
    meal_title: str
    raw_input: str
    estimated_kcal: int
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    resolution_status: MealStatus
    occurred_at: datetime | None = None
    local_date: str
    items: list[MealItemPayload] = Field(default_factory=list)
    trace_ref: dict[str, Any] = Field(default_factory=dict)
