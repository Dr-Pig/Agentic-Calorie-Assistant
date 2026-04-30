"""Thin re-export shim -- protected legacy file.

All ORM models are defined in their owning domain's infrastructure layer.
This file re-exports them for backward compatibility.
"""
from app.shared.infra.models import (  # noqa: F401
    Base,
    MealLog,
    MessageBuffer,
    ProactiveTriggerRecord,
    ProposalContainerRecord,
    ProposalOptionRecord,
    User,
    utcnow,
)
from app.intake.infrastructure.models import MealThreadRecord, MealVersionRecord, MealItemRecord, LegacyMealLogMapRecord  # noqa: F401
from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord  # noqa: F401
from app.body.infrastructure.models import BodyObservationRecord, BodyProfileRecord, BodyPlanRecord  # noqa: F401

__all__ = [
    "Base",
    "utcnow",
    "User",
    "MealLog",
    "MessageBuffer",
    "MealThreadRecord",
    "MealVersionRecord",
    "MealItemRecord",
    "LegacyMealLogMapRecord",
    "DayBudgetLedgerRecord",
    "LedgerEntryRecord",
    "BodyObservationRecord",
    "BodyProfileRecord",
    "BodyPlanRecord",
    "ProactiveTriggerRecord",
]
