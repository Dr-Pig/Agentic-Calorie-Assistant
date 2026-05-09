from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.application.proactive_summary_consumer import (  # noqa: E402
    build_proactive_no_send_summary_consumer_projection,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the proactive no-send summary-consumer projection artifact."
    )
    parser.add_argument("--memory-summary-projection", required=True, type=Path)
    parser.add_argument("--recommendation-quality-report", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    recommendation_quality_report = (
        read_json_artifact(args.recommendation_quality_report)
        if args.recommendation_quality_report
        else None
    )
    projection = build_proactive_no_send_summary_consumer_projection(
        read_json_artifact(args.memory_summary_projection),
        recommendation_quality_report=recommendation_quality_report,
    )
    write_json_artifact(args.output, projection)
    print(json.dumps(projection, ensure_ascii=False))
    return 0 if projection["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
