from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.recommendation.application.read_only_stage_promotion import (  # noqa: E402
    build_recommendation_read_only_stage_promotion_decision,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the recommendation read-only runtime stage decision."
    )
    parser.add_argument("--recommendation-preflight-json", required=True, type=Path)
    parser.add_argument("--review-decision-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    artifact = build_recommendation_read_only_stage_promotion_decision(
        recommendation_preflight_report=read_json_artifact(
            args.recommendation_preflight_json
        ),
        human_review_decision=read_json_artifact(args.review_decision_json),
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False))
    return 0 if artifact["status"] == "approved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
