from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_manager_contract_probe import (  # noqa: E402
    build_fooddb_manager_contract_probe,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_INPUT = ROOT / "artifacts" / "accurate_intake_grokfast_fooddb_packet_smoke.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_manager_contract_probe.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build FoodDB manager contract probe from GrokFast packet live diagnostic artifact."
    )
    parser.add_argument("--diagnostic-artifact", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    diagnostic_artifact = read_json_artifact(Path(args.diagnostic_artifact))
    probe = build_fooddb_manager_contract_probe(diagnostic_artifact=diagnostic_artifact)
    output_path = Path(args.output)
    write_json_artifact(output_path, probe)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "contract_failure_detected": probe["contract_failure_detected"],
                "next_recommended_slice": probe["next_recommended_slice"],
                "summary": probe["summary"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
