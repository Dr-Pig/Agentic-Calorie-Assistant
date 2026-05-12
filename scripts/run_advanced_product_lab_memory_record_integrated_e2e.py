from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.product_lab_memory_record_integrated_e2e import (  # noqa: E402
    run_memory_record_integrated_e2e_chain,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run MemoryRecord-backed advanced product-lab integrated E2E."
    )
    parser.add_argument("--summary-json", required=True, type=Path)
    parser.add_argument("--readiness-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    artifact = run_memory_record_integrated_e2e_chain(
        summary_artifact=read_json_artifact(args.summary_json),
        readiness_report=read_json_artifact(args.readiness_json),
        source_summary_path=args.summary_json,
        source_readiness_path=args.readiness_json,
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
