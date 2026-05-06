from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_live_diagnostic_report import (  # noqa: E402
    build_websearch_live_diagnostic_report,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_INPUT = ROOT / "artifacts" / "accurate_intake_grokfast_websearch_packet_smoke.json"
DEFAULT_PREFLIGHT = ROOT / "artifacts" / "accurate_intake_websearch_live_extract_preflight.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_live_diagnostic_report.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build WebSearch live diagnostic report from a sanitized GrokFast packet smoke artifact."
    )
    parser.add_argument("--diagnostic-artifact", default=str(DEFAULT_INPUT))
    parser.add_argument("--preflight-artifact", default=str(DEFAULT_PREFLIGHT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    diagnostic_artifact = read_json_artifact(Path(args.diagnostic_artifact))
    preflight_path = Path(args.preflight_artifact)
    preflight_artifact = read_json_artifact(preflight_path) if preflight_path.exists() else None
    report = build_websearch_live_diagnostic_report(
        diagnostic_artifact=diagnostic_artifact,
        preflight_artifact=preflight_artifact,
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, report)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "claim_scope": report["claim_scope"],
                "seam_status": report["seam_status"],
                "next_recommended_slice": report["next_recommended_slice"],
                "can_expand_websearch_candidate_pipeline": report[
                    "can_expand_websearch_candidate_pipeline"
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
