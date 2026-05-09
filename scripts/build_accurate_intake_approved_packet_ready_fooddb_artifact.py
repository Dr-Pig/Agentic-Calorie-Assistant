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
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402

DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_approved_packet_ready_fooddb_artifact.json"


def _load_exact_item_cards(path: str | None) -> list[dict[str, object]] | None:
    if not path:
        return None
    payload = read_json_artifact(Path(path))
    return list(payload.get("cards", []))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the minimal approved packet-ready FoodDB artifact for Current Shell handoff."
    )
    parser.add_argument(
        "--exact-item-cards",
        help="Optional exact item cards JSON override. Defaults to app/knowledge/exact_item_cards_tw.json.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output artifact path. Defaults to ignored local artifacts directory.",
    )
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args(argv)

    artifact = build_approved_packet_ready_fooddb_artifact(
        exact_item_cards=_load_exact_item_cards(args.exact_item_cards),
        artifact_path=args.output,
        limit=args.limit,
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "status": artifact["status"],
                "ready_for_other_tracks": artifact["ready_for_other_tracks"],
                "packet_ready_item_count": artifact["summary"]["packet_ready_item_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["ready_for_other_tracks"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
