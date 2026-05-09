from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.composition.dogfood_review_queue import (
    build_dogfood_review_queue_artifact,
    read_desktop_feedback_records,
)

DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH = Path("artifacts/accurate_intake_dogfood_review_queue.json")


def _read_existing_review_queue(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _merge_feedback_records(
    existing_records: list[dict[str, Any]],
    live_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for record in [*existing_records, *live_records]:
        key = str(record.get("feedback_id") or len(merged))
        merged[key] = record
    return list(merged.values())


def build_desktop_review_queue_response(
    *,
    feedback_dir: Path,
    review_queue_artifact_path: Path = DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH,
) -> dict[str, Any]:
    records, jsonl_path = read_desktop_feedback_records(feedback_dir=feedback_dir)
    existing = _read_existing_review_queue(review_queue_artifact_path)
    artifact = build_dogfood_review_queue_artifact(
        review_candidates=_dict_items(existing.get("review_candidates")),
        correction_feedback_events=_dict_items(existing.get("correction_feedback_events")),
        desktop_feedback_records=_merge_feedback_records(
            _dict_items(existing.get("desktop_feedback_records")),
            records,
        ),
    )
    return {
        **artifact,
        "source_feedback_store_path": str(jsonl_path),
        "source_feedback_store_exists": jsonl_path.exists(),
        "source_review_queue_artifact_path": str(review_queue_artifact_path),
        "source_review_queue_artifact_exists": review_queue_artifact_path.exists(),
        "frontend_semantic_owner": False,
        "manager_context_injection_allowed": False,
        "food_kb_truth_update_allowed": False,
        "canonical_eval_promotion_allowed": False,
        "product_truth_update_allowed": False,
    }


__all__ = [
    "DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH",
    "build_desktop_review_queue_response",
]
