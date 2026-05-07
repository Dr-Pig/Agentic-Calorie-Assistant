from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_live_failure_taxonomy_inspection import (  # noqa: E402
    build_websearch_live_failure_taxonomy_inspection,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-diagnostic-report", required=True)
    parser.add_argument("--manager-contract-handoff", required=False)
    parser.add_argument("--status-packet-inspection", required=False)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    artifact = build_websearch_live_failure_taxonomy_inspection(
        live_diagnostic_report=read_json_artifact(Path(args.live_diagnostic_report)),
        manager_contract_handoff_artifact=_read_optional(args.manager_contract_handoff),
        status_packet_inspection_artifact=_read_optional(args.status_packet_inspection),
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "status": artifact["status"],
                "next_safe_slice": artifact["summary"]["next_safe_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _read_optional(value: str | None) -> dict | None:
    if not value:
        return None
    return read_json_artifact(Path(value))


if __name__ == "__main__":
    raise SystemExit(main())
