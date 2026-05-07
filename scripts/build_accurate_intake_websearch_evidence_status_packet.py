from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_evidence_status_packet import (  # noqa: E402
    build_websearch_evidence_status_packet,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402

DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_evidence_status_packet.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-lane-status-packet", type=Path)
    parser.add_argument("--exact-lane-status-packet", type=Path)
    parser.add_argument("--manager-contract-handoff-artifact", type=Path)
    parser.add_argument("--candidate-pipeline-narrow-expansion-artifact", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    artifact = build_websearch_evidence_status_packet(
        candidate_lane_status_packet=_read_optional(args.candidate_lane_status_packet),
        exact_lane_status_packet=_read_optional(args.exact_lane_status_packet),
        manager_contract_handoff_artifact=_read_optional(args.manager_contract_handoff_artifact),
        candidate_pipeline_narrow_expansion_artifact=_read_optional(
            args.candidate_pipeline_narrow_expansion_artifact
        ),
    )
    write_json_artifact(args.output, artifact)
    return 0


def _read_optional(path: Path | None) -> dict | None:
    if path is None:
        return None
    return read_json_artifact(path)


if __name__ == "__main__":
    raise SystemExit(main())
