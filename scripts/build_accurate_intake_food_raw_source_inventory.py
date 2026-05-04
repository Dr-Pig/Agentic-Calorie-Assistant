from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.food_raw_source_inventory import (  # noqa: E402
    build_food_raw_source_inventory,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_food_raw_source_inventory.json"


def default_scan_roots() -> list[Path]:
    candidates = [
        ROOT / ".logs",
        ROOT / "app" / "knowledge",
        ROOT / "workspace_data",
        Path.home() / "Documents" / "Data",
        Path.home() / "Documents" / "Playground" / "line-liff-calorie-helper-text-meal-canary-main",
    ]
    return [path for path in candidates if path.exists()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local-only Accurate Intake FoodDB raw source inventory."
    )
    parser.add_argument(
        "--scan-root",
        action="append",
        default=None,
        help="Local root to scan for known raw/staging source filenames. Can be repeated.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output artifact path. Defaults to ignored local artifacts directory.",
    )
    args = parser.parse_args(argv)

    scan_roots = [Path(root) for root in args.scan_root] if args.scan_root else default_scan_roots()
    inventory = build_food_raw_source_inventory(scan_roots=scan_roots)
    write_json_artifact(Path(args.output), inventory)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": inventory["claim_scope"],
                "present_count": inventory["scan_summary"]["present_count"],
                "absent_count": inventory["scan_summary"]["absent_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
