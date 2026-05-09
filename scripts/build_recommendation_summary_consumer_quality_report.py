from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.recommendation.application.summary_consumer_quality import (  # noqa: E402
    build_recommendation_shadow_summary_consumer_quality_report,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the recommendation shadow summary-consumer quality report."
    )
    parser.add_argument("--memory-summary-projection", required=True, type=Path)
    parser.add_argument("--prepared-candidates-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    prepared_candidates = _prepared_candidates(
        json.loads(args.prepared_candidates_json.read_text(encoding="utf-8"))
    )
    report = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=read_json_artifact(args.memory_summary_projection),
        prepared_candidates=prepared_candidates,
    )
    write_json_artifact(args.output, report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


def _prepared_candidates(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("prepared_candidates_json.must_be_list")
    return [item for item in value if isinstance(item, dict)]


if __name__ == "__main__":
    raise SystemExit(main())
