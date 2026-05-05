from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_activation_wall import (  # noqa: E402
    build_fooddb_activation_wall,
)
from app.nutrition.infrastructure.local_food_evidence_index import (  # noqa: E402
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_TFDA_SOURCE_EVIDENCE = ROOT / "app" / "knowledge" / "tfda_per100g_source_evidence_tw.json"
DEFAULT_EXACT_ITEM_CARDS = ROOT / "app" / "knowledge" / "exact_item_cards_tw.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_activation_wall.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic FoodDB activation minimum wall artifact."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--tfda-source-evidence", default=str(DEFAULT_TFDA_SOURCE_EVIDENCE))
    parser.add_argument("--exact-item-cards", default=str(DEFAULT_EXACT_ITEM_CARDS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    small_anchor_path = Path(args.small_anchor_store)
    index = LocalSmallAnchorFoodEvidenceIndex.from_path(small_anchor_path)
    artifact = build_fooddb_activation_wall(
        small_anchor_payload=read_json_artifact(small_anchor_path),
        tfda_source_payload=read_json_artifact(Path(args.tfda_source_evidence)),
        exact_card_payload=read_json_artifact(Path(args.exact_item_cards)),
        retrieval_records=index.load_records(),
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


if __name__ == "__main__":
    raise SystemExit(main())
