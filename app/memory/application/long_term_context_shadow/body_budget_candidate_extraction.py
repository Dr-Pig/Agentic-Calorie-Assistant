from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.candidate_records import _candidate
from app.memory.application.long_term_context_shadow.utils import (
    _confidence,
    _float_value,
    _parse_date_as_datetime,
    _parse_datetime,
    _source_ref,
    _trace_id,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _body_logging_candidates(
    user_id: str,
    observations: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not observations:
        return []
    observed_at = [_parse_datetime(item.get("observed_at")) for item in observations]
    trace_ids = [_trace_id(item) for item in observations]
    refs = [
        _source_ref(
            item,
            trace_refs,
            fallback_kind="BodyObservation",
            fallback_id_key="trace_id",
        )
        for item in observations
    ]
    return [
        _candidate(
            candidate_id="pattern-weight-logging-consistency",
            candidate_type="logging_adherence_pattern",
            user_id=user_id,
            source_trace_ids=trace_ids,
            source_object_refs=refs,
            evidence_count=len(observations),
            observed_at=[value for value in observed_at if value is not None],
            confidence=_confidence(len(observations), threshold=4),
            proposed_memory_text="Observed body logging consistency candidate",
            payload={"observation_count": len(observations)},
            reason_codes=["l2a_weight_logging_consistency"],
            intended_consumers=["calibration", "proactive", "rescue_later"],
        )
    ]


def _budget_candidates(
    user_id: str,
    budgets: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not budgets:
        return []
    overshoots = [
        budget for budget in budgets if _float_value(budget.get("overshoot_kcal")) > 0
    ]
    trace_ids = [_trace_id(budget) for budget in budgets]
    observed_at = [_parse_date_as_datetime(budget.get("date")) for budget in budgets]
    return [
        _candidate(
            candidate_id="pattern-budget-overshoot-frequency",
            candidate_type="logging_adherence_pattern",
            user_id=user_id,
            source_trace_ids=trace_ids,
            source_object_refs=[
                _source_ref(
                    budget,
                    trace_refs,
                    fallback_kind="DayBudgetLedger",
                    fallback_id_key="date",
                )
                for budget in budgets
            ],
            evidence_count=len(budgets),
            observed_at=[value for value in observed_at if value is not None],
            confidence=_confidence(len(overshoots), threshold=3),
            proposed_memory_text="Observed budget overshoot frequency candidate",
            payload={
                "budget_day_count": len(budgets),
                "overshoot_day_count": len(overshoots),
                "overshoot_frequency": len(overshoots) / len(budgets),
            },
            reason_codes=["l2a_overshoot_frequency"],
            intended_consumers=["calibration", "proactive", "rescue_later"],
        )
    ]


def _calibration_candidates(
    user_id: str,
    diagnostics: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not diagnostics:
        return []
    trace_ids = [_trace_id(diagnostic) for diagnostic in diagnostics]
    return [
        _candidate(
            candidate_id="pattern-calibration-mismatch-trend",
            candidate_type="pattern",
            user_id=user_id,
            source_trace_ids=trace_ids,
            source_object_refs=[
                _source_ref(
                    diagnostic,
                    trace_refs,
                    fallback_kind="CalibrationDiagnostic",
                    fallback_id_key="trace_id",
                )
                for diagnostic in diagnostics
            ],
            evidence_count=len(diagnostics),
            observed_at=[
                value
                for value in (
                    _parse_date_as_datetime(diagnostic.get("window_end"))
                    for diagnostic in diagnostics
                )
                if value is not None
            ],
            confidence=_confidence(len(diagnostics), threshold=3),
            proposed_memory_text="Observed calibration mismatch trend candidate",
            payload={"diagnostics": diagnostics},
            reason_codes=["l2a_calibration_mismatch_trend"],
            intended_consumers=["calibration", "intake_risk_tagging"],
        )
    ]
