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
from app.memory.application.runtime_lab_manager_injection import (  # noqa: E402
    build_manager_memory_injection_comparison,
)
from app.memory.application.runtime_lab_retrieval import (  # noqa: E402
    build_shadow_memory_context_pack,
)
from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore  # noqa: E402
from app.memory.application.runtime_lab_trace_ingress import (  # noqa: E402
    build_memory_ingress_event_from_manager_trace,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run lab-only paired Manager memory injection replay."
    )
    parser.add_argument("--trace-json", required=True, type=Path)
    parser.add_argument("--store-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--enable-lab-injection", action="store_true")
    args = parser.parse_args(argv)

    trace = read_json_artifact(args.trace_json)
    event = build_memory_ingress_event_from_manager_trace(trace)
    extraction = build_candidate_extraction_artifact_from_ingress_events([event])
    store = RuntimeLabMemoryStore(args.store_root)
    for candidate in extraction["candidates"]:
        store.write_candidate(candidate)
    pack = build_shadow_memory_context_pack(
        store,
        event["scope_keys"],
        token_budget=120,
        runtime_connected=True,
    )
    artifact = build_manager_memory_injection_comparison(
        trace,
        pack,
        enable_lab_injection=args.enable_lab_injection,
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
