from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


_PHASE_C_STAGING_KEYS = ("canonical", "legacy_bridge", "ledger_audit", "budget_refresh")


@dataclass(frozen=True)
class CanonicalMealCommitDraft:
    user_id: int
    meal_thread_id: int | None
    local_date: str
    consumed_kcal: int
    legacy_meal_log_id: int | None = None
    budget_kcal: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CanonicalMealCommitStaged:
    meal_thread_id: int
    meal_version_id: int
    local_date: str
    consumed_kcal: int


@dataclass(frozen=True)
class PhaseCTransactionResult:
    committed: bool
    staged_commit: CanonicalMealCommitStaged


class PhaseCTransactionError(RuntimeError):
    def __init__(
        self,
        *,
        failed_step: str,
        cause: BaseException,
        staged_counts_before_rollback: dict[str, int],
    ) -> None:
        super().__init__(f"phase_c_transaction_failed:{failed_step}")
        self.failed_step = failed_step
        self.cause = cause
        self.staged_counts_before_rollback = staged_counts_before_rollback


@runtime_checkable
class PhaseCUnitOfWorkPort(Protocol):
    def commit(self) -> None:
        """Atomically persist all staged canonical, bridge, audit, and budget refresh work."""

    def rollback(self) -> None:
        """Discard all staged Phase C work."""


@runtime_checkable
class MealThreadRepositoryPort(Protocol):
    def stage_canonical_meal_commit(
        self,
        uow: PhaseCUnitOfWorkPort,
        draft: CanonicalMealCommitDraft,
    ) -> CanonicalMealCommitStaged:
        """Stage canonical MealThread / MealVersion / MealItem writes without committing."""


@runtime_checkable
class LegacyMealLogBridgePort(Protocol):
    def stage_legacy_meal_log_bridge(
        self,
        uow: PhaseCUnitOfWorkPort,
        staged_commit: CanonicalMealCommitStaged,
        *,
        legacy_meal_log_id: int | None,
    ) -> None:
        """Stage compatibility bridge writes without defining canonical truth."""


@runtime_checkable
class LedgerAuditPort(Protocol):
    def stage_meal_consumption_audit(
        self,
        uow: PhaseCUnitOfWorkPort,
        staged_commit: CanonicalMealCommitStaged,
    ) -> None:
        """Stage append-only audit events; current consumed truth remains recomputed elsewhere."""


@runtime_checkable
class BudgetLedgerRepositoryPort(Protocol):
    def stage_budget_refresh(
        self,
        uow: PhaseCUnitOfWorkPort,
        staged_commit: CanonicalMealCommitStaged,
        *,
        budget_kcal: int | None,
    ) -> None:
        """Stage budget refresh/read-model work without changing product semantics."""


def _staged_counts(uow: PhaseCUnitOfWorkPort) -> dict[str, int]:
    pending = getattr(uow, "pending", None)
    if not isinstance(pending, dict):
        return {key: 0 for key in _PHASE_C_STAGING_KEYS}
    return {
        key: len(value) if isinstance(value, list) else 0
        for key, value in ((key, pending.get(key)) for key in _PHASE_C_STAGING_KEYS)
    }


def stage_phase_c_commit_transaction(
    *,
    uow: PhaseCUnitOfWorkPort,
    meal_threads: MealThreadRepositoryPort,
    legacy_bridge: LegacyMealLogBridgePort,
    ledger_audit: LedgerAuditPort,
    budget_ledgers: BudgetLedgerRepositoryPort,
    draft: CanonicalMealCommitDraft,
) -> PhaseCTransactionResult:
    failed_step = "unknown"
    staged_commit: CanonicalMealCommitStaged | None = None
    try:
        failed_step = "canonical"
        staged_commit = meal_threads.stage_canonical_meal_commit(uow, draft)

        failed_step = "legacy_bridge"
        legacy_bridge.stage_legacy_meal_log_bridge(
            uow,
            staged_commit,
            legacy_meal_log_id=draft.legacy_meal_log_id,
        )

        failed_step = "ledger_audit"
        ledger_audit.stage_meal_consumption_audit(uow, staged_commit)

        failed_step = "budget_refresh"
        budget_ledgers.stage_budget_refresh(uow, staged_commit, budget_kcal=draft.budget_kcal)

        failed_step = "commit"
        uow.commit()
    except BaseException as exc:
        staged_counts = _staged_counts(uow)
        uow.rollback()
        raise PhaseCTransactionError(
            failed_step=failed_step,
            cause=exc,
            staged_counts_before_rollback=staged_counts,
        ) from exc
    assert staged_commit is not None
    return PhaseCTransactionResult(committed=True, staged_commit=staged_commit)


__all__ = [
    "BudgetLedgerRepositoryPort",
    "CanonicalMealCommitDraft",
    "CanonicalMealCommitStaged",
    "LedgerAuditPort",
    "LegacyMealLogBridgePort",
    "MealThreadRepositoryPort",
    "PhaseCTransactionError",
    "PhaseCTransactionResult",
    "PhaseCUnitOfWorkPort",
    "stage_phase_c_commit_transaction",
]
