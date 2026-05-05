from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_exact_card_manifest_review_packet import (  # noqa: E402
    build_websearch_exact_card_manifest_review_packet,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_MANIFEST = (
    ROOT
    / "artifacts"
    / "accurate_intake_websearch_exact_card_candidate_manifest_diagnostic.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "artifacts"
    / "accurate_intake_websearch_exact_card_manifest_review_packet.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build WebSearch exact-card manifest review packet without runtime truth."
        )
    )
    parser.add_argument("--manifest-diagnostic", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_websearch_exact_card_manifest_review_packet(
        manifest_diagnostic=read_json_artifact(Path(args.manifest_diagnostic))
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "review_packet_count": artifact["summary"]["review_packet_count"],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
