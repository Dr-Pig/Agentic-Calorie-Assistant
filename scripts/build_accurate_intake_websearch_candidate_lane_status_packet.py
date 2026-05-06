from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_candidate_lane_status_packet import (  # noqa: E402
    build_websearch_candidate_lane_status_packet,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_candidate_lane_status_packet.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build WebSearch candidate lane status packet."
    )
    parser.add_argument("--fooddb-status-packet")
    parser.add_argument("--manager-contract-handoff-artifact")
    parser.add_argument("--live-diagnostic-report")
    parser.add_argument("--contract-probe-artifact")
    parser.add_argument("--repair-pack-artifact")
    parser.add_argument("--preflight-artifact")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet=(
            read_json_artifact(Path(args.fooddb_status_packet)) if args.fooddb_status_packet else None
        ),
        manager_contract_handoff_artifact=(
            read_json_artifact(Path(args.manager_contract_handoff_artifact))
            if args.manager_contract_handoff_artifact
            else None
        ),
        live_diagnostic_report=(
            read_json_artifact(Path(args.live_diagnostic_report))
            if args.live_diagnostic_report
            else None
        ),
        contract_probe_artifact=(
            read_json_artifact(Path(args.contract_probe_artifact))
            if args.contract_probe_artifact
            else None
        ),
        repair_pack_artifact=(
            read_json_artifact(Path(args.repair_pack_artifact))
            if args.repair_pack_artifact
            else None
        ),
        preflight_artifact=(
            read_json_artifact(Path(args.preflight_artifact)) if args.preflight_artifact else None
        ),
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "claim_scope": artifact["claim_scope"],
                "upstream_fooddb_gate_status": artifact["summary"]["upstream_fooddb_gate_status"],
                "manager_contract_gate_status": artifact["summary"]["manager_contract_gate_status"],
                "next_required_slices": artifact["next_required_slices"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
