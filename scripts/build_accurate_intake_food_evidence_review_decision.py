from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.food_evidence_review_decision import (  # noqa: E402
    build_food_evidence_review_decision_artifact,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Food Evidence human review decisions as metadata only."
    )
    parser.add_argument("--review-pack", required=True)
    parser.add_argument("--decision-payload", required=True)
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_food_evidence_review_decision.json",
    )
    args = parser.parse_args(argv)

    artifact = build_food_evidence_review_decision_artifact(
        review_pack=read_json_artifact(Path(args.review_pack)),
        decision_payload=read_json_artifact(Path(args.decision_payload)),
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": args.output,
                "status": artifact["status"],
                "claim_scope": artifact["claim_scope"],
                "decision_count": artifact["summary"]["decision_count"],
                "blocker_count": len(artifact["blockers"]),
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] == "valid_review_metadata" else 1


if __name__ == "__main__":
    raise SystemExit(main())
