from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_manager_contract_repair_pack import (  # noqa: E402
    build_fooddb_manager_contract_repair_pack,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_DIAGNOSTIC = ROOT / "artifacts" / "accurate_intake_grokfast_fooddb_packet_smoke.json"
DEFAULT_PROBE = ROOT / "artifacts" / "accurate_intake_fooddb_manager_contract_probe.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_manager_contract_repair_pack.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build FoodDB manager contract repair pack artifact."
    )
    parser.add_argument("--diagnostic-artifact", default=str(DEFAULT_DIAGNOSTIC))
    parser.add_argument("--contract-probe-artifact", default=str(DEFAULT_PROBE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    diagnostic_artifact = read_json_artifact(Path(args.diagnostic_artifact))
    contract_probe_artifact = read_json_artifact(Path(args.contract_probe_artifact))
    report = build_fooddb_manager_contract_repair_pack(
        diagnostic_artifact=diagnostic_artifact,
        contract_probe_artifact=contract_probe_artifact,
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, report)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "case_count": report["summary"]["case_count"],
                "alias_hint_counts": report["summary"]["alias_hint_counts"],
                "next_recommended_slice": report["next_recommended_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
