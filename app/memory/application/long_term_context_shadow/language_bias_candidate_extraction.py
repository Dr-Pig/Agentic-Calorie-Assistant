from __future__ import annotations

from collections import Counter
from typing import Any

from app.memory.application.long_term_context_shadow.candidate_records import _candidate
from app.memory.application.long_term_context_shadow.utils import (
    _bounded_confidence,
    _confidence,
    _dedupe,
    _most_common,
    _parse_datetime,
    _slug,
    _source_ref,
    _trace_id,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _language_candidates(
    user_id: str,
    observations: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    candidates: list[LongTermContextCandidate] = []
    for observation in observations:
        phrase = str(observation.get("user_phrase") or "unknown_phrase")
        observed_at = _parse_datetime(observation.get("observed_at"))
        candidates.append(
            _candidate(
                candidate_id=f"user-language-{_slug(phrase)}",
                candidate_type="user_language_pattern",
                user_id=user_id,
                source_trace_ids=[_trace_id(observation)],
                source_object_refs=[
                    _source_ref(
                        observation,
                        trace_refs,
                        fallback_kind="UserLanguageObservation",
                        fallback_id_key="trace_id",
                    )
                ],
                evidence_count=1,
                observed_at=[observed_at] if observed_at else [],
                confidence=_bounded_confidence(
                    observation.get("confidence"), default=0.4
                ),
                proposed_memory_text=f'Candidate user-language meaning: "{phrase}"',
                payload={
                    "user_phrase": phrase,
                    "observed_meaning": observation.get("observed_meaning"),
                    "pattern_subtype": str(
                        observation.get("phrase_kind") or "semantic_alias"
                    ),
                    "portion_semantics": observation.get("portion_semantics") or {},
                },
                reason_codes=["user_language_semantic_alias_candidate"],
                intended_consumers=[
                    "intake_clarification",
                    "chat_context",
                    "recommendation",
                ],
            )
        )
    return candidates


def _intake_estimation_bias_candidates(
    user_id: str,
    events: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not events:
        return []
    directions: Counter[str] = Counter(
        str(event.get("bias_direction") or "unknown") for event in events
    )
    direction, count = _most_common(directions)
    observed_at = [_parse_datetime(event.get("observed_at")) for event in events]
    missed_item_patterns = _dedupe(
        [
            str(event.get("missed_item_kind"))
            for event in events
            if event.get("missed_item_kind")
        ]
    )
    correction_tendencies = _dedupe(
        [
            str(event.get("correction_tendency"))
            for event in events
            if event.get("correction_tendency")
        ]
    )
    evidence_subtypes = _dedupe(
        [
            *(
                str(event.get("event_kind"))
                for event in events
                if event.get("event_kind")
            ),
            *(["correction_tendency"] if correction_tendencies else []),
        ]
    )
    return [
        _candidate(
            candidate_id=f"intake-estimation-bias-{_slug(direction)}",
            candidate_type="intake_estimation_bias",
            user_id=user_id,
            source_trace_ids=[_trace_id(event) for event in events],
            source_object_refs=[
                _source_ref(
                    event,
                    trace_refs,
                    fallback_kind="IntakeEstimationBiasObservation",
                    fallback_id_key="trace_id",
                )
                for event in events
            ],
            evidence_count=len(events),
            observed_at=[value for value in observed_at if value is not None],
            confidence=_confidence(count, threshold=3),
            proposed_memory_text=f"Candidate intake estimation bias posture: {direction}",
            payload={
                "bias_direction": direction,
                "events": events,
                "evidence_subtypes": evidence_subtypes,
                "missed_item_patterns": missed_item_patterns,
                "correction_tendencies": correction_tendencies,
            },
            reason_codes=["intake_estimation_bias_candidate"],
            intended_consumers=[
                "calibration",
                "intake_risk_tagging",
                "nutrition_clarify_priority",
                "response_context",
            ],
        )
    ]


def _conversation_recall_context_candidates(
    user_id: str,
    summaries: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not summaries:
        return []
    observed_at = [_parse_datetime(summary.get("observed_at")) for summary in summaries]
    return [
        _candidate(
            candidate_id="conversation-recall-context-summary",
            candidate_type="conversation_recall_context",
            user_id=user_id,
            source_trace_ids=[_trace_id(summary) for summary in summaries],
            source_object_refs=[
                _source_ref(
                    summary,
                    trace_refs,
                    fallback_kind="ConversationArchive",
                    fallback_id_key="conversation_id",
                )
                for summary in summaries
            ],
            evidence_count=len(summaries),
            observed_at=[value for value in observed_at if value is not None],
            confidence=_confidence(len(summaries), threshold=3),
            proposed_memory_text="Candidate conversation recall context from summary-first archive",
            payload={
                "summary_first": True,
                "raw_transcript_included": False,
                "manager_tool_call_allowed": False,
                "retrieval_tool_allowed_later": True,
                "conversation_summaries": summaries,
            },
            reason_codes=["conversation_history_retrieval_context_candidate"],
            intended_consumers=[
                "chat_context",
                "intake_clarification",
                "recommendation",
                "calibration",
            ],
        )
    ]
