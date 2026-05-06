from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_live_failure_taxonomy_inspection import (  # noqa: E402
    build_fooddb_live_failure_taxonomy_inspection,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build FoodDB live failure taxonomy inspection.")
    parser.add_argument("--live-diagnostic-report", required=True)
    parser.add_argument("--manager-contract-handoff")
    parser.add_argument("--manager-contract-handoff-inspection")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    artifact = build_fooddb_live_failure_taxonomy_inspection(
        live_diagnostic_report=read_json_artifact(Path(args.live_diagnostic_report)),
        manager_contract_handoff_artifact=_optional_artifact(args.manager_contract_handoff),
        manager_contract_handoff_inspection_artifact=_optional_artifact(
            args.manager_contract_handoff_inspection
        ),
    )
    write_json_artifact(Path(args.output), artifact)
    return 0


def _optional_artifact(value: str | None) -> dict | None:
    return None if not value else read_json_artifact(Path(value))


if __name__ == "__main__":
    raise SystemExit(main())
