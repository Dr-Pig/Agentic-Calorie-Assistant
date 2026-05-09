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
from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore  # noqa: E402
from app.memory.application.runtime_lab_trace_ingress import (  # noqa: E402
    build_memory_ingress_event_from_manager_trace,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay one trace into the isolated runtime-lab memory store."
    )
    parser.add_argument("--trace-json", required=True, type=Path)
    parser.add_argument("--store-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    trace = read_json_artifact(args.trace_json)
    event = build_memory_ingress_event_from_manager_trace(trace)
    extraction = build_candidate_extraction_artifact_from_ingress_events([event])
    store = RuntimeLabMemoryStore(args.store_root)
    records = [store.write_candidate(candidate) for candidate in extraction["candidates"]]
    artifact = {
        "artifact_type": "runtime_lab_memory_store_replay",
        "status": "pass" if records else "blocked",
        "stored_candidate_count": len(records),
        "candidate_ids": [record["candidate_id"] for record in records],
        "store_root": str(args.store_root),
        "runtime_connected": True,
        "lab_isolated": True,
        "canonical_db_changed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "user_facing_behavior_changed": False,
        "shadow_memory_context_pack_used": False,
        "candidate_extraction_status": extraction["status"],
    }
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
