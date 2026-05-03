from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.dogfood_review_queue import (  # noqa: E402
    build_dogfood_review_queue_artifact,
    build_review_candidate_from_runtime_trace,
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local-only Accurate Intake dogfood review queue artifact."
    )
    parser.add_argument(
        "--trace-json",
        action="append",
        default=[],
        help="Runtime turn trace JSON file. May be passed more than once.",
    )
    parser.add_argument(
        "--correction-event-json",
        action="append",
        default=[],
        help="User correction feedback event JSON file. May be passed more than once.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_dogfood_review_queue.json",
        help="Output artifact path.",
    )
    args = parser.parse_args(argv)

    review_candidates = [
        build_review_candidate_from_runtime_trace(_read_json(Path(path)))
        for path in args.trace_json
    ]
    correction_feedback_events = [
        _read_json(Path(path))
        for path in args.correction_event_json
    ]
    artifact = build_dogfood_review_queue_artifact(
        review_candidates=review_candidates,
        correction_feedback_events=correction_feedback_events,
    )
    _write_json(Path(args.output), artifact)
    print(json.dumps({"artifact": args.output, "status": artifact["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
