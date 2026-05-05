from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.grokfast_fooddb_contract_probe import (  # noqa: E402
    build_grokfast_fooddb_contract_probe,
)
from app.providers.builderspace_runtime_contract import response_schema_for_stage  # noqa: E402
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE  # noqa: E402
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_PACKET_SMOKE = ROOT / "artifacts" / "accurate_intake_fooddb_manager_packet_smoke.json"
DEFAULT_DIAGNOSTIC = ROOT / "artifacts" / "accurate_intake_grokfast_fooddb_packet_smoke.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_grokfast_fooddb_contract_probe.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build GrokFast FoodDB packet schema contract drift probe."
    )
    parser.add_argument("--packet-smoke", default=str(DEFAULT_PACKET_SMOKE))
    parser.add_argument("--diagnostic-artifact", default=str(DEFAULT_DIAGNOSTIC))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    packet_artifact = read_json_artifact(Path(args.packet_smoke))
    diagnostic_path = Path(args.diagnostic_artifact)
    diagnostic_artifact = read_json_artifact(diagnostic_path) if diagnostic_path.exists() else None
    artifact = build_grokfast_fooddb_contract_probe(
        packet_artifact=packet_artifact,
        response_schema_for_constraints=lambda constraints: response_schema_for_stage(
            MANAGER_LOOP_STAGE,
            constraints=constraints,
        ),
        diagnostic_artifact=diagnostic_artifact,
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "issue_counts": artifact["summary"]["issue_counts"],
                "next_recommended_slice": artifact["next_recommended_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
