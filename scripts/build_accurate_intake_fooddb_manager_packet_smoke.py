from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_manager_packet_smoke import (  # noqa: E402
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.infrastructure.local_food_evidence_index import (  # noqa: E402
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_manager_packet_smoke.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic FoodDB manager evidence packet smoke artifact."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    index = LocalSmallAnchorFoodEvidenceIndex.from_path(Path(args.small_anchor_store))
    retrieval_records = index.load_records()
    artifact = build_fooddb_manager_packet_smoke(retrieval_records=retrieval_records)
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": artifact["claim_scope"],
                "case_count": artifact["summary"]["case_count"],
                "compact_packet_pass_count": artifact["summary"]["compact_packet_pass_count"],
                "live_provider_used": artifact["live_provider_used"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
