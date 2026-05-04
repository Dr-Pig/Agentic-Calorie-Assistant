from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.recommendation.application.shadow_scorecard import (  # noqa: E402
    build_recommendation_shadow_scorecard,
)
from app.recommendation.application.shadow_artifact_gate import (  # noqa: E402
    evaluate_recommendation_shadow_artifact_payload,
)
from app.recommendation.domain.shadow import (  # noqa: E402
    RecommendationShadowEvalArtifact,
    RecommendationShadowScorecard,
)


DEFAULT_ARTIFACT = ROOT / "artifacts" / "recommendation_shadow_eval.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "recommendation_shadow_scorecard.json"


def build_recommendation_shadow_scorecard_from_file(
    artifact_path: Path = DEFAULT_ARTIFACT,
    output_path: Path = DEFAULT_OUTPUT,
) -> Path:
    payload = json.loads(artifact_path.read_text(encoding="utf-8-sig"))
    gate_result = evaluate_recommendation_shadow_artifact_payload(payload)
    try:
        artifact = RecommendationShadowEvalArtifact.model_validate(payload)
    except ValueError:
        scorecard = RecommendationShadowScorecard(
            gate_passed=False,
            issue_codes=gate_result.failure_codes,
            summary={
                "scenario_count": 0,
                "failure_count": len(gate_result.failure_codes),
                "warning_count": len(gate_result.warning_codes),
                "payload_model_validation_failed": True,
            },
            scenario_scorecards=[],
        )
    else:
        scorecard = build_recommendation_shadow_scorecard(artifact, gate_result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(scorecard.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a reviewer-readable offline recommendation shadow scorecard."
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        default=DEFAULT_ARTIFACT,
        help="Path to recommendation_shadow_eval.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write recommendation_shadow_scorecard.json.",
    )
    args = parser.parse_args()
    output = build_recommendation_shadow_scorecard_from_file(args.artifact, args.output)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
