from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.three_node_shadow_policy import (
    candidates as fixture_candidates,
)


def recommendation_source_candidates(
    *,
    payload: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return _deduped_candidates(
        [
            *_fixture_source_candidates(payload),
            *_memory_source_candidates(memory_context_pack),
        ]
    )


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
                "estimated_kcal": kcal,
                "estimated_kcal_range": {
                    "min": max(kcal - 80, 0),
                    "max": kcal,
                },
                "evidence_posture": "exact",
                "availability_posture": "available",
                "realistic_executable": True,
                "user_accessible": True,
                "item_patterns": items,
                "hard_avoid_flags": [],
                "source_refs": [f"memory_candidate:{record_id}"],
                "memory_record_id": record_id,
            }
        )
    return candidates


def _deduped_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id or candidate_id in seen:
            continue
        seen.add(candidate_id)
        deduped.append(candidate)
    return deduped


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


__all__ = ["recommendation_source_candidates"]
