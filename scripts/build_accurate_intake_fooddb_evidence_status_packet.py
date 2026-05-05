from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_evidence_status_packet import (  # noqa: E402
    build_fooddb_evidence_status_packet,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_TFDA_SOURCE = ROOT / "app" / "knowledge" / "tfda_per100g_source_evidence_tw.json"
DEFAULT_EXACT_CARDS = ROOT / "app" / "knowledge" / "exact_item_cards_tw.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_evidence_status_packet.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a compact FoodDB/WebSearch evidence status packet."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--tfda-source", default=str(DEFAULT_TFDA_SOURCE))
    parser.add_argument("--exact-cards", default=str(DEFAULT_EXACT_CARDS))
    parser.add_argument("--contract-handoff-artifact")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    contract_handoff_path = Path(args.contract_handoff_artifact) if args.contract_handoff_artifact else None

    packet = build_fooddb_evidence_status_packet(
        small_anchor_payload=read_json_artifact(Path(args.small_anchor_store)),
        tfda_source_payload=read_json_artifact(Path(args.tfda_source)),
        exact_card_payload=read_json_artifact(Path(args.exact_cards)),
        contract_handoff_artifact=(
            read_json_artifact(contract_handoff_path) if contract_handoff_path is not None else None
        ),
    )
    write_json_artifact(Path(args.output), packet)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": packet["claim_scope"],
                "runtime_truth_changed": packet["runtime_truth_changed"],
                "readiness_claimed": packet["readiness_claimed"],
                "summary": packet["summary"],
                "next_required_slices": packet["next_required_slices"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
