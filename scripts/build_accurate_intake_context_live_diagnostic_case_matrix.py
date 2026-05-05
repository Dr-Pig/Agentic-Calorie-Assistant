from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (  # noqa: E402
    build_context_live_diagnostic_case_matrix_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_case_matrix.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the PL+CE context live diagnostic case matrix without invoking a live provider."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    artifact = build_context_live_diagnostic_case_matrix_artifact()
    write_json_artifact(Path(args.output), artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
