from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_quality_plan import (  # noqa: E402
    build_fooddb_quality_improvement_plan,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local-only FoodDB quality improvement plan before truth promotion."
    )
    parser.add_argument(
        "--inventory-json",
        required=True,
        help="Food KB inventory JSON produced by build_accurate_intake_food_kb_inventory.py.",
    )
    parser.add_argument(
        "--food-gap-register",
        default=None,
        help="Optional Food KB gap register JSON.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_fooddb_quality_plan.json",
        help="Output artifact path.",
    )
    args = parser.parse_args(argv)

    plan = build_fooddb_quality_improvement_plan(
        inventory=read_json_artifact(Path(args.inventory_json)),
        food_gap_register=read_json_artifact(Path(args.food_gap_register))
        if args.food_gap_register
        else {},
    )
    write_json_artifact(Path(args.output), plan)
    print(
        json.dumps(
            {
                "artifact": args.output,
                "claim_scope": plan["claim_scope"],
                "first_batch_review_family_count": len(plan["first_batch_review_families"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
