from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.three_node_shadow_policy import (
    candidates as fixture_candidates,
    filter_reason_codes,
)


def build_candidate_retrieval_guard_scoring(
    *,
    planning: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _mapping(fixture_inputs.get("recommendation_payload"))
    source_candidates = [
        *_fixture_source_candidates(payload),
        *_memory_source_candidates(memory_context_pack),
    ]
    allowed: list[dict[str, Any]] = []
    filtered: list[dict[str, Any]] = []
    for candidate in source_candidates:
        reasons = filter_reason_codes(candidate, payload)
        if reasons:
            filtered.append(
                {
                    "candidate_id": str(candidate.get("candidate_id") or ""),
                    "reason_codes": reasons,
                }
            )
            continue
        scored = {**candidate, "quality_score": _quality_score(candidate, payload)}
        allowed.append(scored)
    allowed.sort(key=_sort_key)
    return {
        "node": "candidate_retrieval_guard_scoring",
        "owner": "deterministic",
        "deterministic_guard_only": True,
        "source_candidate_ids": [
            str(candidate.get("candidate_id") or "") for candidate in source_candidates
        ],
        "allowed_candidate_ids": [
            str(candidate.get("candidate_id") or "") for candidate in allowed
        ],
        "allowed_candidates": allowed,
        "filtered_candidates": filtered,
        "quality_signals": [
            _quality_signal(candidate) for candidate in allowed
        ],
        "candidate_spec_obeyed": bool(planning.get("candidate_spec")),
        "blockers": [],
    }


def _fixture_source_candidates(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(candidate) for candidate in fixture_candidates(payload)]


def _memory_source_candidates(
    memory_context_pack: Mapping[str, Any],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for entry in memory_context_pack.get("entries") or []:
        if not isinstance(entry, Mapping) or entry.get("memory_type") != "golden_order":
            continue
        kcal = _int_or_none(entry.get("estimated_kcal")) or 0
        record_id = str(entry.get("record_id") or "")
        items = [str(item) for item in entry.get("item_names") or [] if str(item)]
        store_name = str(entry.get("store_name") or "Remembered option")
        title = " ".join([store_name, *items]).strip()
        candidates.append(
            {
                "candidate_id": record_id,
                "title": title or str(entry.get("summary") or record_id),
                "source_type": "memory_golden_order",
                "estimated_kcal_range": {
                    "min": max(kcal - 80, 0),
                    "max": kcal,
                },
                "item_patterns": items,
                "hard_avoid_flags": [],
                "source_refs": [f"memory_candidate:{record_id}"],
                "memory_record_id": record_id,
            }
        )
    return candidates


def _quality_score(candidate: Mapping[str, Any], payload: Mapping[str, Any]) -> int:
    score = 50
    source_type = str(candidate.get("source_type") or "")
    if source_type == "memory_golden_order":
        score += 50
    elif source_type == "golden_order":
        score += 25
    if candidate.get("evidence_posture") == "exact":
        score += 8
    if candidate.get("realistic_executable") is True:
        score += 5
    if candidate.get("user_accessible") is True:
        score += 5
    remaining = _remaining_kcal(payload)
    kcal_max = _int_or_none(_mapping(candidate.get("estimated_kcal_range")).get("max"))
    if remaining is not None and kcal_max is not None:
        score += max(min((remaining - kcal_max) // 50, 10), -10)
    return int(score)


def _quality_signal(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "quality_score": int(candidate.get("quality_score") or 0),
        "source_type": str(candidate.get("source_type") or ""),
        "source_refs": [str(ref) for ref in candidate.get("source_refs") or []],
    }


def _sort_key(candidate: Mapping[str, Any]) -> tuple[int, int, str]:
    source_priority = 1 if candidate.get("source_type") == "memory_golden_order" else 0
    return (
        -int(candidate.get("quality_score") or 0),
        -source_priority,
        str(candidate.get("candidate_id") or ""),
    )


def _remaining_kcal(payload: Mapping[str, Any]) -> int | None:
    return _int_or_none(_mapping(payload.get("current_budget_view")).get("remaining_kcal"))


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_candidate_retrieval_guard_scoring"]
