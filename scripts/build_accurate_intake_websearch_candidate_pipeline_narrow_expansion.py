from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_candidate_pipeline_narrow_expansion import (  # noqa: E402
    build_websearch_candidate_pipeline_narrow_expansion_artifact,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_PIPELINE = ROOT / "artifacts" / "accurate_intake_websearch_candidate_pipeline.json"
DEFAULT_LIVE_CASE_MATRIX = (
    ROOT / "artifacts" / "accurate_intake_websearch_grokfast_packet_live_diagnostic_case_matrix.json"
)
DEFAULT_OUTPUT = (
    ROOT / "artifacts" / "accurate_intake_websearch_candidate_pipeline_narrow_expansion.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic WebSearch candidate pipeline narrow-expansion status."
    )
    parser.add_argument("--candidate-pipeline-artifact", type=Path, default=DEFAULT_PIPELINE)
    parser.add_argument("--live-case-matrix-artifact", type=Path, default=DEFAULT_LIVE_CASE_MATRIX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    artifact = build_websearch_candidate_pipeline_narrow_expansion_artifact(
        candidate_pipeline_artifact=read_json_artifact(args.candidate_pipeline_artifact),
        live_case_matrix_artifact=read_json_artifact(args.live_case_matrix_artifact),
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
