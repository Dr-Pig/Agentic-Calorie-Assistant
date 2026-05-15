from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class V2ResolvedState:
    user_external_id: str
    user_id: int
    local_date: str
    onboarding_ready: bool
    active_body_plan_view: Any
    current_budget_view: Any
    active_meal: dict[str, Any] | None
    conversation_state: Any
    injected_context: dict[str, Any]
