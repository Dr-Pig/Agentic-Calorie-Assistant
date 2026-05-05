from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.body_budget_calibration_closeout import (  # noqa: E402
    build_body_budget_calibration_closeout_pack,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a local BodyBudget calibration closeout diagnostic pack.")
    parser.add_argument(
        "--output",
        default="artifacts/body_budget_calibration_closeout.json",
    )
    args = parser.parse_args(argv)

    artifact = build_body_budget_calibration_closeout_pack()
    write_json_artifact(Path(args.output), artifact)
    print(json.dumps({"artifact": args.output, "status": artifact["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
