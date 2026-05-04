from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_target_candidate_eval import (  # noqa: E402
    build_context_target_candidate_eval_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run fixture-only Accurate Intake context target-candidate eval."
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_context_target_candidate_eval.json",
    )
    args = parser.parse_args(argv)

    artifact = build_context_target_candidate_eval_artifact()
    write_json_artifact(Path(args.output), artifact)
    print(json.dumps({"artifact": args.output, "status": artifact["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
