from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_guarded_afk_truth_audit import (  # noqa: E402
    build_fooddb_guarded_afk_truth_audit,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_TFDA_SOURCE = ROOT / "app" / "knowledge" / "tfda_per100g_source_evidence_tw.json"
DEFAULT_EXACT_CARDS = ROOT / "app" / "knowledge" / "exact_item_cards_tw.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_guarded_afk_truth_audit.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a FoodDB Guarded AFK truth audit artifact without changing runtime truth."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--tfda-source", default=str(DEFAULT_TFDA_SOURCE))
    parser.add_argument("--exact-cards", default=str(DEFAULT_EXACT_CARDS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    audit = build_fooddb_guarded_afk_truth_audit(
        small_anchor_payload=read_json_artifact(Path(args.small_anchor_store)),
        tfda_source_payload=read_json_artifact(Path(args.tfda_source)),
        exact_card_payload=read_json_artifact(Path(args.exact_cards)),
    )
    write_json_artifact(Path(args.output), audit)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": audit["claim_scope"],
                "stop_gate_status": audit["stop_gate_status"],
                "blocker_count": audit["summary"]["blocker_count"],
                "runtime_common_serving_anchor_count": audit["summary"][
                    "runtime_common_serving_anchor_count"
                ],
                "tfda_source_evidence_only_count": audit["summary"][
                    "tfda_source_evidence_only_count"
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0 if audit["stop_gate_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
