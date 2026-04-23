from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.shared.contracts.common import MealStatus


class CanonicalMealState(BaseModel):
    meal_id: int | None = None
    meal_title: str = ""
    status: MealStatus = "candidate_meal"
    components: list[dict[str, Any]] = Field(default_factory=list)
    pending_questions: list[str] = Field(default_factory=list)
    unresolved_info: list[str] = Field(default_factory=list)
    followup_count: int = 0
    asked_questions_history: list[str] = Field(default_factory=list)
    last_followup_key: str | None = None
    boundary_history: list[str] = Field(default_factory=list)
    last_updated_at: datetime | None = None
    source_log_ids: list[int] = Field(default_factory=list)
