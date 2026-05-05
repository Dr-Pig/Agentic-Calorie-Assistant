from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_exact_card_candidate_manifest_diagnostic import (  # noqa: E402
    build_websearch_exact_card_candidate_manifest_diagnostic,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_POLICY = (
    ROOT
    / "artifacts"
    / "accurate_intake_websearch_exact_card_runtime_promotion_policy.json"
)
DEFAULT_REQUESTS = (
    ROOT
    / "artifacts"
    / "accurate_intake_websearch_exact_card_candidate_manifest_input.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "artifacts"
    / "accurate_intake_websearch_exact_card_candidate_manifest_diagnostic.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build WebSearch exact-card candidate manifest diagnostic without truth."
        )
    )
    parser.add_argument("--runtime-promotion-policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--promotion-requests", default=str(DEFAULT_REQUESTS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    request_artifact = read_json_artifact(Path(args.promotion_requests))
    artifact = build_websearch_exact_card_candidate_manifest_diagnostic(
        runtime_promotion_policy=read_json_artifact(
            Path(args.runtime_promotion_policy)
        ),
        promotion_requests=request_artifact.get("promotion_requests"),
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "manifest_candidate_count": artifact["summary"][
                    "manifest_candidate_count"
                ],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
