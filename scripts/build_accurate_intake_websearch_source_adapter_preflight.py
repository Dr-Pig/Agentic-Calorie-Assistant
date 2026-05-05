from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_source_adapter_preflight import (  # noqa: E402
    build_websearch_source_adapter_preflight,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_source_adapter_preflight.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic WebSearch source adapter preflight artifact."
    )
    parser.add_argument("--websearch-status-packet")
    parser.add_argument("--cache-rate-license-artifact")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_websearch_source_adapter_preflight(
        websearch_status_packet=(
            read_json_artifact(Path(args.websearch_status_packet))
            if args.websearch_status_packet
            else None
        ),
        cache_rate_license_artifact=(
            read_json_artifact(Path(args.cache_rate_license_artifact))
            if args.cache_rate_license_artifact
            else None
        ),
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "blockers": artifact["blockers"],
                "ready_for_live_search_diagnostic": artifact[
                    "ready_for_live_search_diagnostic"
                ],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
