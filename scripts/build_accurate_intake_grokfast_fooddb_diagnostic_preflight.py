from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.grokfast_fooddb_diagnostic_preflight import (  # noqa: E402
    build_grokfast_fooddb_diagnostic_preflight,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_RETRIEVAL_EVAL_WALL = ROOT / "artifacts" / "accurate_intake_retrieval_eval_wall.json"
DEFAULT_FOODDB_STATUS_PACKET = (
    ROOT / "artifacts" / "accurate_intake_fooddb_evidence_status_packet.json"
)
DEFAULT_MANAGER_PACKET_SMOKE = (
    ROOT / "artifacts" / "accurate_intake_fooddb_manager_packet_smoke.json"
)
DEFAULT_FOODDB_ACTIVATION_WALL = (
    ROOT / "artifacts" / "accurate_intake_fooddb_activation_wall.json"
)
DEFAULT_LOCAL_ACTIVATION_SCENARIO_WALL = (
    ROOT / "artifacts" / "accurate_intake_fooddb_local_activation_scenario_wall.json"
)
DEFAULT_OUTPUT = (
    ROOT / "artifacts" / "accurate_intake_grokfast_fooddb_diagnostic_preflight.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic GrokFast FoodDB diagnostic preflight artifact."
    )
    parser.add_argument("--retrieval-eval-wall", default=str(DEFAULT_RETRIEVAL_EVAL_WALL))
    parser.add_argument("--fooddb-status-packet", default=str(DEFAULT_FOODDB_STATUS_PACKET))
    parser.add_argument("--manager-packet-smoke", default=str(DEFAULT_MANAGER_PACKET_SMOKE))
    parser.add_argument("--fooddb-activation-wall", default=str(DEFAULT_FOODDB_ACTIVATION_WALL))
    parser.add_argument(
        "--local-activation-scenario-wall",
        default=str(DEFAULT_LOCAL_ACTIVATION_SCENARIO_WALL),
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=read_json_artifact(Path(args.retrieval_eval_wall)),
        fooddb_status_packet=read_json_artifact(Path(args.fooddb_status_packet)),
        manager_packet_smoke_artifact=read_json_artifact(Path(args.manager_packet_smoke)),
        fooddb_activation_wall_artifact=read_json_artifact(Path(args.fooddb_activation_wall)),
        local_activation_scenario_wall_artifact=read_json_artifact(
            Path(args.local_activation_scenario_wall)
        ),
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "clear_to_run_live_diagnostic": artifact["clear_to_run_live_diagnostic"],
                "blockers": artifact["blockers"],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
