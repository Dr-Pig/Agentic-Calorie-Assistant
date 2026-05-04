from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.food_gap_register import build_food_kb_gap_register  # noqa: E402
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build local-only Accurate Intake Food KB gap candidates from an operator review artifact."
    )
    parser.add_argument(
        "--operator-review-json",
        required=True,
        help="PR111 dogfood operator review surface JSON.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_food_kb_gap_register.json",
        help="Output artifact path.",
    )
    args = parser.parse_args(argv)

    artifact = build_food_kb_gap_register(read_json_artifact(Path(args.operator_review_json)))
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": args.output,
                "status": artifact["status"],
                "candidate_count": artifact["summary"]["candidate_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
