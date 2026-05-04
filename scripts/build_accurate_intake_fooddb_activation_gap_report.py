from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_activation_gap_report import (  # noqa: E402
    build_fooddb_activation_gap_report,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_TFDA_SOURCE = ROOT / "app" / "knowledge" / "tfda_per100g_source_evidence_tw.json"
DEFAULT_EXACT_CARDS = ROOT / "app" / "knowledge" / "exact_item_cards_tw.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_activation_gap_report.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a report-only FoodDB activation gap report artifact."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--tfda-source", default=str(DEFAULT_TFDA_SOURCE))
    parser.add_argument("--exact-cards", default=str(DEFAULT_EXACT_CARDS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_fooddb_activation_gap_report(
        small_anchor_payload=read_json_artifact(Path(args.small_anchor_store)),
        tfda_source_payload=read_json_artifact(Path(args.tfda_source)),
        exact_card_payload=read_json_artifact(Path(args.exact_cards)),
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": artifact["claim_scope"],
                "runtime_truth_changed": artifact["runtime_truth_changed"],
                "runtime_visible_common_serving_anchor_count": artifact["summary"][
                    "runtime_visible_common_serving_anchor_count"
                ],
                "listed_component_anchor_count": artifact["summary"][
                    "listed_component_anchor_count"
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
