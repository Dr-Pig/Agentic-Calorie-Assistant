from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_status_packet_inspection import (  # noqa: E402
    build_fooddb_status_packet_inspection,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402

DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_status_packet_inspection.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fooddb-status-packet", type=Path, required=True)
    parser.add_argument("--live-runner-readiness-artifact", type=Path)
    parser.add_argument("--contract-handoff-artifact", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    artifact = build_fooddb_status_packet_inspection(
        fooddb_status_packet=read_json_artifact(args.fooddb_status_packet),
        live_runner_readiness_artifact=_read_optional(args.live_runner_readiness_artifact),
        contract_handoff_artifact=_read_optional(args.contract_handoff_artifact),
    )
    write_json_artifact(args.output, artifact)
    return 0


def _read_optional(path: Path | None) -> dict | None:
    return None if path is None else read_json_artifact(path)


if __name__ == "__main__":
    raise SystemExit(main())
