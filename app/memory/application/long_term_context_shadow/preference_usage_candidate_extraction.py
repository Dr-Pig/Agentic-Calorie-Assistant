from __future__ import annotations

from collections import Counter
from typing import Any

from app.memory.application.long_term_context_shadow.candidate_records import _candidate
from app.memory.application.long_term_context_shadow.utils import (
    _bounded_confidence,
    _confidence,
    _most_common,
    _parse_datetime,
    _slug,
    _source_ref,
    _trace_id,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _app_usage_style_candidates(
    user_id: str,
    events: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not events:
        return []
    signals: Counter[str] = Counter(
        str(event.get("usage_signal") or "unknown") for event in events
    )
    observed_at = [_parse_datetime(event.get("observed_at")) for event in events]
    return [
        _candidate(
            candidate_id="app-usage-style-pattern",
            candidate_type="app_usage_style",
            user_id=user_id,
            source_trace_ids=[_trace_id(event) for event in events],
            source_object_refs=[
                _source_ref(
                    event,
                    trace_refs,
                    fallback_kind="AppUsageEvent",
                    fallback_id_key="trace_id",
                )
                for event in events
            ],
            evidence_count=len(events),
            observed_at=[value for value in observed_at if value is not None],
            confidence=_confidence(len(events), threshold=5),
            proposed_memory_text="Candidate app usage style pattern",
            payload={"usage_signal_distribution": dict(sorted(signals.items()))},
            reason_codes=["app_usage_style_candidate"],
            intended_consumers=[
                "chat_context",
                "proactive",
                "ux",
                "recommendation_presentation",
            ],
        )
    ]


def _interaction_preference_candidates(
    user_id: str,
    events: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not events:
        return []
    signals: Counter[str] = Counter(
        str(event.get("preference_signal") or "unknown") for event in events
    )
    signal, count = _most_common(signals)
    observed_at = [_parse_datetime(event.get("observed_at")) for event in events]
    return [
        _candidate(
            candidate_id=f"interaction-preference-{_slug(signal)}",
            candidate_type="interaction_preference",
            user_id=user_id,
            source_trace_ids=[_trace_id(event) for event in events],
            source_object_refs=[
                _source_ref(
                    event,
                    trace_refs,
                    fallback_kind="InteractionPreferenceEvent",
                    fallback_id_key="trace_id",
                )
                for event in events
            ],
            evidence_count=len(events),
            observed_at=[value for value in observed_at if value is not None],
            confidence=_confidence(count, threshold=3),
            proposed_memory_text=f"Candidate interaction preference: {signal}",
            payload={"preference_signal": signal, "events": events},
            reason_codes=["interaction_preference_candidate"],
            intended_consumers=[
                "response_generation",
                "chat_context",
                "proactive_message_style",
            ],
        )
    ]


def _negative_preference_candidates(
    user_id: str,
    observations: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    candidates: list[LongTermContextCandidate] = []
    for observation in observations:
        scope = str(observation.get("preference_scope") or "general")
        value = str(observation.get("value") or "unknown")
        observed_at = _parse_datetime(observation.get("observed_at"))
        candidates.append(
            _candidate(
                candidate_id=f"negative-preference-{_slug(scope)}-{_slug(value)}",
                candidate_type="negative_preference",
                user_id=user_id,
                source_trace_ids=[_trace_id(observation)],
                source_object_refs=[
                    _source_ref(
                        observation,
                        trace_refs,
                        fallback_kind="NegativePreferenceObservation",
                        fallback_id_key="trace_id",
                    )
                ],
                evidence_count=1,
                observed_at=[observed_at] if observed_at else [],
                confidence=_bounded_confidence(
                    observation.get("confidence"), default=0.5
                ),
                proposed_memory_text=f"Candidate negative preference: avoid {value}",
                payload={
                    "preference_scope": scope,
                    "value": value,
                    "source_signal": observation.get("source_signal"),
                    "confirmed": False,
                },
                reason_codes=["negative_preference_candidate"],
                intended_consumers=[
                    "recommendation",
                    "proactive",
                    "intake_clarification",
                ],
            )
        )
    return candidates


def _temporary_preference_candidates(
    user_id: str,
    observations: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    candidates: list[LongTermContextCandidate] = []
    for observation in observations:
        value = str(observation.get("value") or "unknown")
        observed_at = _parse_datetime(observation.get("observed_at"))
        valid_until = str(observation.get("valid_until") or "")
        candidates.append(
            _candidate(
                candidate_id=f"temporary-preference-{_slug(value)}",
                candidate_type="temporary_preference",
                user_id=user_id,
                source_trace_ids=[_trace_id(observation)],
                source_object_refs=[
                    _source_ref(
                        observation,
                        trace_refs,
                        fallback_kind="TemporaryPreferenceObservation",
                        fallback_id_key="trace_id",
                    )
                ],
                evidence_count=1,
                observed_at=[observed_at] if observed_at else [],
                confidence=_bounded_confidence(
                    observation.get("confidence"), default=0.5
                ),
                proposed_memory_text=(
                    f"Candidate temporary preference through {valid_until}: {value}"
                ),
                payload={
                    "preference_type": observation.get("preference_type"),
                    "value": value,
                    "context_scope": observation.get("context_scope"),
                    "valid_from": observation.get("valid_from"),
                    "valid_until": observation.get("valid_until"),
                    "confirmed": False,
                },
                reason_codes=["temporary_preference_candidate"],
                intended_consumers=[
                    "recommendation",
                    "chat_context",
                    "proactive",
                    "intake_clarification",
                ],
            )
        )
    return candidates
