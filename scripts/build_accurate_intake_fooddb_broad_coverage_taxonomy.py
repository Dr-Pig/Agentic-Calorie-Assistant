from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_broad_coverage_taxonomy import (  # noqa: E402
    build_fooddb_broad_coverage_taxonomy,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_broad_coverage_taxonomy.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a report-only FoodDB broad coverage taxonomy artifact."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_fooddb_broad_coverage_taxonomy(
        small_anchor_payload=read_json_artifact(Path(args.small_anchor_store)),
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": artifact["claim_scope"],
                "runtime_truth_changed": artifact["runtime_truth_changed"],
                "next_runtime_batch_candidate_count": artifact["summary"][
                    "next_runtime_batch_candidate_count"
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
