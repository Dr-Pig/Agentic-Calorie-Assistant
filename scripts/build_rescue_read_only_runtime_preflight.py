from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rescue.application.read_only_runtime_preflight import (  # noqa: E402
    build_rescue_read_only_runtime_preflight_report,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the rescue read-only runtime preflight report."
    )
    parser.add_argument("--memory-stage-promotion-decision-json", required=True, type=Path)
    parser.add_argument("--rescue-context-projection-json", required=True, type=Path)
    parser.add_argument("--no-commit-viability-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    report = build_rescue_read_only_runtime_preflight_report(
        memory_stage_promotion_decision=read_json_artifact(
            args.memory_stage_promotion_decision_json
        ),
        rescue_context_projection=read_json_artifact(args.rescue_context_projection_json),
        no_commit_viability_packet=read_json_artifact(args.no_commit_viability_json),
    )
    write_json_artifact(args.output, report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
