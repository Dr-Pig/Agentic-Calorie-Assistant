from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.composition.dogfood_review_queue import build_dogfood_review_queue_artifact

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEEDBACK_JSONL_PATH = Path("workspace_data/local_dogfood_feedback/accurate_intake_dogfood_feedback.jsonl")
DEFAULT_REVIEW_QUEUE_ARTIFACT_PATH = Path("artifacts/accurate_intake_dogfood_review_queue.json")


def _resolved_path(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def _count_jsonl_records(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _read_json_object(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _read_jsonl_objects(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(dict(payload))
    return records


def _copy_sidecar_if_present(*, source_path: Path, export_dir: Path, filename: str) -> str | None:
    if not source_path.exists():
        return None
    copy_path = export_dir / filename
    copy_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, copy_path)
    return str(copy_path)


def _materialize_review_queue_sidecar_from_feedback(
    *,
    feedback_path: Path,
    export_dir: Path,
    filename: str,
) -> tuple[str | None, dict]:
    feedback_records = _read_jsonl_objects(feedback_path)
    if not feedback_records:
        return None, {}
    payload = build_dogfood_review_queue_artifact(
        review_candidates=[],
        desktop_feedback_records=feedback_records,
    )
    copy_path = export_dir / filename
    copy_path.parent.mkdir(parents=True, exist_ok=True)
    copy_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(copy_path), payload


def build_export_sidecar_evidence_manifest(
    *,
    export_dir: Path,
    feedback_jsonl_path: Path | None = None,
    review_queue_artifact_path: Path | None = None,
) -> dict:
    feedback_path = feedback_jsonl_path or DEFAULT_FEEDBACK_JSONL_PATH
    review_path = review_queue_artifact_path or DEFAULT_REVIEW_QUEUE_ARTIFACT_PATH
    resolved_feedback = _resolved_path(feedback_path)
    resolved_review = _resolved_path(review_path)
    review_payload = _read_json_object(resolved_review)
    feedback_copy = _copy_sidecar_if_present(
        source_path=resolved_feedback,
        export_dir=export_dir,
        filename="accurate_intake_dogfood_feedback.jsonl",
    )
    review_copy = _copy_sidecar_if_present(
        source_path=resolved_review,
        export_dir=export_dir,
        filename="accurate_intake_dogfood_review_queue.json",
    )
    review_materialized_from_feedback = False
    if review_copy is None:
        review_copy, materialized_review_payload = _materialize_review_queue_sidecar_from_feedback(
            feedback_path=resolved_feedback,
            export_dir=export_dir,
            filename="accurate_intake_dogfood_review_queue.json",
        )
        if review_copy is not None:
            review_payload = materialized_review_payload
            review_materialized_from_feedback = True
    return {
        "feedback_jsonl": {
            "exists": resolved_feedback.exists(),
            "source_path": str(feedback_path),
            "copy_path": feedback_copy,
            "copied": feedback_copy is not None,
            "record_count": _count_jsonl_records(resolved_feedback),
        },
        "review_queue": {
            "exists": resolved_review.exists(),
            "source_path": str(review_path),
            "copy_path": review_copy,
            "copied": review_copy is not None,
            "materialized_from_feedback_jsonl": review_materialized_from_feedback,
            "feedback_triage_record_count": int(review_payload.get("feedback_triage_record_count") or 0),
            "review_candidate_count": int(review_payload.get("review_candidate_count") or 0),
        },
    }
