from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_integration_readiness_matrix import (  # noqa: E402
    build_websearch_integration_readiness_matrix,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_integration_readiness_matrix.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build FoodDB/WebSearch evidence integration readiness matrix."
    )
    parser.add_argument("--fooddb-status-packet")
    parser.add_argument("--websearch-status-packet")
    parser.add_argument("--source-adapter-preflight")
    parser.add_argument("--live-search-canary-report")
    parser.add_argument("--exact-lane-status-packet")
    parser.add_argument("--live-extract-preflight")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_websearch_integration_readiness_matrix(
        fooddb_status_packet=_read_optional(args.fooddb_status_packet),
        websearch_status_packet=_read_optional(args.websearch_status_packet),
        source_adapter_preflight=_read_optional(args.source_adapter_preflight),
        live_search_canary_report=_read_optional(args.live_search_canary_report),
        exact_lane_status_packet=_read_optional(args.exact_lane_status_packet),
        live_extract_preflight=_read_optional(args.live_extract_preflight),
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "clear_edge_count": artifact["summary"]["clear_edge_count"],
                "blocked_edge_count": artifact["summary"]["blocked_edge_count"],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _read_optional(path: str | None) -> dict | None:
    return read_json_artifact(Path(path)) if path else None


if __name__ == "__main__":
    raise SystemExit(main())
