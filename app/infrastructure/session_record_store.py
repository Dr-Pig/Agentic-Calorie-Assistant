from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ..domain import MealRecord, RetrievedContextChunk, SessionTranscriptRecord
from ..paths import SESSION_RECORD_DIR, ensure_runtime_dirs


ensure_runtime_dirs()

SESSION_RECORD_ROOT = Path(os.getenv("SESSION_RECORD_ROOT", SESSION_RECORD_DIR))


def _safe_session_id(session_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", session_id).strip("._-") or "default"


def _session_dir(session_id: str) -> Path:
    return SESSION_RECORD_ROOT / _safe_session_id(session_id)


def _transcript_path(session_id: str) -> Path:
    return _session_dir(session_id) / "transcript.jsonl"


def _meal_path(session_id: str) -> Path:
    return _session_dir(session_id) / "meal_records.jsonl"


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def _tokenize(text: str) -> list[str]:
    normalized = _normalize_text(text)
    return [token for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", normalized) if len(token) > 1]


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _time_decay_seconds(age_seconds: float) -> float:
    hours = max(age_seconds, 0.0) / 3600.0
    return 1.0 / (1.0 + hours)


def _mmr_select(
    candidates: list[RetrievedContextChunk],
    *,
    limit: int,
    lambda_weight: float = 0.72,
) -> list[RetrievedContextChunk]:
    selected: list[RetrievedContextChunk] = []
    remaining = list(candidates)
    while remaining and len(selected) < limit:
        if not selected:
            remaining.sort(key=lambda item: item.score, reverse=True)
            selected.append(remaining.pop(0))
            continue
        best_item: RetrievedContextChunk | None = None
        best_score = -10**9
        selected_terms = [set(item.matched_terms) | set(_tokenize(item.content)) for item in selected]
        for item in remaining:
            item_terms = set(item.matched_terms) | set(_tokenize(item.content))
            similarity = 0.0
            for prior_terms in selected_terms:
                union = item_terms.union(prior_terms)
                if not union:
                    continue
                similarity = max(similarity, len(item_terms.intersection(prior_terms)) / len(union))
            mmr_score = lambda_weight * item.score - (1.0 - lambda_weight) * similarity
            if mmr_score > best_score:
                best_score = mmr_score
                best_item = item
        if best_item is None:
            break
        selected.append(best_item)
        remaining = [item for item in remaining if item.chunk_id != best_item.chunk_id]
    return selected


def sync_session_records(
    *,
    session_id: str,
    transcript_records: Iterable[dict[str, object]],
    meal_records: Iterable[dict[str, object]],
) -> None:
    session_dir = _session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    transcript_lines = [
        json.dumps(record, ensure_ascii=False, default=_json_default)
        for record in transcript_records
    ]
    _transcript_path(session_id).write_text("\n".join(transcript_lines) + ("\n" if transcript_lines else ""), encoding="utf-8")

    meal_lines = [
        json.dumps(record, ensure_ascii=False, default=_json_default)
        for record in meal_records
    ]
    _meal_path(session_id).write_text("\n".join(meal_lines) + ("\n" if meal_lines else ""), encoding="utf-8")


def load_transcript_records(session_id: str) -> list[SessionTranscriptRecord]:
    path = _transcript_path(session_id)
    if not path.exists():
        return []
    records: list[SessionTranscriptRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(SessionTranscriptRecord(**json.loads(line)))
        except Exception:
            continue
    return records


def load_meal_records(session_id: str) -> list[MealRecord]:
    path = _meal_path(session_id)
    if not path.exists():
        return []
    records: list[MealRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(MealRecord(**json.loads(line)))
        except Exception:
            continue
    return records


def retrieve_planner_context(
    *,
    session_id: str,
    query: str,
    active_meal_id: int | None,
    pending_question: str | None,
    limit_transcript: int = 4,
    limit_meals: int = 3,
    historical_limit: int = 2,
) -> tuple[list[RetrievedContextChunk], list[RetrievedContextChunk], float | None, dict[str, object]]:
    transcript_records = load_transcript_records(session_id)
    meal_records = load_meal_records(session_id)
    now = datetime.now(timezone.utc)
    query_terms = set(_tokenize(query))
    pending_terms = set(_tokenize(pending_question or ""))

    active_meal = next((record for record in meal_records if active_meal_id and record.meal_id == active_meal_id), None)
    active_time_gap_seconds: float | None = None
    if active_meal and active_meal.timestamp:
        parsed_active = _parse_ts(active_meal.timestamp)
        if parsed_active is not None:
            active_time_gap_seconds = max((now - parsed_active).total_seconds(), 0.0)

    transcript_candidates: list[RetrievedContextChunk] = []
    for record in transcript_records:
        content_terms = set(_tokenize(record.content))
        lexical = len(query_terms.intersection(content_terms))
        pending_overlap = len(pending_terms.intersection(content_terms))
        score = lexical * 3.0 + pending_overlap * 2.0
        parsed_time = _parse_ts(record.timestamp)
        if parsed_time is not None:
            time_decay = _time_decay_seconds((now - parsed_time).total_seconds())
            score += time_decay
        else:
            time_decay = 0.0
        active_meal_boost = 0.0
        if record.linked_meal_id and active_meal_id and record.linked_meal_id == active_meal_id:
            active_meal_boost = 3.5
            score += active_meal_boost
        if score <= 0:
            continue
        transcript_candidates.append(
            RetrievedContextChunk(
                chunk_id=f"transcript:{record.turn_id}",
                source_type="transcript",
                source_id=record.turn_id,
                content=record.content,
                timestamp=record.timestamp,
                linked_meal_id=record.linked_meal_id,
                score=round(score, 4),
                matched_terms=sorted(query_terms.intersection(content_terms)),
                metadata={
                    "role": record.role,
                    "trace_id": record.trace_id,
                    "score_breakdown": {
                        "lexical_overlap": lexical * 3.0,
                        "pending_overlap": pending_overlap * 2.0,
                        "active_meal_boost": active_meal_boost,
                        "time_decay": round(time_decay, 4),
                        "final_score": round(score, 4),
                    },
                },
            )
        )

    meal_candidates: list[RetrievedContextChunk] = []
    for record in meal_records:
        text = " ".join(
            [
                record.title,
                record.raw_input,
                " ".join(str(component.get("name", "")) for component in record.components),
                record.pending_question or "",
                " ".join(record.resolved_slots),
            ]
        )
        content_terms = set(_tokenize(text))
        lexical = len(query_terms.intersection(content_terms))
        pending_overlap = len(pending_terms.intersection(content_terms))
        score = lexical * 3.0 + pending_overlap * 2.0
        active_meal_boost = 0.0
        if active_meal_id and record.meal_id == active_meal_id:
            active_meal_boost = 8.0
            score += active_meal_boost
        unresolved_boost = 0.0
        if record.status in {"draft", "draft_unresolved", "candidate_meal", "completed", "completed_meal"} and record.pending_question:
            unresolved_boost = 2.0
            score += unresolved_boost
        parsed_time = _parse_ts(record.timestamp)
        if parsed_time is not None:
            time_decay = _time_decay_seconds((now - parsed_time).total_seconds()) * 2.0
            score += time_decay
        else:
            time_decay = 0.0
        if score <= 0:
            continue
        meal_candidates.append(
            RetrievedContextChunk(
                chunk_id=f"meal:{record.meal_id}",
                source_type="meal_record",
                source_id=record.meal_id,
                content=text.strip(),
                timestamp=record.timestamp,
                linked_meal_id=record.meal_id,
                score=round(score, 4),
                matched_terms=sorted(query_terms.intersection(content_terms)),
                metadata={
                    "title": record.title,
                    "status": record.status,
                    "pending_question": record.pending_question,
                    "score_breakdown": {
                        "lexical_overlap": lexical * 3.0,
                        "pending_overlap": pending_overlap * 2.0,
                        "active_meal_boost": active_meal_boost,
                        "unresolved_boost": unresolved_boost,
                        "time_decay": round(time_decay, 4),
                        "final_score": round(score, 4),
                    },
                },
            )
        )

    hard_meal_chunks = [
        item for item in meal_candidates
        if active_meal_id is not None and item.linked_meal_id == active_meal_id
    ][:1]
    remaining_meal = [item for item in meal_candidates if item.chunk_id not in {x.chunk_id for x in hard_meal_chunks}]
    remaining_meal.sort(key=lambda item: item.score, reverse=True)
    selected_meals = hard_meal_chunks + _mmr_select(remaining_meal, limit=max(limit_meals - len(hard_meal_chunks), 0))

    transcript_candidates.sort(key=lambda item: item.score, reverse=True)
    selected_transcript = _mmr_select(transcript_candidates, limit=limit_transcript)

    historical = [
        item
        for item in selected_meals
        if not (active_meal_id is not None and item.linked_meal_id == active_meal_id)
    ][:historical_limit]
    selected_meals = hard_meal_chunks + historical[: max(limit_meals - len(hard_meal_chunks), 0)]
    selected_transcript_ids = {item.chunk_id for item in selected_transcript}
    selected_meal_ids = {item.chunk_id for item in selected_meals}
    for item in transcript_candidates:
        item.metadata["mmr_selected"] = item.chunk_id in selected_transcript_ids
    for item in meal_candidates:
        item.metadata["mmr_selected"] = item.chunk_id in selected_meal_ids
        item.metadata["hard_included"] = item.chunk_id in {x.chunk_id for x in hard_meal_chunks}
    diagnostics = {
        "transcript_candidates": [
            item.model_dump(mode="json")
            for item in sorted(transcript_candidates, key=lambda chunk: chunk.score, reverse=True)[:8]
        ],
        "meal_candidates": [
            item.model_dump(mode="json")
            for item in sorted(meal_candidates, key=lambda chunk: chunk.score, reverse=True)[:8]
        ],
    }
    return selected_transcript, selected_meals, active_time_gap_seconds, diagnostics
