from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (  # noqa: E402
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.application.fooddb_real_manager_e2e import (  # noqa: E402
    build_fooddb_real_manager_e2e,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_APPROVED_ARTIFACT_PATH = ROOT / "artifacts" / "approved_packet_ready_fooddb_full.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_real_manager_e2e.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build real packet-ready FoodDB Manager evidence-path E2E artifact."
    )
    parser.add_argument("--approved-packet-ready-artifact")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    approved_artifact = (
        read_json_artifact(Path(args.approved_packet_ready_artifact))
        if args.approved_packet_ready_artifact
        else build_approved_packet_ready_fooddb_artifact(
            artifact_path=str(DEFAULT_APPROVED_ARTIFACT_PATH),
            selection_profile="full_current_shell",
        )
    )
    artifact = build_fooddb_real_manager_e2e(
        approved_packet_ready_artifact=approved_artifact,
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": artifact["claim_scope"],
                "case_count": artifact["summary"]["case_count"],
                "pass_count": artifact["summary"]["pass_count"],
                "live_provider_used": artifact["live_provider_used"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
