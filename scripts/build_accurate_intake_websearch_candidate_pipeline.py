from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_candidate_pipeline import (  # noqa: E402
    build_websearch_candidate_pipeline_diagnostic,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_candidate_pipeline.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic WebSearch candidate pipeline diagnostic artifact."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_websearch_candidate_pipeline_diagnostic()
    write_json_artifact(Path(args.output), artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
