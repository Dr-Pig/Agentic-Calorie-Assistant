from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.food_evidence_approved_batch_proposal import (  # noqa: E402
    build_food_evidence_approved_batch_proposal,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a promotion-blocked proposal from approved Food Evidence decisions."
    )
    parser.add_argument("--review-pack", required=True)
    parser.add_argument("--review-decision", required=True)
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_food_evidence_approved_batch_proposal.json",
    )
    args = parser.parse_args(argv)

    artifact = build_food_evidence_approved_batch_proposal(
        review_pack=read_json_artifact(Path(args.review_pack)),
        review_decision_artifact=read_json_artifact(Path(args.review_decision)),
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": args.output,
                "status": artifact["status"],
                "claim_scope": artifact["claim_scope"],
                "approved_candidate_count": artifact["summary"]["approved_candidate_count"],
                "blocker_count": len(artifact["blockers"]),
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] == "valid_promotion_blocked_proposal" else 1


if __name__ == "__main__":
    raise SystemExit(main())
