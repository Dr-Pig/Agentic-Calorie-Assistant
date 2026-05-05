from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_post_extract_lane_status_packet import (  # noqa: E402
    build_websearch_post_extract_lane_status_packet,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_EXTRACT_REPORT = (
    ROOT / "artifacts" / "accurate_intake_websearch_live_extract_canary_report.json"
)
DEFAULT_OUTPUT = (
    ROOT / "artifacts" / "accurate_intake_websearch_post_extract_lane_status_packet.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build WebSearch post-live-extract lane status packet."
    )
    parser.add_argument("--extract-canary-report", default=str(DEFAULT_EXTRACT_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    packet = build_websearch_post_extract_lane_status_packet(
        extract_canary_report=read_json_artifact(Path(args.extract_canary_report))
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, packet)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": packet["status"],
                "next_required_slices": packet["next_required_slices"],
                "runtime_web_activation_approved": packet[
                    "runtime_web_activation_approved"
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
