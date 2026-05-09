from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.application.proactive_read_only_runtime_preflight import (  # noqa: E402
    build_proactive_read_only_runtime_preflight_report,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the proactive read-only no-send runtime preflight."
    )
    parser.add_argument("--recommendation-stage-decision-json", required=True, type=Path)
    parser.add_argument("--rescue-stage-decision-json", required=True, type=Path)
    parser.add_argument("--no-send-decision-pack-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    artifact = build_proactive_read_only_runtime_preflight_report(
        recommendation_stage_decision=read_json_artifact(
            args.recommendation_stage_decision_json
        ),
        rescue_stage_decision=read_json_artifact(args.rescue_stage_decision_json),
        no_send_decision_pack=read_json_artifact(args.no_send_decision_pack_json),
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
