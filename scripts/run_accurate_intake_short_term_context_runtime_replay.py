from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_short_term_context_runtime_replay import (  # noqa: E402
    build_short_term_context_runtime_replay_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Accurate Intake short-term context runtime replay diagnostic."
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_short_term_context_runtime_replay.json",
    )
    args = parser.parse_args(argv)

    artifact = build_short_term_context_runtime_replay_artifact()
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": args.output,
                "status": artifact["status"],
                "current_gap_scenarios": artifact["summary"]["current_gap_scenarios"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
