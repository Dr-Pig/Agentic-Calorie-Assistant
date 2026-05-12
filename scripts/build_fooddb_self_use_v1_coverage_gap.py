from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (  # noqa: E402
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.application.fooddb_self_use_v1_coverage_gap import (  # noqa: E402
    build_fooddb_self_use_v1_coverage_gap,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_APPROVED_ARTIFACT = (
    ROOT / "artifacts" / "accurate_intake_approved_packet_ready_fooddb_artifact.json"
)
DEFAULT_OUTPUT = ROOT / "artifacts" / "fooddb_self_use_v1_1000_packet_ready_coverage_gap.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a report-only FoodDB self-use v1 1000 packet-ready coverage gap artifact."
    )
    parser.add_argument("--approved-artifact", default=str(DEFAULT_APPROVED_ARTIFACT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--build-current-artifact",
        action="store_true",
        help="Build the full_current_shell approved packet-ready artifact instead of reading one.",
    )
    args = parser.parse_args(argv)

    if args.build_current_artifact:
        approved = build_approved_packet_ready_fooddb_artifact(
            artifact_path=str(DEFAULT_APPROVED_ARTIFACT),
            selection_profile="full_current_shell",
        )
    else:
        approved = read_json_artifact(Path(args.approved_artifact))

    report = build_fooddb_self_use_v1_coverage_gap(
        approved_packet_ready_artifact=approved,
    )
    write_json_artifact(Path(args.output), report)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "status": report["status"],
                "remaining_packet_ready_records": report["gap"]["packet_ready_item_count"],
                "runtime_truth_changed": report["runtime_truth_changed"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
