from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.composition.phase_c_transaction_ports import (
    BudgetLedgerRepositoryPort,
    CanonicalMealCommitDraft,
    CanonicalMealCommitStaged,
    LegacyMealLogBridgePort,
    LedgerAuditPort,
    MealThreadRepositoryPort,
    PhaseCTransactionError,
    PhaseCUnitOfWorkPort,
    stage_phase_c_commit_transaction,
)


class _InjectedFailure(RuntimeError):
    pass


@dataclass
class _FakeUnitOfWork(PhaseCUnitOfWorkPort):
    fail_on: str | None = None
    pending: dict[str, list[Any]] = field(
        default_factory=lambda: {"canonical": [], "legacy_bridge": [], "ledger_audit": [], "budget_refresh": []}
    )
    committed: dict[str, list[Any]] = field(
        default_factory=lambda: {"canonical": [], "legacy_bridge": [], "ledger_audit": [], "budget_refresh": []}
    )
    committed_called: bool = False
    rolled_back_called: bool = False

    def assert_can_stage(self, step: str) -> None:
        if self.fail_on == step:
            raise _InjectedFailure(step)

    def commit(self) -> None:
        self.assert_can_stage("commit")
        for key, values in self.pending.items():
            self.committed[key].extend(values)
        self.pending = {"canonical": [], "legacy_bridge": [], "ledger_audit": [], "budget_refresh": []}
        self.committed_called = True

    def rollback(self) -> None:
        self.pending = {"canonical": [], "legacy_bridge": [], "ledger_audit": [], "budget_refresh": []}
        self.rolled_back_called = True


class _FakeMealThreadRepository(MealThreadRepositoryPort):
    def stage_canonical_meal_commit(
        self,
        uow: _FakeUnitOfWork,
        draft: CanonicalMealCommitDraft,
    ) -> CanonicalMealCommitStaged:
        uow.assert_can_stage("canonical")
        staged = CanonicalMealCommitStaged(
            meal_thread_id=draft.meal_thread_id or 101,
            meal_version_id=202,
            local_date=draft.local_date,
            consumed_kcal=draft.consumed_kcal,
        )
        uow.pending["canonical"].append(staged)
        return staged


class _FakeLegacyMealLogBridge(LegacyMealLogBridgePort):
    def stage_legacy_meal_log_bridge(
        self,
        uow: _FakeUnitOfWork,
        staged_commit: CanonicalMealCommitStaged,
        *,
        legacy_meal_log_id: int | None,
    ) -> None:
        uow.assert_can_stage("legacy_bridge")
        if legacy_meal_log_id is not None:
            uow.pending["legacy_bridge"].append(
                {
                    "meal_log_id": legacy_meal_log_id,
                    "meal_thread_id": staged_commit.meal_thread_id,
                    "meal_version_id": staged_commit.meal_version_id,
                }
            )


class _FakeLedgerAudit(LedgerAuditPort):
    def stage_meal_consumption_audit(
        self,
        uow: _FakeUnitOfWork,
        staged_commit: CanonicalMealCommitStaged,
    ) -> None:
        uow.assert_can_stage("ledger_audit")
        uow.pending["ledger_audit"].append(
            {
                "entry_type": "meal_consumption",
                "source_type": "meal_version",
                "source_id": staged_commit.meal_version_id,
                "delta_kcal": staged_commit.consumed_kcal,
            }
        )


class _FakeBudgetLedgerRepository(BudgetLedgerRepositoryPort):
    def stage_budget_refresh(
        self,
        uow: _FakeUnitOfWork,
        staged_commit: CanonicalMealCommitStaged,
        *,
        budget_kcal: int | None,
    ) -> None:
        uow.assert_can_stage("budget_refresh")
        uow.pending["budget_refresh"].append(
            {
                "local_date": staged_commit.local_date,
                "budget_kcal": budget_kcal,
                "observed_runtime_policy": "preserve_current_behavior",
            }
        )


def _draft() -> CanonicalMealCommitDraft:
    return CanonicalMealCommitDraft(
        user_id=7,
        meal_thread_id=None,
        local_date="2026-05-01",
        consumed_kcal=420,
        legacy_meal_log_id=555,
        budget_kcal=1800,
    )


def _run(fake_uow: _FakeUnitOfWork):
    return stage_phase_c_commit_transaction(
        uow=fake_uow,
        meal_threads=_FakeMealThreadRepository(),
        legacy_bridge=_FakeLegacyMealLogBridge(),
        ledger_audit=_FakeLedgerAudit(),
        budget_ledgers=_FakeBudgetLedgerRepository(),
        draft=_draft(),
    )


def test_phase_c_transaction_contract_commits_canonical_bridge_audit_and_budget_refresh_atomically() -> None:
    uow = _FakeUnitOfWork()

    result = _run(uow)

    assert result.committed is True
    assert uow.committed_called is True
    assert uow.rolled_back_called is False
    assert len(uow.committed["canonical"]) == 1
    assert uow.committed["legacy_bridge"] == [{"meal_log_id": 555, "meal_thread_id": 101, "meal_version_id": 202}]
    assert uow.committed["ledger_audit"] == [
        {"entry_type": "meal_consumption", "source_type": "meal_version", "source_id": 202, "delta_kcal": 420}
    ]
    assert uow.committed["budget_refresh"] == [
        {"local_date": "2026-05-01", "budget_kcal": 1800, "observed_runtime_policy": "preserve_current_behavior"}
    ]


@pytest.mark.parametrize(
    ("fail_on", "expected_staged_before_failure"),
    [
        ("canonical", {"canonical": 0, "legacy_bridge": 0, "ledger_audit": 0, "budget_refresh": 0}),
        ("legacy_bridge", {"canonical": 1, "legacy_bridge": 0, "ledger_audit": 0, "budget_refresh": 0}),
        ("ledger_audit", {"canonical": 1, "legacy_bridge": 1, "ledger_audit": 0, "budget_refresh": 0}),
        ("budget_refresh", {"canonical": 1, "legacy_bridge": 1, "ledger_audit": 1, "budget_refresh": 0}),
        ("commit", {"canonical": 1, "legacy_bridge": 1, "ledger_audit": 1, "budget_refresh": 1}),
    ],
)
def test_phase_c_transaction_contract_rolls_back_any_partial_state_on_failure(
    fail_on: str,
    expected_staged_before_failure: dict[str, int],
) -> None:
    uow = _FakeUnitOfWork(fail_on=fail_on)

    with pytest.raises(PhaseCTransactionError) as exc_info:
        _run(uow)

    assert exc_info.value.failed_step == fail_on
    assert exc_info.value.staged_counts_before_rollback == expected_staged_before_failure
    assert uow.rolled_back_called is True
    assert uow.committed_called is False
    assert uow.pending == {"canonical": [], "legacy_bridge": [], "ledger_audit": [], "budget_refresh": []}
    assert uow.committed == {"canonical": [], "legacy_bridge": [], "ledger_audit": [], "budget_refresh": []}
