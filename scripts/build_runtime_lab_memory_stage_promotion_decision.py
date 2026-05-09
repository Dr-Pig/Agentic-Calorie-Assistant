from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.memory.application.runtime_lab_stage_promotion import (  # noqa: E402
    build_runtime_lab_memory_stage_promotion_decision,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the long-term memory runtime-lab stage promotion decision."
    )
    parser.add_argument("--quality-report-json", required=True, type=Path)
    parser.add_argument("--review-decision-json", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    quality_report = read_json_artifact(args.quality_report_json)
    review_decision = (
        read_json_artifact(args.review_decision_json)
        if args.review_decision_json
        else None
    )
    artifact = build_runtime_lab_memory_stage_promotion_decision(
        read_only_runtime_lab_pack=_read_only_runtime_lab_pack(quality_report),
        human_review_decision=review_decision,
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False))
    return 0 if artifact["status"] == "approved" else 1


def _read_only_runtime_lab_pack(quality_report: dict[str, object]) -> dict[str, object]:
    pack = quality_report.get("read_only_runtime_lab_pack")
    if isinstance(pack, dict):
        return pack
    return {
        "artifact_type": "missing",
        "status": "missing",
        "blockers": ["read_only_runtime_lab_pack_missing"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
