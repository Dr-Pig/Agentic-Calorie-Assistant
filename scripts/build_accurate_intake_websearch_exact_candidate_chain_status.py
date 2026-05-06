from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_exact_candidate_chain_status import (  # noqa: E402
    build_websearch_exact_candidate_chain_status,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_exact_candidate_chain_status.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic WebSearch exact-candidate source-chain status."
    )
    parser.add_argument("--selected-extract-artifact")
    parser.add_argument("--extract-result-artifact")
    parser.add_argument("--exact-review-packet-artifact")
    parser.add_argument("--preflight-artifact")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_websearch_exact_candidate_chain_status(
        selected_extract_artifact=_read_optional(args.selected_extract_artifact),
        extract_result_artifact=_read_optional(args.extract_result_artifact),
        exact_review_packet_artifact=_read_optional(args.exact_review_packet_artifact),
        preflight_artifact=_read_optional(args.preflight_artifact),
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "blockers": artifact["blockers"],
                "summary": artifact["summary"],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _read_optional(path: str | None) -> dict[str, object] | None:
    return read_json_artifact(Path(path)) if path else None


if __name__ == "__main__":
    raise SystemExit(main())
