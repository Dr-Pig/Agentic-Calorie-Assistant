from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.exact_evidence_lane_status_packet import (  # noqa: E402
    build_exact_evidence_lane_status_packet,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_exact_evidence_lane_status_packet.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build exact evidence lane status packet."
    )
    parser.add_argument("--websearch-status-packet")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_exact_evidence_lane_status_packet(
        websearch_status_packet=(
            read_json_artifact(Path(args.websearch_status_packet)) if args.websearch_status_packet else None
        )
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "claim_scope": artifact["claim_scope"],
                "upstream_websearch_gate_status": artifact["summary"]["upstream_websearch_gate_status"],
                "next_required_slices": artifact["next_required_slices"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
