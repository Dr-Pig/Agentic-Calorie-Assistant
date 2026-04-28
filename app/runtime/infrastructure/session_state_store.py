from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.paths import SESSION_RECORD_DIR, ensure_runtime_dirs
from app.runtime.infrastructure.session_archive_query_support import (
    enrich_meal_records,
    json_default,
    load_jsonl_records,
    meal_path,
    mmr_select,
    parse_ts,
    query_context_requirements,
    session_dir,
    time_decay_seconds,
    tokenize,
    transcript_path,
)
from app.shared.domain import MealRecord, RetrievedContextChunk, SessionTranscriptRecord


ensure_runtime_dirs()

SESSION_RECORD_ROOT = Path(os.getenv("SESSION_RECORD_ROOT", SESSION_RECORD_DIR))


def sync_session_records(
    *,
    session_id: str,
    transcript_records: Iterable[dict[str, object]],
    meal_records: Iterable[dict[str, object]],
) -> None:
    target_session_dir = session_dir(SESSION_RECORD_ROOT, session_id)
    target_session_dir.mkdir(parents=True, exist_ok=True)

    transcript_lines = [
        json.dumps(record, ensure_ascii=False, default=json_default)
        for record in transcript_records
    ]
    transcript_path(SESSION_RECORD_ROOT, session_id).write_text(
        "\n".join(transcript_lines) + ("\n" if transcript_lines else ""),
        encoding="utf-8",
    )

    meal_lines = [
        json.dumps(record, ensure_ascii=False, default=json_default)
        for record in enrich_meal_records(session_id=session_id, meal_records=meal_records)
    ]
    meal_path(SESSION_RECORD_ROOT, session_id).write_text(
        "\n".join(meal_lines) + ("\n" if meal_lines else ""),
        encoding="utf-8",
    )


def load_transcript_records(session_id: str) -> list[SessionTranscriptRecord]:
    return load_jsonl_records(transcript_path(SESSION_RECORD_ROOT, session_id), SessionTranscriptRecord)  # type: ignore[return-value]


def load_meal_records(session_id: str) -> list[MealRecord]:
    return load_jsonl_records(meal_path(SESSION_RECORD_ROOT, session_id), MealRecord)  # type: ignore[return-value]


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
    query_terms, relative_date_target, requested_meal_type, requested_brands = query_context_requirements(query, now=now)
    pending_terms = set(tokenize(pending_question or ""))

    active_meal = next((record for record in meal_records if active_meal_id and record.meal_id == active_meal_id), None)
    active_meal_time_gap_seconds: float | None = None
    if active_meal and active_meal.timestamp:
        parsed_active = parse_ts(active_meal.timestamp)
        if parsed_active is not None:
            active_meal_time_gap_seconds = max((now - parsed_active).total_seconds(), 0.0)

    transcript_candidates: list[RetrievedContextChunk] = []
    for record in transcript_records:
        content_terms = set(tokenize(record.content))
        lexical = len(query_terms.intersection(content_terms))
        pending_overlap = len(pending_terms.intersection(content_terms))
        score = lexical * 3.0 + pending_overlap * 2.0
        parsed_time = parse_ts(record.timestamp)
        if parsed_time is not None:
            time_decay = time_decay_seconds((now - parsed_time).total_seconds())
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
                record.normalized_user_input or "",
                " ".join(record.resolved_food_items or []),
                " ".join(str(component.get("name", "")) for component in record.components),
                record.pending_question or "",
                " ".join(record.resolved_slots),
            ]
        )
        content_terms = set(tokenize(text))
        lexical = len(query_terms.intersection(content_terms))
        pending_overlap = len(pending_terms.intersection(content_terms))
        score = lexical * 3.0 + pending_overlap * 2.0
        hard_filter_boost = 0.0
        hard_filter_miss_penalty = 0.0
        if relative_date_target:
            if record.local_date == relative_date_target:
                hard_filter_boost += 4.0
            else:
                hard_filter_miss_penalty -= 2.0
        if requested_meal_type != "unknown":
            if record.meal_type == requested_meal_type:
                hard_filter_boost += 3.0
            else:
                hard_filter_miss_penalty -= 1.5
        if requested_brands:
            if any(brand.lower() in text.lower() for brand in requested_brands):
                hard_filter_boost += 2.5
            else:
                hard_filter_miss_penalty -= 1.0
        score += hard_filter_boost + hard_filter_miss_penalty
        active_meal_boost = 0.0
        if active_meal_id and record.meal_id == active_meal_id:
            active_meal_boost = 8.0
            score += active_meal_boost
        unresolved_boost = 0.0
        if record.status in {"draft", "draft_unresolved", "candidate_meal", "completed", "completed_meal"} and record.pending_question:
            unresolved_boost = 2.0
            score += unresolved_boost
        parsed_time = parse_ts(record.timestamp)
        if parsed_time is not None:
            time_decay = time_decay_seconds((now - parsed_time).total_seconds()) * 2.0
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
                        "hard_filter_boost": round(hard_filter_boost, 4),
                        "hard_filter_miss_penalty": round(hard_filter_miss_penalty, 4),
                        "active_meal_boost": active_meal_boost,
                        "unresolved_boost": unresolved_boost,
                        "time_decay": round(time_decay, 4),
                        "final_score": round(score, 4),
                    },
                    "router_filters": {
                        "relative_date_target": relative_date_target,
                        "requested_meal_type": requested_meal_type,
                        "requested_brands": requested_brands,
                    },
                },
            )
        )

    hard_meal_chunks = [
        item for item in meal_candidates if active_meal_id is not None and item.linked_meal_id == active_meal_id
    ][:1]
    remaining_meal = [item for item in meal_candidates if item.chunk_id not in {x.chunk_id for x in hard_meal_chunks}]
    remaining_meal.sort(key=lambda item: item.score, reverse=True)
    selected_meals = hard_meal_chunks + mmr_select(remaining_meal, limit=max(limit_meals - len(hard_meal_chunks), 0))

    transcript_candidates.sort(key=lambda item: item.score, reverse=True)
    selected_transcript = mmr_select(transcript_candidates, limit=limit_transcript)

    historical = [item for item in selected_meals if not (active_meal_id is not None and item.linked_meal_id == active_meal_id)][
        :historical_limit
    ]
    selected_meals = hard_meal_chunks + historical[: max(limit_meals - len(hard_meal_chunks), 0)]
    selected_transcript_ids = {item.chunk_id for item in selected_transcript}
    selected_meal_ids = {item.chunk_id for item in selected_meals}
    for item in transcript_candidates:
        item.metadata["mmr_selected"] = item.chunk_id in selected_transcript_ids
    for item in meal_candidates:
        item.metadata["mmr_selected"] = item.chunk_id in selected_meal_ids
        item.metadata["hard_included"] = item.chunk_id in {x.chunk_id for x in hard_meal_chunks}
    diagnostics = {
        "router_order": ["state_memory", "typed_meal_records", "transcript_hybrid"],
        "query_filters": {
            "relative_date_target": relative_date_target,
            "requested_meal_type": requested_meal_type,
            "requested_brands": requested_brands,
        },
        "active_meal_id": active_meal_id,
        "transcript_candidates": [
            item.model_dump(mode="json")
            for item in sorted(transcript_candidates, key=lambda chunk: chunk.score, reverse=True)[:8]
        ],
        "meal_candidates": [
            item.model_dump(mode="json")
            for item in sorted(meal_candidates, key=lambda chunk: chunk.score, reverse=True)[:8]
        ],
    }
    return selected_transcript, selected_meals, active_meal_time_gap_seconds, diagnostics
