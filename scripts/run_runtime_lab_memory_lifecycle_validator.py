from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.memory.application.runtime_lab_candidate_extraction import (  # noqa: E402
    build_candidate_extraction_artifact_from_ingress_events,
)
from app.memory.application.runtime_lab_lifecycle_validator import (  # noqa: E402
    build_lifecycle_decision_artifact,
)
from app.memory.application.runtime_lab_trace_ingress import (  # noqa: E402
    build_memory_ingress_event_from_manager_trace,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build lab-only memory lifecycle decision artifact from a trace."
    )
    parser.add_argument("--trace-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args(argv)

    trace = read_json_artifact(args.trace_json)
    event = build_memory_ingress_event_from_manager_trace(trace)
    extraction = build_candidate_extraction_artifact_from_ingress_events([event])
    artifact = build_lifecycle_decision_artifact(
        extraction["candidates"],
        as_of=args.as_of,
        runtime_connected=True,
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
