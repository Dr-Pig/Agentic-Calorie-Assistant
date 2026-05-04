from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_manager_packet_smoke import (  # noqa: E402
    build_websearch_manager_packet_projection,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_INPUT = ROOT / "artifacts" / "accurate_intake_websearch_tool_evidence_result_smoke.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_manager_packet_smoke.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic WebSearch manager packet projection smoke artifact."
    )
    parser.add_argument("--tool-evidence-result", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    input_path = Path(args.tool_evidence_result)
    if input_path.exists():
        tool_artifact = read_json_artifact(input_path)
    else:
        from scripts.build_accurate_intake_websearch_tool_evidence_result_smoke import (  # noqa: PLC0415
            main as build_tool_evidence_result_smoke,
        )

        build_tool_evidence_result_smoke(["--output", str(input_path)])
        tool_artifact = read_json_artifact(input_path)

    artifact = build_websearch_manager_packet_projection(tool_evidence_artifact=tool_artifact)
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "claim_scope": artifact["claim_scope"],
                "case_count": artifact["summary"]["case_count"],
                "candidate_only_count": artifact["summary"]["candidate_only_count"],
                "live_websearch_used": artifact["live_websearch_used"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
