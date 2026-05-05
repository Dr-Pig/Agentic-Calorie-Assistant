from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_live_extract_canary_report import (  # noqa: E402
    build_websearch_live_extract_canary_report,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_CANARY = (
    ROOT / "artifacts" / "accurate_intake_websearch_live_extract_diagnostic_canary.json"
)
DEFAULT_OUTPUT = (
    ROOT / "artifacts" / "accurate_intake_websearch_live_extract_canary_report.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build WebSearch live-extract canary report without runtime activation."
    )
    parser.add_argument("--canary-artifact", default=str(DEFAULT_CANARY))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    report = build_websearch_live_extract_canary_report(
        canary_artifact=read_json_artifact(Path(args.canary_artifact))
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, report)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": report["status"],
                "selected_option": report["selected_option"],
                "runtime_web_activation_approved": report[
                    "runtime_web_activation_approved"
                ],
                "next_required_slice": report["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
