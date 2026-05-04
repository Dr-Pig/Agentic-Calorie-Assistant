from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.food_evidence_auto_eligible_batch import (  # noqa: E402
    build_food_evidence_auto_eligible_batch,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_VALIDATION = ROOT / "artifacts" / "accurate_intake_food_evidence_validation.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_food_auto_eligible_batch.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build auto-eligible FoodDB candidate batch diagnostics before PR121 truth promotion."
    )
    parser.add_argument(
        "--validation-json",
        default=str(DEFAULT_VALIDATION),
        help="Food evidence validation artifact JSON path.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output artifact path. Defaults to ignored local artifacts directory.",
    )
    parser.add_argument(
        "--sample-size-per-group",
        type=int,
        default=10,
        help="Maximum sample audit rows per source/role group.",
    )
    args = parser.parse_args(argv)

    validation_artifact = read_json_artifact(Path(args.validation_json))
    artifact = build_food_evidence_auto_eligible_batch(
        validation_artifact=validation_artifact,
        sample_size_per_group=args.sample_size_per_group,
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": artifact["claim_scope"],
                "auto_eligible_count": artifact["summary"]["auto_eligible_count"],
                "exception_count": artifact["summary"]["exception_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
