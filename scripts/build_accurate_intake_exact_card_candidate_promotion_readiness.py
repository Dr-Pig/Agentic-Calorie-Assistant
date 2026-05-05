from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.exact_card_candidate_promotion_readiness import (  # noqa: E402
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (  # noqa: E402
    build_exact_evidence_lane_policy_artifact,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_EXACT_LANE = ROOT / "artifacts" / "accurate_intake_exact_evidence_lane_policy.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_exact_card_candidate_promotion_readiness.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build exact-card candidate promotion readiness artifact."
    )
    parser.add_argument("--exact-lane-artifact", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    if args.exact_lane_artifact:
        exact_lane = read_json_artifact(Path(args.exact_lane_artifact))
    elif DEFAULT_EXACT_LANE.exists():
        exact_lane = read_json_artifact(DEFAULT_EXACT_LANE)
    else:
        exact_lane = build_exact_evidence_lane_policy_artifact()

    artifact = build_exact_card_candidate_promotion_readiness(exact_lane_artifact=exact_lane)
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "blockers": artifact["blockers"],
                "summary": artifact["summary"],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
