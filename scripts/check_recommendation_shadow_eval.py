from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.recommendation.application.shadow_artifact_gate import (  # noqa: E402
    evaluate_recommendation_shadow_artifact_payload,
)


DEFAULT_ARTIFACT = ROOT / "artifacts" / "recommendation_shadow_eval.json"


def check_recommendation_shadow_eval_artifact(
    artifact_path: Path = DEFAULT_ARTIFACT,
) -> tuple[int, dict]:
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    result = evaluate_recommendation_shadow_artifact_payload(payload)
    payload = result.model_dump(mode="json")
    return (0 if result.passed else 1), payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check the offline recommendation shadow eval artifact."
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        default=DEFAULT_ARTIFACT,
        help="Path to recommendation_shadow_eval.json.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional JSON report output path.",
    )
    args = parser.parse_args()

    exit_code, payload = check_recommendation_shadow_eval_artifact(args.artifact)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if exit_code == 0:
        print("recommendation shadow artifact gate passed")
    else:
        print("recommendation shadow artifact gate failed")
        print(json.dumps(payload["failure_codes"], indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
