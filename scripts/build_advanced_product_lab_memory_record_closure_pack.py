from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.product_lab_memory_record_closure_pack import (  # noqa: E402
    build_memory_record_closure_pack,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the MemoryRecord advanced product-lab closure pack."
    )
    parser.add_argument("--summary-json", required=True, type=Path)
    parser.add_argument("--readiness-json", required=True, type=Path)
    parser.add_argument("--integrated-e2e-json", required=True, type=Path)
    parser.add_argument("--live-diagnostic-json", required=True, type=Path)
    parser.add_argument("--holdout-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    pack = build_memory_record_closure_pack(
        summary_artifact=read_json_artifact(args.summary_json),
        readiness_report=read_json_artifact(args.readiness_json),
        integrated_e2e_artifact=read_json_artifact(args.integrated_e2e_json),
        live_diagnostic_artifact=read_json_artifact(args.live_diagnostic_json),
        holdout_report=read_json_artifact(args.holdout_json),
        source_summary_path=args.summary_json,
        source_readiness_path=args.readiness_json,
        source_integrated_e2e_path=args.integrated_e2e_json,
        source_live_diagnostic_path=args.live_diagnostic_json,
        source_holdout_path=args.holdout_json,
    )
    write_json_artifact(args.output, pack)
    print(json.dumps(pack, ensure_ascii=False))
    return 0 if pack["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
