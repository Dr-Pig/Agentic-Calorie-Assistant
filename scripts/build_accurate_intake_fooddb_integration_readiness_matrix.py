from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_integration_readiness_matrix import (  # noqa: E402
    build_fooddb_integration_readiness_matrix,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_integration_readiness_matrix.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build FoodDB/WebSearch integration readiness matrix artifact."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--product-loop-handoff")
    parser.add_argument("--approved-packet-ready-artifact")
    parser.add_argument("--fooddb-manager-packet-smoke")
    args = parser.parse_args(argv)

    artifact = build_fooddb_integration_readiness_matrix(
        product_loop_handoff=_load_optional(args.product_loop_handoff),
        approved_packet_ready_artifact=_load_optional(args.approved_packet_ready_artifact),
        fooddb_manager_packet_smoke=_load_optional(args.fooddb_manager_packet_smoke),
    )
    write_json_artifact(Path(args.output), artifact)
    validation = artifact.get("current_shell_product_loop_fooddb_validation") or {}
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": artifact["claim_scope"],
                "edge_count": artifact["summary"]["edge_count"],
                "contract_backed": artifact["summary"]["contract_backed"],
                "draft": artifact["summary"]["draft"],
                "missing": artifact["summary"]["missing"],
                "current_shell_product_loop_fooddb_validation_status": validation.get(
                    "status", "not_evaluated"
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _load_optional(path: str | None) -> dict | None:
    return read_json_artifact(Path(path)) if path else None


if __name__ == "__main__":
    raise SystemExit(main())
