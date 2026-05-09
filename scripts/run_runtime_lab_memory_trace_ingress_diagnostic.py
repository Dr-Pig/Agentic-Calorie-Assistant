from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.memory.application.runtime_lab_trace_ingress import (  # noqa: E402
    write_memory_trace_ingress_diagnostic_artifact,
)
from app.shared.infra.json_artifacts import read_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a lab-only memory trace ingress diagnostic artifact."
    )
    parser.add_argument(
        "--trace-json",
        required=True,
        type=Path,
        help="Path to one runtime request trace JSON object.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output path for the diagnostic artifact.",
    )
    args = parser.parse_args(argv)

    trace = read_json_artifact(args.trace_json)
    live_invoked = os.getenv("RUNTIME_LAB_MEMORY_LIVE_DIAGNOSTIC") == "1"
    artifact = write_memory_trace_ingress_diagnostic_artifact(
        args.output,
        [trace],
        live_invoked=live_invoked,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "status": artifact["status"],
                "event_count": artifact["event_count"],
                "rejected_trace_count": artifact["rejected_trace_count"],
                "live_invoked": artifact["live_invoked"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
