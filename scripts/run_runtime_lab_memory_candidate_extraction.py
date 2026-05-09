from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.memory.application.runtime_lab_candidate_extraction import (  # noqa: E402
    write_candidate_extraction_artifact_from_trace,
)
from app.shared.infra.json_artifacts import read_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build lab-only memory candidate extraction artifact from a trace."
    )
    parser.add_argument("--trace-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    trace = read_json_artifact(args.trace_json)
    live_dogfood_replay = os.getenv("RUNTIME_LAB_MEMORY_DOGFOOD_REPLAY") == "1"
    artifact = write_candidate_extraction_artifact_from_trace(
        args.output,
        trace,
        live_dogfood_replay=live_dogfood_replay,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "status": artifact["status"],
                "candidate_count": artifact["candidate_count"],
                "rejection_count": artifact["rejection_count"],
                "live_dogfood_replay": artifact["live_dogfood_replay"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
