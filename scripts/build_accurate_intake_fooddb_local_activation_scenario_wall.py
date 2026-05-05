from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_local_activation_scenario_wall import (  # noqa: E402
    build_fooddb_local_activation_scenario_wall,
)
from app.nutrition.infrastructure.local_food_evidence_index import (  # noqa: E402
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_ACTIVATION_WALL = ROOT / "artifacts" / "accurate_intake_fooddb_activation_wall.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_local_activation_scenario_wall.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic FoodDB local activation scenario packet wall artifact."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--activation-wall", default=str(DEFAULT_ACTIVATION_WALL))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    index = LocalSmallAnchorFoodEvidenceIndex.from_path(Path(args.small_anchor_store))
    activation_wall = _optional_artifact(Path(args.activation_wall))
    artifact = build_fooddb_local_activation_scenario_wall(
        retrieval_records=index.load_records(),
        activation_wall_artifact=activation_wall,
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "status": artifact["status"],
                "blocker_count": len(artifact["blockers"]),
                "next_required_slice": artifact["next_required_slice"],
                "readiness_claimed": artifact["readiness_claimed"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] == "pass" else 1


def _optional_artifact(path: Path) -> dict | None:
    if not path.exists():
        raise FileNotFoundError(
            f"FoodDB activation wall artifact is required before scenario wall: {path}"
        )
    return read_json_artifact(path)


if __name__ == "__main__":
    raise SystemExit(main())
