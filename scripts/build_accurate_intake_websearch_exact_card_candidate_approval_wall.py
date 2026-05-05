from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_exact_card_candidate_approval_wall import (  # noqa: E402
    build_websearch_exact_card_candidate_approval_wall,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_REFRESH = (
    ROOT
    / "artifacts"
    / "accurate_intake_websearch_exact_card_review_packet_refresh.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "artifacts"
    / "accurate_intake_websearch_exact_card_candidate_approval_wall.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build WebSearch exact-card approval wall without exact-card truth promotion."
        )
    )
    parser.add_argument("--exact-card-review-packet-refresh", default=str(DEFAULT_REFRESH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_websearch_exact_card_candidate_approval_wall(
        exact_card_review_packet_refresh=read_json_artifact(
            Path(args.exact_card_review_packet_refresh)
        )
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "blockers": artifact["blockers"],
                "approval_wall_record_count": artifact["summary"][
                    "approval_wall_record_count"
                ],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
