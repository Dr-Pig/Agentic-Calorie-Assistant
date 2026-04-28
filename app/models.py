"""Thin re-export shim -- protected legacy file.

All ORM models are defined in their owning domain's infrastructure layer.
This file re-exports them for backward compatibility.
"""
from app.shared.infra.models import Base, utcnow, User, MealLog, MessageBuffer, ProactiveTriggerRecord  # noqa: F401
from app.intake.infrastructure.models import MealThreadRecord, MealVersionRecord, MealItemRecord, LegacyMealLogMapRecord  # noqa: F401
from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord  # noqa: F401
from app.body.infrastructure.models import BodyObservationRecord, BodyProfileRecord, BodyPlanRecord  # noqa: F401
from app.archive.rescue.infrastructure.models import ProposalContainerRecord, ProposalOptionRecord  # noqa: F401

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
    "ProposalContainerRecord",
    "ProposalOptionRecord",
    "ProactiveTriggerRecord",
]
