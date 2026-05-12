from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.memory_feedback_contract import (
    NON_MUTATION_FLAGS,
    validate_memory_record_contract,
)


BLOCK_SCORE = -1000
DOWNRANK_SCORE = -100
BOOST_SCORE = 50


def evaluate_preference_memory_policy(
    *,
    memory_records: list[Mapping[str, Any]],
    candidates: list[Mapping[str, Any]],
) -> dict[str, Any]:
    record_blockers = _record_blockers(memory_records)
    candidate_blockers = _candidate_blockers(candidates)
    blockers = record_blockers + candidate_blockers
    if blockers:
        return _artifact(status="blocked", blockers=blockers, candidate_evaluations=[])

    evaluations = [
        _evaluate_candidate(candidate, memory_records) for candidate in candidates
    ]
    return _artifact(status="pass", blockers=[], candidate_evaluations=evaluations)


def _evaluate_candidate(
    candidate: Mapping[str, Any], memory_records: list[Mapping[str, Any]]
) -> dict[str, Any]:
    candidate_subjects = set(_subject_keys(candidate))
    blocked_by: list[str] = []
    downranked_by: list[str] = []
    boosted_by: list[str] = []

    for record in memory_records:
        if not candidate_subjects.intersection(_subject_keys(record)):
            continue
        polarity = str(record.get("polarity") or "")
        strength = str(record.get("strength") or "")
        record_id = str(record.get("id") or "")
        if polarity == "negative" and strength == "block":
            blocked_by.append(record_id)
        elif polarity == "negative" and strength == "downrank":
            downranked_by.append(record_id)
        elif polarity == "positive" and strength == "boost":
            boosted_by.append(record_id)

    blocked = bool(blocked_by)
    score_adjustment = len(downranked_by) * DOWNRANK_SCORE
    if blocked:
        score_adjustment += BLOCK_SCORE
    else:
        score_adjustment += len(boosted_by) * BOOST_SCORE

    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "blocked": blocked,
        "blocked_by": blocked_by,
        "downranked_by": downranked_by,
        "boosted_by": boosted_by if not blocked else [],
        "boost_suppressed_by_negative": blocked and bool(boosted_by),
        "score_adjustment": score_adjustment,
        "allowed_after_memory_policy": not blocked,
    }


def _record_blockers(records: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for record in records:
        record_id = str(record.get("id") or "memory_record")
        validation = validate_memory_record_contract(record)
        blockers.extend(f"{record_id}.{item}" for item in validation["blockers"])
        if not _subject_keys(record):
            blockers.append(f"{record_id}.subject_keys.missing")
    return blockers


def _candidate_blockers(candidates: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "candidate")
        if not candidate.get("candidate_id"):
            blockers.append("candidate_id.missing")
        if not _subject_keys(candidate):
            blockers.append(f"{candidate_id}.subject_keys.missing")
        if not _source_refs(candidate):
            blockers.append(f"{candidate_id}.source_refs.missing")
    return blockers


def _subject_keys(payload: Mapping[str, Any]) -> list[str]:
    keys = payload.get("subject_keys")
    if not isinstance(keys, list):
        return []
    return [str(item) for item in keys if str(item)]


def _source_refs(payload: Mapping[str, Any]) -> list[str]:
    refs = payload.get("source_refs")
    if not isinstance(refs, list):
        return []
    return [str(item) for item in refs if str(item)]


def _artifact(
    *, status: str, blockers: list[str], candidate_evaluations: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "artifact_type": "memory_preference_policy_evaluation",
        "status": status,
        "blockers": blockers,
        "candidate_evaluations": candidate_evaluations,
        "semantic_inference_used": False,
        **NON_MUTATION_FLAGS,
    }


__all__ = [
    "BOOST_SCORE",
    "BLOCK_SCORE",
    "DOWNRANK_SCORE",
    "evaluate_preference_memory_policy",
]
