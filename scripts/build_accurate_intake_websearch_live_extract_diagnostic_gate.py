from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_live_extract_diagnostic_gate import (  # noqa: E402
    build_websearch_live_extract_diagnostic_gate,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_live_extract_diagnostic_gate.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build WebSearch live extract diagnostic gate artifact."
    )
    parser.add_argument("--integration-matrix", required=True)
    parser.add_argument("--live-extract-preflight", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_websearch_live_extract_diagnostic_gate(
        integration_matrix_artifact=read_json_artifact(Path(args.integration_matrix)),
        live_extract_preflight_artifact=read_json_artifact(Path(args.live_extract_preflight)),
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "ready_for_trace_only_live_extract_diagnostic": artifact[
                    "ready_for_trace_only_live_extract_diagnostic"
                ],
                "review_packet_ref_count": artifact["summary"]["review_packet_ref_count"],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
