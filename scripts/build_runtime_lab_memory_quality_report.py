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
    build_candidate_extraction_artifact_from_edd_suite,
    build_candidate_extraction_artifact_from_ingress_events,
)
from app.memory.application.runtime_lab_consumer_summary_pack import (  # noqa: E402
    build_runtime_lab_memory_consumer_summary_pack,
)
from app.memory.application.runtime_lab_lifecycle_validator import (  # noqa: E402
    build_lifecycle_decision_artifact,
)
from app.memory.application.runtime_lab_manager_injection import (  # noqa: E402
    build_manager_memory_injection_comparison,
)
from app.memory.application.runtime_lab_memory_edd import (  # noqa: E402
    load_runtime_lab_memory_edd_suite,
)
from app.memory.application.runtime_lab_quality_report import (  # noqa: E402
    build_runtime_lab_memory_quality_report,
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
        description="Build the memory runtime-lab shadow quality report."
    )
    parser.add_argument("--trace-json", required=True, type=Path)
    parser.add_argument("--store-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--review-contract-json", type=Path)
    parser.add_argument("--consumer-summary-output", type=Path)
    args = parser.parse_args(argv)
    if args.consumer_summary_output and not args.review_contract_json:
        parser.error("--consumer-summary-output requires --review-contract-json")

    suite = load_runtime_lab_memory_edd_suite()
    fixture_extraction = build_candidate_extraction_artifact_from_edd_suite(suite)
    trace = read_json_artifact(args.trace_json)
    event = build_memory_ingress_event_from_manager_trace(trace)
    dogfood_extraction = build_candidate_extraction_artifact_from_ingress_events([event])
    lifecycle = build_lifecycle_decision_artifact(
        dogfood_extraction["candidates"],
        as_of=args.as_of,
        runtime_connected=True,
    )
    store = RuntimeLabMemoryStore(args.store_root)
    for candidate in dogfood_extraction["candidates"]:
        store.write_candidate(candidate)
    context_pack = build_shadow_memory_context_pack(
        store,
        event["scope_keys"],
        token_budget=120,
        runtime_connected=True,
    )
    injection = build_manager_memory_injection_comparison(
        trace,
        context_pack,
        enable_lab_injection=True,
    )
    consumer_summary_projection = None
    if args.review_contract_json:
        consumer_summary_projection = build_runtime_lab_memory_consumer_summary_pack(
            read_json_artifact(args.review_contract_json)
        )
        if args.consumer_summary_output:
            write_json_artifact(args.consumer_summary_output, consumer_summary_projection)
    report = build_runtime_lab_memory_quality_report(
        suite=suite,
        fixture_extraction=fixture_extraction,
        dogfood_extraction=dogfood_extraction,
        lifecycle=lifecycle,
        context_pack=context_pack,
        injection=injection,
        consumer_summary_projection=consumer_summary_projection,
        optional_live_run_invoked=os.getenv("RUNTIME_LAB_MEMORY_OPTIONAL_LIVE_REPORT")
        == "1",
    )
    write_json_artifact(args.output, report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
