from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.food_review_pack import (  # noqa: E402
    build_food_evidence_human_review_pack,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local-only first Food Evidence human review pack from gap artifacts."
    )
    parser.add_argument(
        "--food-gap-register",
        required=True,
        help="Food KB gap register JSON produced from the operator review surface.",
    )
    parser.add_argument(
        "--inventory-json",
        required=True,
        help="Food KB source-quality inventory JSON.",
    )
    parser.add_argument(
        "--quality-plan-json",
        required=True,
        help="FoodDB quality improvement plan JSON.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_food_evidence_human_review_pack.json",
        help="Output artifact path.",
    )
    args = parser.parse_args(argv)

    review_pack = build_food_evidence_human_review_pack(
        food_gap_register=read_json_artifact(Path(args.food_gap_register)),
        inventory=read_json_artifact(Path(args.inventory_json)),
        quality_plan=read_json_artifact(Path(args.quality_plan_json)),
    )
    write_json_artifact(Path(args.output), review_pack)
    print(
        json.dumps(
            {
                "artifact": args.output,
                "claim_scope": review_pack["claim_scope"],
                "review_packet_count": review_pack["summary"]["review_packet_count"],
                "candidate_count": review_pack["summary"]["candidate_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
