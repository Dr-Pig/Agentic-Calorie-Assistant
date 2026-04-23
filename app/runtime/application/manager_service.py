from __future__ import annotations

from ..agent.manager import IntakeManagerResult, run_intake_manager


MAX_MANAGER_ROUNDS = 3


__all__ = [
    "MAX_MANAGER_ROUNDS",
    "IntakeManagerResult",
    "run_intake_manager",
]
