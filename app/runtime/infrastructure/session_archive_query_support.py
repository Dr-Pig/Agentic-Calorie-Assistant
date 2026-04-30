from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.shared.domain import MealRecord, RetrievedContextChunk, SessionTranscriptRecord
from app.shared.time_labels import DEFAULT_TIMEZONE, describe_time_fields, infer_relative_date_target


def safe_session_id(session_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", session_id).strip("._-") or "default"


def session_dir(session_record_root: Path, session_id: str) -> Path:
    return session_record_root / safe_session_id(session_id)


def transcript_path(session_record_root: Path, session_id: str) -> Path:
    return session_dir(session_record_root, session_id) / "transcript.jsonl"


def meal_path(session_record_root: Path, session_id: str) -> Path:
    return session_dir(session_record_root, session_id) / "meal_records.jsonl"


def json_default(value: object) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [token for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", normalized) if len(token) > 1]


def infer_meal_type(text: str) -> str:
    normalized = normalize_text(text)
    if any(token in normalized for token in ("早餐", "早飯", "breakfast")):
        return "breakfast"
    if any(token in normalized for token in ("午餐", "午飯", "lunch")):
        return "lunch"
    if any(token in normalized for token in ("晚餐", "晚飯", "dinner")):
        return "dinner"
    if any(token in normalized for token in ("點心", "零食", "snack")):
        return "snack"
    return "unknown"


def extract_brand_tokens(text: str) -> list[str]:
    normalized = normalize_text(text)
    brand_hints = [
        "7-11",
        "全家",
        "familymart",
        "mos",
        "摩斯",
        "starbucks",
        "星巴克",
        "mcdonald",
        "麥當勞",
        "subway",
        "爭鮮",
    ]
    return [brand for brand in brand_hints if brand.lower() in normalized]


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def time_decay_seconds(age_seconds: float) -> float:
    hours = max(age_seconds, 0.0) / 3600.0
    return 1.0 / (1.0 + hours)


def mmr_select(
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
        selected_terms = [set(item.matched_terms) | set(tokenize(item.content)) for item in selected]
        for item in remaining:
            item_terms = set(item.matched_terms) | set(tokenize(item.content))
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


def enrich_meal_records(*, session_id: str, meal_records: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    enriched_meal_records: list[dict[str, object]] = []
    for record in meal_records:
        payload = dict(record)
        time_fields = describe_time_fields(
            str(payload.get("occurred_at_utc") or payload.get("timestamp") or ""),
            timezone_name=str(payload.get("timezone") or DEFAULT_TIMEZONE),
        )
        payload.setdefault("created_at_utc", str(payload.get("timestamp") or time_fields.get("occurred_at_utc") or ""))
        payload.setdefault("updated_at_utc", str(payload.get("timestamp") or time_fields.get("occurred_at_utc") or ""))
        payload.setdefault("occurred_at_utc", time_fields.get("occurred_at_utc"))
        payload.setdefault("occurred_at_local", time_fields.get("occurred_at_local"))
        payload.setdefault("local_date", time_fields.get("local_date"))
        payload.setdefault("timezone", time_fields.get("timezone"))
        payload.setdefault("relative_time_label", time_fields.get("relative_time_label"))
        payload.setdefault(
            "meal_type",
            infer_meal_type(" ".join([str(payload.get("title") or ""), str(payload.get("raw_input") or "")])),
        )
        payload.setdefault("normalized_user_input", str(payload.get("raw_input") or ""))
        payload.setdefault(
            "resolved_food_items",
            [
                str(component.get("name") or "")
                for component in payload.get("components", [])
                if isinstance(component, dict) and str(component.get("name") or "").strip()
            ],
        )
        payload.setdefault("component_breakdown", list(payload.get("components") or []))
        payload.setdefault("followup_status", "open" if payload.get("pending_question") else "closed")
        payload.setdefault("missing_slots", [str(payload.get("pending_question"))] if payload.get("pending_question") else [])
        payload.setdefault("conversation_id", session_id)
        payload.setdefault("user_id", session_id)
        payload.setdefault("correction_parent_meal_id", payload.get("parent_log_id"))
        enriched_meal_records.append(payload)
    return enriched_meal_records


def load_jsonl_records(path: Path, model_cls: type[SessionTranscriptRecord] | type[MealRecord]) -> list[SessionTranscriptRecord] | list[MealRecord]:
    if not path.exists():
        return []
    records: list[SessionTranscriptRecord] | list[MealRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(model_cls(**json.loads(line)))  # type: ignore[arg-type]
        except Exception:
            continue
    return records


def query_context_requirements(query: str, *, now: datetime) -> tuple[set[str], str | None, str, list[str]]:
    query_terms = set(tokenize(query))
    relative_date_target = infer_relative_date_target(query, timezone_name=DEFAULT_TIMEZONE, now_utc=now)
    requested_meal_type = infer_meal_type(query)
    requested_brands = extract_brand_tokens(query)
    return query_terms, relative_date_target, requested_meal_type, requested_brands
