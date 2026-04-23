from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.logging import REQUEST_TRACE_DIR
from app.runtime.infrastructure.trace.trace_triage import build_live_trace_triage


def _latest_trace_paths(limit: int) -> list[Path]:
    return sorted(REQUEST_TRACE_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build live trace triage summaries from request artifacts.")
    parser.add_argument("--request-id", help="Specific request id to triage.")
    parser.add_argument("--latest", type=int, default=1, help="Number of latest traces to triage when request id is omitted.")
    args = parser.parse_args()

    if args.request_id:
        paths = [REQUEST_TRACE_DIR / f"{args.request_id}.json"]
    else:
        paths = _latest_trace_paths(max(args.latest, 1))

    results = []
    for path in paths:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        triage = build_live_trace_triage(data)
        results.append(
            {
                "request_id": path.stem,
                "timestamp": data.get("timestamp"),
                "triage": triage,
            }
        )

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
